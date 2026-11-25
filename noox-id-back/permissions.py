"""Permisos de administrador: lista de correos en ADMIN_EMAILS (variable de entorno)."""
from config import Config
from models import User


def is_admin(user_id):
    user = User.query.get(user_id)
    return bool(user and user.verified and user.email and user.email.lower() in Config.ADMIN_EMAILS)
