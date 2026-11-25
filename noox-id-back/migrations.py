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
