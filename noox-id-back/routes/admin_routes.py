"""Administración de roles (permiso `roles.manage`)."""
from flask import Blueprint, jsonify, request

import rbac
from authz import permission_required
from models import Role, User

admin_bp = Blueprint('admin', __name__)


def _rol_dict(rol):
    return {'name': rol.name, 'label': rol.label, 'permissions': sorted(p.name for p in rol.permissions)}


@admin_bp.route('/roles', methods=['GET'])
@permission_required('roles.manage')
def listar_roles():
    return jsonify({'success': True, 'roles': [_rol_dict(r) for r in Role.query.order_by(Role.name).all()]}), 200


@admin_bp.route('/users/<int:user_id>/roles', methods=['GET'])
@permission_required('roles.manage')
def roles_de_usuario(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
    return jsonify({'success': True, 'roles': [_rol_dict(r) for r in user.roles]}), 200


@admin_bp.route('/users/<int:user_id>/roles', methods=['POST'])
@permission_required('roles.manage')
def asignar_rol(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
    nombre = (request.get_json(silent=True) or {}).get('role')
    try:
        rbac.assign_role(user, nombre)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    return jsonify({'success': True, 'roles': [_rol_dict(r) for r in user.roles]}), 200


@admin_bp.route('/users/<int:user_id>/roles/<role_name>', methods=['DELETE'])
@permission_required('roles.manage')
def quitar_rol(user_id, role_name):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
    # nunca dejar el sistema sin quien pueda gestionar roles
    if role_name == 'admin' and len(rbac.users_with_role('admin')) <= 1:
        return jsonify({'success': False, 'message': 'No se puede quitar al último administrador'}), 409
    try:
        rbac.revoke_role(user, role_name)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    return jsonify({'success': True, 'roles': [_rol_dict(r) for r in user.roles]}), 200
