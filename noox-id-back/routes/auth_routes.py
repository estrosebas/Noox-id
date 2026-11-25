from flask import Blueprint, request, jsonify
from crud import UserCRUD
from face_recognition_service import FaceRecognitionService
import jwt
from datetime import datetime, timedelta
from config import Config
import google_auth_service

auth_bp = Blueprint('auth', __name__)
face_service = FaceRecognitionService()

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registrar nuevo usuario"""
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['firstname', 'lastname', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'message': f'Campo {field} requerido'}), 400
        
        # Procesar imagen de perfil si se proporciona
        if 'base64imageprofile' in data and data['base64imageprofile']:
            face_result = face_service.process_user_profile_image(data['base64imageprofile'])
            if face_result['success']:
                data['base64vector'] = face_result['base64vector']
            else:
                return jsonify({'success': False, 'message': face_result['message']}), 400
        
        # Crear usuario
        result = UserCRUD.create_user(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Iniciar sesión"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'success': False, 'message': 'Email y contraseña requeridos'}), 400
        
        # Verificar credenciales
        result = UserCRUD.verify_password(data['email'], data['password'])
        
        if result['success']:
            # Generar JWT token
            payload = {
                'user_id': result['user']['id'],
                'email': result['user']['email'],
                'exp': datetime.utcnow() + timedelta(days=7)
            }
            
            token = jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
            
            return jsonify({
                'success': True,
                'message': 'Inicio de sesión exitoso',
                'token': token,
                'user': result['user']
            }), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route('/face-login', methods=['POST'])
def face_login():
    """Iniciar sesión con reconocimiento facial"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('face_image'):
            return jsonify({'success': False, 'message': 'Email e imagen facial requeridos'}), 400
        
        # Obtener usuario por email
        user_result = UserCRUD.get_user_by_email(data['email'])
        if not user_result['success']:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        user = user_result['user_obj']
        
        # Verificar si el usuario tiene vector facial
        if not user.base64vector:
            return jsonify({'success': False, 'message': 'Usuario no tiene imagen facial registrada'}), 400
        
        # Verificar rostro
        face_result = face_service.verify_user_face(user.base64vector, data['face_image'])
        
        if face_result['verified']:
            # Generar JWT token
            payload = {
                'user_id': user.id,
                'email': user.email,
                'exp': datetime.utcnow() + timedelta(days=7)
            }
            
            token = jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
            
            return jsonify({
                'success': True,
                'message': 'Inicio de sesión facial exitoso',
                'token': token,
                'user': user.to_dict(),
                'face_verification': {
                    'verified': True,
                    'confidence': face_result['confidence'],
                    'distance': face_result['distance']
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Rostro no verificado',
                'face_verification': {
                    'verified': False,
                    'confidence': face_result['confidence'],
                    'distance': face_result['distance']
                }
            }), 401
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """Verificar token JWT"""
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Token no proporcionado'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        
        # Obtener usuario actual
        user_result = UserCRUD.get_user_by_id(payload['user_id'])
        if user_result['success']:
            return jsonify({
                'success': True,
                'valid': True,
                'user': user_result['user']
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
            
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'message': 'Token expirado'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'message': 'Token inválido'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route('/google-auth', methods=['POST'])
def google_auth():
    """Autenticación con Google. Exige un ID token firmado por Google; el correo y el googleid salen del
    token verificado, nunca de lo que envíe el cliente."""
    try:
        data = request.get_json(silent=True) or {}

        try:
            claims = google_auth_service.verify_id_token(data.get('id_token'))
        except google_auth_service.GoogleNotConfigured:
            return jsonify({'success': False, 'message': 'El acceso con Google no está configurado'}), 503
        except google_auth_service.GoogleTokenInvalid as e:
            return jsonify({'success': False, 'message': f'Token de Google inválido: {e}'}), 401
        except RuntimeError as e:
            return jsonify({'success': False, 'message': str(e)}), 502

        # Buscar usuario existente por correo verificado por Google
        user_result = UserCRUD.get_user_by_email(claims['email'])

        if user_result['success']:
            user = user_result['user_obj']
            if user.googleid and user.googleid != claims['sub']:
                return jsonify({'success': False,
                                'message': 'Esta cuenta está vinculada a otra cuenta de Google'}), 403
            if not user.googleid:
                UserCRUD.update_user(user.id, {'googleid': claims['sub']})
            user_data = user.to_dict()
        else:
            user_result = UserCRUD.create_user({
                'firstname': claims['firstname'],
                'lastname': claims['lastname'],
                'email': claims['email'],
                'googleid': claims['sub'],
                'verified': True  # Google ya verificó el correo
            })
            if not user_result['success']:
                return jsonify(user_result), 400
            user_data = user_result['user']

        # Generar JWT token
        payload = {
            'user_id': user_data['id'],
            'email': user_data['email'],
            'exp': datetime.utcnow() + timedelta(days=7)
        }

        token = jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

        return jsonify({
            'success': True,
            'message': 'Autenticación con Google exitosa',
            'token': token,
            'user': user_data
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
