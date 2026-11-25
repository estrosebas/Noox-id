"""Prueba automática de NooxID. Ejecuta: python tests/prueba_roles_permisos.py
Usa una base SQLite temporal y un SMTP simulado: no toca tu base de datos ni envía correos.
Termina con una línea «... OK» si todo pasa."""
import os, sys, tempfile, subprocess, io, contextlib
BACK = str(__import__('pathlib').Path(__file__).resolve().parents[1])
os.chdir(BACK); sys.path.insert(0, BACK)
DBFILE = os.path.join(tempfile.mkdtemp(), 'rbac.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + DBFILE.replace(chr(92), '/')
os.environ['MAIL_CONSOLE'] = 'true'

from app import create_app
import rbac
from models import db, User, Role, Permission
with contextlib.redirect_stdout(io.StringIO()) as sal:
    app = create_app()
assert 'No hay administradores' in sal.getvalue()
c = app.test_client()
def j(r): return r.status_code, r.get_json()

# seed idempotente
with contextlib.redirect_stdout(io.StringIO()):
    create_app(); create_app()
with app.app_context():
    assert Role.query.count() == 1 and Permission.query.count() == len(rbac.PERMISSIONS)
    assert sorted(p.name for p in Role.query.filter_by(name='admin').first().permissions) == sorted(rbac.PERMISSIONS)

def crear(email, verificado=True):
    j(c.post('/api/auth/register', json={'firstname': 'N', 'lastname': 'A', 'email': email, 'password': 'pw12345'}))
    with app.app_context():
        u = User.query.filter_by(email=email).first(); u.verified = verificado; db.session.commit()
        uid = u.id
    if not verificado:
        return None, uid
    tok = j(c.post('/api/auth/login', json={'email': email, 'password': 'pw12345'}))[1]['token']
    return {'Authorization': 'Bearer ' + tok}, uid

HA, id_a = crear('admin@x.com'); HU, id_u = crear('user@x.com'); HV, id_v = crear('viewer@x.com')
# sin roles: nadie puede nada
assert j(c.post('/api/face/tolerance', json={'tolerance': 0.4}, headers=HA))[0] == 403
st, d = j(c.post('/api/face/tolerance', json={'tolerance': 0.4}, headers=HA)); assert d['required_permission'] == 'face.threshold.update'
assert j(c.get('/api/admin/roles', headers=HA))[0] == 403

# primer administrador por la línea de comandos (como `php artisan`)
def cli(*args):
    env = dict(os.environ)
    r = subprocess.run([sys.executable, 'manage.py', *args], cwd=BACK, env=env, capture_output=True, text=True, encoding='utf-8')
    return r.returncode, r.stdout + r.stderr
rc, out = cli('make-admin', 'noexiste@x.com'); assert rc != 0 and 'No existe' in out
rc, out = cli('make-admin', 'admin@x.com'); assert rc == 0 and 'ahora es administrador' in out, out
rc, out = cli('admins'); assert 'admin@x.com' in out
rc, out = cli('roles'); assert 'admin' in out and 'face.threshold.update' in out
st, d = j(c.post('/api/auth/login', json={'email': 'admin@x.com', 'password': 'pw12345'})); assert d['user']['roles'] == ['admin']
# el permiso se aplica al instante, con el mismo token
assert j(c.post('/api/face/tolerance', json={'tolerance': 0.4}, headers=HA))[0] == 200
assert j(c.get('/api/users/', headers=HA))[0] == 200 and j(c.get('/api/users/search?email=user@x.com', headers=HA))[0] == 200
assert j(c.get('/api/users/', headers=HU))[0] == 403

# gestión de roles por API
st, d = j(c.get('/api/admin/roles', headers=HA)); assert st == 200 and d['roles'][0]['name'] == 'admin'
assert j(c.get('/api/admin/roles', headers=HU))[0] == 403
assert j(c.post(f'/api/admin/users/{id_u}/roles', json={'role': 'inexistente'}, headers=HA))[0] == 404
# un rol nuevo con UN solo permiso (la lógica pregunta por permisos, no por roles)
with app.app_context():
    r = Role(name='auditor', label='Auditor'); r.permissions.append(Permission.query.filter_by(name='users.list').first())
    db.session.add(r); db.session.commit()
assert j(c.post(f'/api/admin/users/{id_v}/roles', json={'role': 'auditor'}, headers=HA))[0] == 200
assert j(c.get('/api/users/', headers=HV))[0] == 200, 'el auditor lista'
assert j(c.get('/api/users/search?email=user@x.com', headers=HV))[0] == 403, 'pero no busca'
assert j(c.post('/api/face/tolerance', json={'tolerance': 0.1}, headers=HV))[0] == 403
assert j(c.get('/api/admin/roles', headers=HV))[0] == 403
# quitar el rol surte efecto al instante
assert j(c.delete(f'/api/admin/users/{id_v}/roles/auditor', headers=HA))[0] == 200
assert j(c.get('/api/users/', headers=HV))[0] == 403
# nunca se queda el sistema sin administrador
st, d = j(c.delete(f'/api/admin/users/{id_a}/roles/admin', headers=HA)); assert st == 409, (st, d)
# con dos administradores sí se puede quitar uno
assert j(c.post(f'/api/admin/users/{id_u}/roles', json={'role': 'admin'}, headers=HA))[0] == 200
assert j(c.delete(f'/api/admin/users/{id_a}/roles/admin', headers=HA))[0] == 200
assert j(c.get('/api/admin/roles', headers=HA))[0] == 403
# un administrador con el correo sin verificar no tiene permisos
HX, id_x = crear('pend@x.com', verificado=False)
with app.app_context():
    rbac.assign_role(User.query.get(id_x), 'admin')
    from permissions import has_permission
    assert has_permission(id_x, 'users.list') is False
    u = User.query.get(id_x); u.verified = True; db.session.commit()
    assert has_permission(id_x, 'users.list') is True
# CORS: el origen de la demo está permitido
r = c.post('/api/auth/login', json={'email': 'x', 'password': 'y'}, headers={'Origin': 'http://localhost:8080'})
assert r.headers.get('Access-Control-Allow-Origin') == 'http://localhost:8080', r.headers
r = c.post('/api/auth/login', json={'email': 'x', 'password': 'y'}, headers={'Origin': 'http://evil.example'})
assert r.headers.get('Access-Control-Allow-Origin') is None
print('RBAC OK')
