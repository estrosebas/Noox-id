"""Consulta de permisos de un usuario (los roles y permisos viven en la base de datos; ver rbac.py)."""
from models import User


def has_permission(user_id, permission):
    """True si alguno de los roles del usuario incluye el permiso. Exige correo verificado."""
    user = User.query.get(user_id)
    if not user or not user.verified:
        return False
    return any(p.name == permission for rol in user.roles for p in rol.permissions)


def has_role(user_id, role):
    user = User.query.get(user_id)
    return bool(user and user.verified and any(r.name == role for r in user.roles))
