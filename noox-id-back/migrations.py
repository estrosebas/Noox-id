"""Migración mínima: añade columnas nuevas a tablas ya existentes.

`db.create_all()` crea tablas que faltan pero no agrega columnas a las que ya existen, así que una
base creada antes del TOTP no tendría los campos nuevos. Esto los añade si faltan (idempotente).
"""
from sqlalchemy import inspect, text

# tabla -> {columna: definición SQL}
NEW_COLUMNS = {
    'users': {
        'totp_secret': 'TEXT NULL',
        'totp_enabled': 'BOOLEAN NOT NULL DEFAULT 0',
        'totp_last_step': 'BIGINT NOT NULL DEFAULT 0',
    },
    'apps': {
        'requires_totp': 'BOOLEAN NOT NULL DEFAULT 0',
        'api_key_prefix': 'VARCHAR(16) NULL',
    },
    'email_otps': {
        'purpose': "VARCHAR(10) NOT NULL DEFAULT 'login'",
    },
}


def ensure_schema(db):
    inspector = inspect(db.engine)
    added = []
    for table, columns in NEW_COLUMNS.items():
        if not inspector.has_table(table):
            continue
        existing = {c['name'] for c in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in existing:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
                added.append(f'{table}.{name}')
    if added:
        db.session.commit()
        print('Migración: columnas añadidas ->', ', '.join(added))
    return added


def grandfather_existing_users(db, primera_vez):
    """Una sola vez (al aplicarse por primera vez la verificación de correo): da por verificados a los usuarios que ya
    existían, para no dejarlos fuera cuando el acceso exija correo verificado. Los registros nuevos sí se verifican."""
    if not primera_vez:
        return 0
    res = db.session.execute(text('UPDATE users SET verified = 1 WHERE verified = 0'))
    db.session.commit()
    if res.rowcount:
        print(f'Migración: {res.rowcount} usuario(s) existentes marcados como verificados')
    return res.rowcount


def hash_existing_api_keys(db):
    """Las claves guardadas en texto plano por versiones anteriores se sustituyen por su hash (siguen funcionando)."""
    from models import hash_api_key
    filas = db.session.execute(text('SELECT id, api_key FROM apps')).fetchall()
    n = 0
    for id_app, clave in filas:
        if clave and not clave.startswith('h1:'):
            db.session.execute(text('UPDATE apps SET api_key = :h, api_key_prefix = :p WHERE id = :i'),
                               {'h': hash_api_key(clave), 'p': clave[:10], 'i': id_app})
            n += 1
    if n:
        db.session.commit()
        print(f'Migración: {n} API key(s) guardadas ahora solo como hash')
    return n


def ampliar_columnas_mysql(db):
    """En MySQL/MariaDB la foto de perfil en base64 necesita MEDIUMTEXT; las bases creadas antes tienen TEXT (64 KB)."""
    if db.engine.dialect.name not in ('mysql', 'mariadb'):
        return 0
    tipo = db.session.execute(text(
        "SELECT DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'users' AND COLUMN_NAME = 'base64imageprofile'")).scalar()
    if tipo and tipo.lower() == 'text':
        db.session.execute(text('ALTER TABLE users MODIFY COLUMN base64imageprofile MEDIUMTEXT NULL'))
        db.session.commit()
        print('Migración: users.base64imageprofile ampliada a MEDIUMTEXT')
        return 1
    return 0
