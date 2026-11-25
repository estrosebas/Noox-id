"""Roles y permisos en la base de datos (al estilo de spatie/laravel-permission).

- Un usuario tiene uno o más ROLES (tabla user_roles); un rol agrupa PERMISOS (tabla role_permissions).
- El código pregunta por permisos (`has_permission(user, 'face.threshold.update')`), no por quién es el usuario,
  de modo que se pueden crear roles nuevos sin tocar las rutas.
- `seed()` crea los permisos y roles base de forma idempotente al arrancar; el primer administrador se
  asigna con `python manage.py make-admin correo@empresa.com`.
"""
from models import db, Role, Permission, User

# nombre -> descripción
PERMISSIONS = {
    'users.list': 'Listar usuarios',
    'users.search': 'Buscar usuarios por correo',
    'users.view': 'Ver el perfil de cualquier usuario',
    'face.threshold.update': 'Cambiar el umbral de reconocimiento facial',
    'roles.manage': 'Asignar y quitar roles',
}

# nombre -> (etiqueta, permisos)
ROLES = {
    'admin': ('Administrador', list(PERMISSIONS)),
}


def seed():
    """Crea (sin duplicar) los permisos y roles base y le da al rol su lista de permisos."""
    for nombre, descripcion in PERMISSIONS.items():
        if not Permission.query.filter_by(name=nombre).first():
            db.session.add(Permission(name=nombre, description=descripcion))
    db.session.flush()
    for nombre, (etiqueta, permisos) in ROLES.items():
        rol = Role.query.filter_by(name=nombre).first()
        if not rol:
            rol = Role(name=nombre, label=etiqueta)
            db.session.add(rol)
        existentes = {p.name for p in rol.permissions}
        for p in permisos:
            if p not in existentes:
                rol.permissions.append(Permission.query.filter_by(name=p).first())
    db.session.commit()


def assign_role(user, role_name):
    rol = Role.query.filter_by(name=role_name).first()
    if not rol:
        raise ValueError(f'El rol «{role_name}» no existe')
    if rol not in user.roles:
        user.roles.append(rol)
        db.session.commit()
    return rol


def revoke_role(user, role_name):
    rol = Role.query.filter_by(name=role_name).first()
    if not rol:
        raise ValueError(f'El rol «{role_name}» no existe')
    if rol in user.roles:
        user.roles.remove(rol)
        db.session.commit()
    return rol


def users_with_role(role_name):
    rol = Role.query.filter_by(name=role_name).first()
    return list(rol.users) if rol else []
