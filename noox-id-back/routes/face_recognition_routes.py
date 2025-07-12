from flask import Blueprint, request, jsonify
from face_recognition_service import FaceRecognitionService
from crud import UserCRUD, AppCRUD
import jwt
from config import Config

face_bp = Blueprint('face', __name__)
face_service = FaceRecognitionService()

def verify_api_key():
    """Verificar API key en las cabeceras"""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return None, jsonify({'success': False, 'message': 'API Key requerida'}), 401
    
    # Buscar la aplicación por API key
    # En una implementación real, podrías tener un índice para esto
    # Por ahora, simplificamos asumiendo que se pasa el app_id también
    app_id = request.headers.get('X-App-ID')
    if not app_id:
        return None, jsonify({'success': False, 'message': 'App ID requerido'}), 401
    
    try:
        app_result = AppCRUD.get_app_by_id(int(app_id))
        if not app_result['success']:
            return None, jsonify({'success': False, 'message': 'Aplicación no encontrada'}), 404
        
        if app_result['app']['api_key'] != api_key:
            return None, jsonify({'success': False, 'message': 'API Key inválida'}), 401
        
        return app_result['app'], None, None
        
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
        
        # Verificar si el usuario tiene vector facial
        if not user.base64vector:
            return jsonify({'success': False, 'message': 'Usuario no tiene imagen facial registrada'}), 400
        
        # Verificar rostro
        face_result = face_service.verify_user_face(user.base64vector, data['face_image'])
        
        return jsonify({
            'success': True,
            'verification': face_result,
            'user_id': user.id,
            'app_id': app['id']
        }), 200
        
    except Exception as e:
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
