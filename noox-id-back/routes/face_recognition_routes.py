from flask import Blueprint, request, jsonify
from face_recognition_service import FaceRecognitionService, FaceError
from crud import UserCRUD, AppCRUD
from models import db, User, App
import throttle
from permissions import has_permission
import totp_service
from auth_flow import app_auth_response, avisar_acceso, is_member
import jwt
from config import Config

face_bp = Blueprint('face', __name__)
face_service = FaceRecognitionService()

def verify_api_key():
    """Verificar API key en las cabeceras (la clave se compara contra su hash; ver models.App)"""
    api_key = request.headers.get('X-API-Key')
    app_id = request.headers.get('X-App-ID')
    if not api_key or not app_id:
        return None, jsonify({'success': False, 'message': 'API Key y App ID requeridos'}), 401

    try:
        app_row = App.query.get(int(app_id))
        # misma respuesta para app inexistente y clave incorrecta: no se revela qué apps existen
        if not app_row or not app_row.check_api_key(api_key):
            return None, jsonify({'success': False, 'message': 'API Key inválida'}), 401
        return app_row.to_dict(), None, None
    except ValueError:
        return None, jsonify({'success': False, 'message': 'App ID inválido'}), 401
    except Exception as e:
        return None, jsonify({'success': False, 'message': str(e)}), 500


@face_bp.route('/compare', methods=['POST'])
def compare_faces():
    """Comparar dos rostros - Endpoint público con API key"""
    try:
        app, error_response, status_code = verify_api_key()
        if error_response:
            return error_response, status_code
        
        data = request.get_json()
        
        if not data.get('face1') or not data.get('face2'):
            return jsonify({'success': False, 'message': 'Se requieren dos imágenes faciales'}), 400
        
        # Extraer encodings de ambas imágenes
        encoding1 = face_service.extract_face_encoding(data['face1'])
        encoding2 = face_service.extract_face_encoding(data['face2'])
        
        # Comparar rostros
        comparison_result = face_service.compare_faces(encoding1, encoding2)
        
        return jsonify({
            'success': True,
            'comparison': comparison_result,
            'app_id': app['id']
        }), 200
        
    except FaceError as e:
        # imagen sin rostro, borrosa, etc.: error del cliente, no del servidor
        return jsonify({'success': False, 'code': 'FACE_ERROR', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@face_bp.route('/verify-user', methods=['POST'])
def verify_user_face():
    """Verificar rostro de usuario registrado - Endpoint público con API key"""
    try:
        app, error_response, status_code = verify_api_key()
        if error_response:
            return error_response, status_code
        
        data = request.get_json()
        
        if not data.get('user_email') or not data.get('face_image'):
            return jsonify({'success': False, 'message': 'Email de usuario e imagen facial requeridos'}), 400
        
        # Obtener usuario por email
        user_result = UserCRUD.get_user_by_email(data['user_email'])
        if not user_result['success']:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        user = user_result['user_obj']
        
        clave_intentos = f"vu:{app['id']}:{data['user_email'].lower()}"
        espera = throttle.FACE.locked(clave_intentos)
        if espera:
            return jsonify({'success': False, 'retry_after': espera,
                            'message': f'Demasiados intentos fallidos. Espera {espera} s.'}), 429
        
        if not user.verified:
            return jsonify({'success': False, 'code': 'EMAIL_NOT_VERIFIED',
                            'message': 'El usuario no ha verificado su correo'}), 403
        
        if not is_member(user.id, app['id']):
            return jsonify({'success': False, 'code': 'NOT_A_MEMBER',
                            'message': 'El usuario no está registrado en esta aplicación'}), 403
        
        # Verificar si el usuario tiene vector facial
        if not user.base64vector:
            return jsonify({'success': False, 'message': 'Usuario no tiene imagen facial registrada'}), 400
        
        # Verificar rostro
        face_result = face_service.verify_user_face(user.base64vector, data['face_image'])
        (throttle.FACE.reset if face_result.get('verified') else throttle.FACE.fail)(clave_intentos)
        # `authenticated` es lo que debe mirar la app cliente (ver auth_flow.app_auth_response)
        response = app_auth_response(user, app, bool(face_result.get('verified')), 'face')
        response['verification'] = face_result
        
        return jsonify(response), 200

    except FaceError as e:
        # imagen sin rostro, borrosa, etc.: error del cliente, no del servidor
        return jsonify({'success': False, 'code': 'FACE_ERROR', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@face_bp.route('/verify-totp', methods=['POST'])
def verify_totp():
    """Segundo paso: canjea el reto de /verify-user por el código TOTP - Endpoint público con API key"""
    try:
        app, error_response, status_code = verify_api_key()
        if error_response:
            return error_response, status_code

        data = request.get_json(silent=True) or {}
        if not data.get('challenge_token') or not data.get('totp_code'):
            return jsonify({'success': False, 'authenticated': False,
                            'message': 'challenge_token y totp_code requeridos'}), 400

        try:
            challenge = totp_service.read_challenge(data['challenge_token'])
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'authenticated': False,
                            'message': 'El reto venció; repite la verificación facial'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'authenticated': False, 'message': 'Reto inválido'}), 401

        # El reto solo vale para la app donde se pasó el rostro
        if challenge.get('app_id') != app['id']:
            return jsonify({'success': False, 'authenticated': False,
                            'message': 'El reto no corresponde a esta aplicación'}), 401

        user = User.query.get(challenge['user_id'])
        if not user or not user.totp_enabled or not user.totp_secret:
            return jsonify({'success': False, 'authenticated': False,
                            'message': 'El usuario no tiene el autenticador activo'}), 400

        secret = totp_service.decrypt_secret(user.totp_secret)
        if not secret:
            return jsonify({'success': False, 'authenticated': False, 'message': 'Secreto ilegible'}), 500

        wait = totp_service.lock_remaining(user.id)
        if wait:
            return jsonify({'success': False, 'authenticated': False, 'retry_after': wait,
                            'message': f'Demasiados intentos fallidos. Espera {wait} s.'}), 429

        step = totp_service.verify_code(secret, data['totp_code'], last_step=user.totp_last_step or 0)
        if step is None:
            totp_service.register_failure(user.id)
            return jsonify({'success': False, 'authenticated': False,
                            'message': 'Código incorrecto o vencido'}), 401

        totp_service.clear_failures(user.id)
        user.totp_last_step = step
        db.session.commit()
        avisar_acceso(user, app['name_app'], challenge.get('method'), True)

        return jsonify({
            'success': True,
            'authenticated': True,
            'user_id': user.id,
            'app_id': app['id']
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@face_bp.route('/extract-encoding', methods=['POST'])
def extract_face_encoding():
    """Extraer encoding facial de una imagen - Endpoint público con API key"""
    try:
        app, error_response, status_code = verify_api_key()
        if error_response:
            return error_response, status_code
        
        data = request.get_json()
        
        if not data.get('face_image'):
            return jsonify({'success': False, 'message': 'Imagen facial requerida'}), 400
        
        # Extraer encoding
        encoding = face_service.extract_face_encoding(data['face_image'])
        
        # Convertir a base64 para almacenamiento
        encoding_base64 = face_service.encoding_to_base64(encoding)
        
        return jsonify({
            'success': True,
            'encoding': encoding_base64,
            'message': 'Encoding extraído correctamente',
            'app_id': app['id']
        }), 200
        
    except FaceError as e:
        # imagen sin rostro, borrosa, etc.: error del cliente, no del servidor
        return jsonify({'success': False, 'code': 'FACE_ERROR', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# =============================================================================
# ENDPOINTS INTERNOS (CON JWT TOKEN)
# =============================================================================

def verify_token_decorator(f):
    """Decorador para verificar token JWT"""
    def wrapper(*args, **kwargs):
        try:
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'success': False, 'message': 'Token no proporcionado'}), 401
            
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            request.current_user_id = payload['user_id']
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Token inválido'}), 401
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    wrapper.__name__ = f.__name__
    return wrapper

@face_bp.route('/process-profile-image', methods=['POST'])
@verify_token_decorator
def process_profile_image():
    """Procesar imagen de perfil para extraer encoding facial y actualizar usuario"""
    try:
        data = request.get_json()
        
        if not data.get('base64imageprofile'):
            return jsonify({'success': False, 'message': 'Imagen base64 requerida'}), 400
        
        # Procesar imagen
        result = face_service.process_user_profile_image(data['base64imageprofile'])
        
        if not result['success']:
            return jsonify(result), 400
        
        # Si el procesamiento fue exitoso, actualizar el usuario
        from crud import UserCRUD
        
        update_data = {
            'ProfilePickPath': result['base64imageprofile'],  # Guardar la imagen
            'base64vector': result['base64vector']  # Guardar el vector facial
        }
        
        update_result = UserCRUD.update_user(request.current_user_id, update_data)
        
        if update_result['success']:
            return jsonify({
                'success': True,
                'message': 'Imagen de perfil procesada y guardada correctamente',
                'data': {
                    'face_detected': True,
                    'encoding_extracted': True,
                    'profile_updated': True
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': f'Error actualizando perfil: {update_result["message"]}'
            }), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@face_bp.route('/compare-with-user', methods=['POST'])
@verify_token_decorator
def compare_with_current_user():
    """Comparar imagen facial con el usuario actual"""
    try:
        data = request.get_json()
        
        if not data.get('face_image'):
            return jsonify({'success': False, 'message': 'Imagen facial requerida'}), 400
        
        # Obtener usuario actual
        user_result = UserCRUD.get_user_by_id(request.current_user_id)
        if not user_result['success']:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        user = user_result['user']
        
        # Verificar si el usuario tiene vector facial
        if not user.get('base64vector'):
            return jsonify({'success': False, 'message': 'Usuario no tiene imagen facial registrada'}), 400
        
        # Verificar rostro
        face_result = face_service.verify_user_face(user['base64vector'], data['face_image'])
        
        return jsonify({
            'success': True,
            'verification': face_result
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@face_bp.route('/tolerance', methods=['GET', 'POST'])
@verify_token_decorator
def manage_tolerance():
    """Obtener o configurar tolerancia del reconocimiento facial"""
    try:
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'tolerance': face_service.tolerance,
                'message': 'Tolerancia actual del servicio'
            }), 200
        
        elif request.method == 'POST':
            if not has_permission(request.current_user_id, 'face.threshold.update'):
                return jsonify({'success': False, 'message': 'No tienes permiso para cambiar el umbral',
                                'required_permission': 'face.threshold.update'}), 403
            data = request.get_json()
            tolerance = data.get('tolerance')
            
            if tolerance is None or not (0 <= tolerance <= 1):
                return jsonify({'success': False, 'message': 'Tolerancia debe estar entre 0 y 1'}), 400
            
            face_service.tolerance = tolerance
            
            return jsonify({
                'success': True,
                'tolerance': face_service.tolerance,
                'message': 'Tolerancia actualizada correctamente'
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
