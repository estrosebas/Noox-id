"""Decoradores de autenticación y autorización para las rutas internas (JWT + permisos)."""
from functools import wraps

import jwt
from flask import request, jsonify

from config import Config
from permissions import has_permission


def token_required(f):
    """Exige un JWT válido y deja el id en request.current_user_id."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Token no proporcionado'}), 401
        if token.startswith('Bearer '):
            token = token[7:]
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            request.current_user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token expirado'}), 401
        except (jwt.InvalidTokenError, KeyError):
            return jsonify({'success': False, 'message': 'Token inválido'}), 401
        return f(*args, **kwargs)
    return wrapper


def permission_required(*permisos):
    """Además del JWT, exige que el usuario tenga TODOS los permisos indicados (403 si no)."""
    def decorador(f):
        @wraps(f)
        @token_required
        def wrapper(*args, **kwargs):
            for permiso in permisos:
                if not has_permission(request.current_user_id, permiso):
                    return jsonify({'success': False, 'message': 'No tienes permiso para esta acción',
                                    'required_permission': permiso}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorador
