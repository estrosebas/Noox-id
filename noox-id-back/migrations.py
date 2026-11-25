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
