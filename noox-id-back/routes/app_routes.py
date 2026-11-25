from flask import Blueprint, request, jsonify
from crud import AppCRUD, UserInAppCRUD, TokenToAccessCRUD
import jwt
from config import Config

app_bp = Blueprint('apps', __name__)

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

# =============================================================================
# RUTAS PARA APLICACIONES
# =============================================================================

@app_bp.route('/', methods=['POST'])
@verify_token_decorator
def create_app():
    """Crear nueva aplicación"""
    try:
        data = request.get_json()
        
        if not data.get('name_app'):
            return jsonify({'success': False, 'message': 'Nombre de aplicación requerido'}), 400

        if 'requires_totp' in data and not isinstance(data['requires_totp'], bool):
            return jsonify({'success': False, 'message': 'requires_totp debe ser booleano'}), 400

        data['owner'] = request.current_user_id
        result = AppCRUD.create_app(data)
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/', methods=['GET'])
@verify_token_decorator
def get_user_apps():
    """Obtener aplicaciones del usuario actual"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = AppCRUD.get_apps_by_owner(request.current_user_id, page=page, per_page=per_page)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/<int:app_id>', methods=['GET'])
@verify_token_decorator
def get_app(app_id):
    """Obtener aplicación por ID"""
    try:
        result = AppCRUD.get_app_by_id(app_id)
        
        if result['success']:
            # Verificar permisos (solo el propietario puede ver los detalles completos)
            if result['app']['owner'] != request.current_user_id:
                # Retornar información limitada para no propietarios
                limited_app = {
                    'id': result['app']['id'],
                    'name_app': result['app']['name_app'],
                    'is_verified': result['app']['is_verified'],
                    'IconAppPath': result['app']['IconAppPath']
                }
                return jsonify({'success': True, 'app': limited_app}), 200
        
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/<int:app_id>', methods=['PUT'])
@verify_token_decorator
def update_app(app_id):
    """Actualizar aplicación"""
    try:
        # Verificar que el usuario es el propietario
        app_result = AppCRUD.get_app_by_id(app_id)
        if not app_result['success']:
            return jsonify({'success': False, 'message': 'Aplicación no encontrada'}), 404
        
        if app_result['app']['owner'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para modificar esta aplicación'}), 403
        
        data = request.get_json()
        if 'requires_totp' in data and not isinstance(data['requires_totp'], bool):
            return jsonify({'success': False, 'message': 'requires_totp debe ser booleano'}), 400
        result = AppCRUD.update_app(app_id, data)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/<int:app_id>', methods=['DELETE'])
@verify_token_decorator
def delete_app(app_id):
    """Eliminar aplicación"""
    try:
        # Verificar que el usuario es el propietario
        app_result = AppCRUD.get_app_by_id(app_id)
        if not app_result['success']:
            return jsonify({'success': False, 'message': 'Aplicación no encontrada'}), 404
        
        if app_result['app']['owner'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para eliminar esta aplicación'}), 403
        
        result = AppCRUD.delete_app(app_id)
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/<int:app_id>/regenerate-key', methods=['POST'])
@verify_token_decorator
def regenerate_api_key(app_id):
    """Regenerar API key de la aplicación"""
    try:
        # Verificar que el usuario es el propietario
        app_result = AppCRUD.get_app_by_id(app_id)
        if not app_result['success']:
            return jsonify({'success': False, 'message': 'Aplicación no encontrada'}), 404
        
        if app_result['app']['owner'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para regenerar la API key'}), 403
        
        result = AppCRUD.regenerate_api_key(app_id)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# =============================================================================
# RUTAS PARA USUARIOS EN APLICACIONES
# =============================================================================

@app_bp.route('/<int:app_id>/users', methods=['POST'])
@verify_token_decorator
def add_user_to_app(app_id):
    """Agregar usuario a aplicación"""
    try:
        # Verificar que el usuario es el propietario de la app
        app_result = AppCRUD.get_app_by_id(app_id)
        if not app_result['success']:
            return jsonify({'success': False, 'message': 'Aplicación no encontrada'}), 404
        
        if app_result['app']['owner'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para modificar usuarios de esta aplicación'}), 403
        
        data = request.get_json()
        
        if not data.get('id_usuario'):
            return jsonify({'success': False, 'message': 'ID de usuario requerido'}), 400
        
        user_app_data = {
            'id_usuario': data['id_usuario'],
            'id_app': app_id,
            'status': data.get('status', 'enable'),
            'TokenToAcces': data.get('TokenToAcces')
        }
        
        result = UserInAppCRUD.create_user_in_app(user_app_data)
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/<int:app_id>/users', methods=['GET'])
@verify_token_decorator
def get_app_users(app_id):
    """Obtener usuarios de una aplicación"""
    try:
        # Verificar que el usuario es el propietario
        app_result = AppCRUD.get_app_by_id(app_id)
        if not app_result['success']:
            return jsonify({'success': False, 'message': 'Aplicación no encontrada'}), 404
        
        if app_result['app']['owner'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para ver usuarios de esta aplicación'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = UserInAppCRUD.get_app_users(app_id, page=page, per_page=per_page)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/<int:app_id>/users/<int:user_id>', methods=['PUT'])
@verify_token_decorator
def update_user_app_status(app_id, user_id):
    """Actualizar estado de usuario en aplicación"""
    try:
        # Verificar que el usuario es el propietario
        app_result = AppCRUD.get_app_by_id(app_id)
        if not app_result['success']:
            return jsonify({'success': False, 'message': 'Aplicación no encontrada'}), 404
        
        if app_result['app']['owner'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para modificar usuarios de esta aplicación'}), 403
        
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['enable', 'disable']:
            return jsonify({'success': False, 'message': 'Estado debe ser enable o disable'}), 400
        
        result = UserInAppCRUD.update_user_in_app_status(user_id, app_id, status)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/<int:app_id>/users/<int:user_id>', methods=['DELETE'])
@verify_token_decorator
def remove_user_from_app(app_id, user_id):
    """Remover usuario de aplicación"""
    try:
        # Verificar que el usuario es el propietario
        app_result = AppCRUD.get_app_by_id(app_id)
        if not app_result['success']:
            return jsonify({'success': False, 'message': 'Aplicación no encontrada'}), 404
        
        if app_result['app']['owner'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para modificar usuarios de esta aplicación'}), 403
        
        result = UserInAppCRUD.delete_user_in_app(user_id, app_id)
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# =============================================================================
# RUTAS PARA TOKENS DE ACCESO
# =============================================================================

@app_bp.route('/tokens', methods=['POST'])
@verify_token_decorator
def create_access_token():
    """Crear token de acceso"""
    try:
        data = request.get_json()
        
        data['id_usuario'] = request.current_user_id
        result = TokenToAccessCRUD.create_token(data)
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/tokens', methods=['GET'])
@verify_token_decorator
def get_user_tokens():
    """Obtener tokens del usuario actual"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = TokenToAccessCRUD.get_user_tokens(request.current_user_id, page=page, per_page=per_page)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/tokens/<int:token_id>', methods=['GET'])
@verify_token_decorator
def get_token(token_id):
    """Obtener token por ID"""
    try:
        result = TokenToAccessCRUD.get_token_by_id(token_id)
        
        if result['success']:
            # Verificar que el token pertenece al usuario actual
            if result['token']['id_usuario'] != request.current_user_id:
                return jsonify({'success': False, 'message': 'Sin permisos para ver este token'}), 403
        
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/tokens/<int:token_id>', methods=['PUT'])
@verify_token_decorator
def update_token(token_id):
    """Actualizar token"""
    try:
        # Verificar que el token pertenece al usuario actual
        token_result = TokenToAccessCRUD.get_token_by_id(token_id)
        if not token_result['success']:
            return jsonify({'success': False, 'message': 'Token no encontrado'}), 404
        
        if token_result['token']['id_usuario'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para modificar este token'}), 403
        
        data = request.get_json()
        result = TokenToAccessCRUD.update_token(token_id, data)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/tokens/<int:token_id>', methods=['DELETE'])
@verify_token_decorator
def delete_token(token_id):
    """Eliminar token"""
    try:
        # Verificar que el token pertenece al usuario actual
        token_result = TokenToAccessCRUD.get_token_by_id(token_id)
        if not token_result['success']:
            return jsonify({'success': False, 'message': 'Token no encontrado'}), 404
        
        if token_result['token']['id_usuario'] != request.current_user_id:
            return jsonify({'success': False, 'message': 'Sin permisos para eliminar este token'}), 403
        
        result = TokenToAccessCRUD.delete_token(token_id)
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app_bp.route('/tokens/<int:token_id>/validate', methods=['GET'])
@verify_token_decorator
def validate_token(token_id):
    """Validar token"""
    try:
        result = TokenToAccessCRUD.is_token_valid(token_id)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
