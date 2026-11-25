"""Comandos de administración de NooxID (equivalente a `php artisan` en Laravel).

    python manage.py make-admin correo@empresa.com     # da el rol admin a un usuario ya registrado
    python manage.py assign correo@empresa.com <rol>   # asigna un rol
    python manage.py revoke correo@empresa.com <rol>   # quita un rol
    python manage.py roles                             # roles y sus permisos
    python manage.py admins                            # quién tiene el rol admin
"""
import argparse
import sys

from app import create_app
import rbac
from models import User


def _usuario(email):
    user = User.query.filter_by(email=email).first()
    if not user:
        sys.exit(f'No existe un usuario con el correo {email}. Debe registrarse primero.')
    return user


def main():
    p = argparse.ArgumentParser(description='Administración de NooxID')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('roles', help='Lista los roles y sus permisos')
    sub.add_parser('admins', help='Lista a los administradores')
    a = sub.add_parser('make-admin', help='Da el rol admin a un usuario')
    a.add_argument('email')
    for nombre in ('assign', 'revoke'):
        s = sub.add_parser(nombre, help=f'{nombre} un rol')
        s.add_argument('email')
        s.add_argument('role')
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        if args.cmd == 'roles':
            from models import Role
            for rol in Role.query.order_by(Role.name):
                print(f'{rol.name} ({rol.label})')
                for perm in sorted(x.name for x in rol.permissions):
                    print(f'   - {perm}')
        elif args.cmd == 'admins':
            for u in rbac.users_with_role('admin'):
                print(f'{u.id}\t{u.email}')
        elif args.cmd == 'make-admin':
            user = _usuario(args.email)
            if not user.verified:
                print('Aviso: el correo de este usuario aún no está verificado; los permisos no se aplican hasta que lo verifique.')
            rbac.assign_role(user, 'admin')
            print(f'{user.email} ahora es administrador.')
        elif args.cmd == 'assign':
            rbac.assign_role(_usuario(args.email), args.role)
            print(f'Rol {args.role} asignado a {args.email}.')
        elif args.cmd == 'revoke':
            rbac.revoke_role(_usuario(args.email), args.role)
            print(f'Rol {args.role} retirado de {args.email}.')


if __name__ == '__main__':
    main()
