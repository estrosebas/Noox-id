from flask import Blueprint, request, jsonify
from crud import UserCRUD
from models import User
from permissions import is_admin
from face_recognition_service import FaceRecognitionService
import jwt
from config import Config

user_bp = Blueprint('users', __name__)
face_service = FaceRecognitionService()

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


CAMPOS_EDITABLES = ('firstname', 'lastname', 'base64imageprofile', 'ProfilePickPath', 'password')


def _datos_permitidos(data, user_id):
    """Solo los campos que el usuario puede cambiar por sí mismo. Quedan fuera email, verified, googleid,
    base64vector y totp_*: el correo se verifica y el vector solo sale del procesamiento facial."""
    data = data or {}
    limpio = {k: data[k] for k in CAMPOS_EDITABLES if k in data}
    if 'password' in limpio:
        u = User.query.get(user_id)
        if u and u.password:
            actual = data.get('current_password')
            if not actual or not UserCRUD.verify_password(u.email, actual)['success']:
                return None, (jsonify({'success': False, 'message': 'Contraseña actual incorrecta'}), 403)
    return limpio, None


@user_bp.route('/', methods=['GET'])
@verify_token_decorator
def get_users():
    """Obtener todos los usuarios (paginado)"""
    try:
        if not is_admin(request.current_user_id):
            return jsonify({'success': False, 'message': 'Solo un administrador puede listar usuarios'}), 403
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = UserCRUD.get_all_users(page=page, per_page=per_page)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/<int:user_id>', methods=['GET'])
@verify_token_decorator
def get_user(user_id):
    """Obtener usuario por ID"""
    try:
        if request.current_user_id != user_id and not is_admin(request.current_user_id):
            return jsonify({'success': False, 'message': 'Sin permisos para ver este usuario'}), 403
        result = UserCRUD.get_user_by_id(user_id)
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/profile', methods=['GET'])
@verify_token_decorator
def get_current_user():
    """Obtener perfil del usuario actual"""
    try:
        result = UserCRUD.get_user_by_id(request.current_user_id)
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/profile', methods=['PUT'])
@verify_token_decorator
def update_current_user():
    """Actualizar perfil del usuario actual"""
    try:
        data, error = _datos_permitidos(request.get_json(), request.current_user_id)
        if error:
            return error
        
        # Procesar imagen de perfil si se actualiza
        if 'base64imageprofile' in data and data['base64imageprofile']:
            face_result = face_service.process_user_profile_image(data['base64imageprofile'])
            if face_result['success']:
                data['base64vector'] = face_result['base64vector']
            else:
                return jsonify({'success': False, 'message': face_result['message']}), 400
        
        result = UserCRUD.update_user(request.current_user_id, data)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/<int:user_id>', methods=['PUT'])
@verify_token_decorator
def update_user(user_id):
    """Actualizar usuario por ID (solo admin o el mismo usuario)"""
    try:
        # Verificar permisos (simplificado - en producción agregar roles)
        if request.current_user_id != user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para modificar este usuario'}), 403
        
        data, error = _datos_permitidos(request.get_json(), request.current_user_id)
        if error:
            return error
        
        # Procesar imagen de perfil si se actualiza
        if 'base64imageprofile' in data and data['base64imageprofile']:
            face_result = face_service.process_user_profile_image(data['base64imageprofile'])
            if face_result['success']:
                data['base64vector'] = face_result['base64vector']
            else:
                return jsonify({'success': False, 'message': face_result['message']}), 400
        
        result = UserCRUD.update_user(user_id, data)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/<int:user_id>', methods=['DELETE'])
@verify_token_decorator
def delete_user(user_id):
    """Eliminar usuario por ID (solo admin o el mismo usuario)"""
    try:
        # Verificar permisos (simplificado - en producción agregar roles)
        if request.current_user_id != user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para eliminar este usuario'}), 403
        
        result = UserCRUD.delete_user(user_id)
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/upload-face', methods=['POST'])
@verify_token_decorator
def upload_face_image():
    """Subir o actualizar imagen facial del usuario"""
    try:
        data = request.get_json()
        
        if not data.get('base64imageprofile'):
            return jsonify({'success': False, 'message': 'Imagen base64 requerida'}), 400
        
        # Procesar imagen facial
        face_result = face_service.process_user_profile_image(data['base64imageprofile'])
        
        if face_result['success']:
            # Actualizar usuario con nueva imagen y vector
            update_data = {
                'base64imageprofile': face_result['base64imageprofile'],
                'base64vector': face_result['base64vector']
            }
            
            result = UserCRUD.update_user(request.current_user_id, update_data)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Imagen facial actualizada correctamente',
                    'user': result['user']
                }), 200
            else:
                return jsonify(result), 400
        else:
            return jsonify(face_result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/verify-face', methods=['POST'])
@verify_token_decorator
def verify_face():
    """Verificar rostro del usuario actual"""
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
            'verification_result': face_result
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/search', methods=['GET'])
@verify_token_decorator
def search_users():
    """Buscar usuarios por email o nombre"""
    try:
        if not is_admin(request.current_user_id):
            return jsonify({'success': False, 'message': 'Solo un administrador puede buscar usuarios'}), 403
        email = request.args.get('email')
        
        if email:
            result = UserCRUD.get_user_by_email(email)
            if result['success']:
                return jsonify({'success': True, 'users': [result['user']]}), 200
            else:
                return jsonify({'success': True, 'users': []}), 200
        
        # En producción, agregar búsqueda por nombre
        return jsonify({'success': False, 'message': 'Parámetro de búsqueda requerido'}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
