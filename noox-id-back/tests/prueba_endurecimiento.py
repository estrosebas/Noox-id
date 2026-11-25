"""Prueba automática de NooxID. Ejecuta: python tests/prueba_endurecimiento.py
Usa una base SQLite temporal y un SMTP simulado: no toca tu base de datos ni envía correos.
Termina con una línea «... OK» si todo pasa."""
import os, sys, tempfile, subprocess, io, contextlib
BACK = str(__import__('pathlib').Path(__file__).resolve().parents[1])
os.chdir(BACK); sys.path.insert(0, BACK)
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'h.db').replace('\\', '/')
os.environ['MAIL_CONSOLE'] = 'true'

from app import create_app
from config import Config
from models import db, User, App, UserInApp
import throttle
import routes.face_recognition_routes as FR
import routes.auth_routes as AR
with contextlib.redirect_stdout(io.StringIO()):
    app = create_app()
c = app.test_client()
def j(r): return r.status_code, r.get_json()
FAKE = {'ok': True}
FR.face_service.verify_user_face = lambda v, i: {'verified': FAKE['ok'], 'distance': .3, 'confidence': .7}
AR.face_service.verify_user_face = FR.face_service.verify_user_face

def crear(email, pw='pw12345'):
    st, d = j(c.post('/api/auth/register', json={'firstname': 'N', 'lastname': 'A', 'email': email, 'password': pw}))
    assert st == 201, d
    with app.app_context():
        u = User.query.filter_by(email=email).first(); u.verified = True; u.base64vector = 'v'; db.session.commit()
    tok = j(c.post('/api/auth/login', json={'email': email, 'password': pw}))[1]['token']
    return {'Authorization': 'Bearer ' + tok}

HA = crear('admin@x.com'); HU = crear('user@x.com'); HO = crear('otro@x.com')
import rbac
with app.app_context():
    rbac.assign_role(User.query.filter_by(email='admin@x.com').first(), 'admin')
with app.app_context():
    id_user = User.query.filter_by(email='user@x.com').first().id
    id_otro = User.query.filter_by(email='otro@x.com').first().id

# 1) umbral facial: solo administradores
assert j(c.post('/api/face/tolerance', json={'tolerance': 0}, headers=HU))[0] == 403
assert FR.face_service.tolerance > 0, 'un usuario normal no debe poder cambiar el umbral'
assert j(c.get('/api/face/tolerance', headers=HU))[0] == 200
assert j(c.post('/api/face/tolerance', json={'tolerance': 0.4}, headers=HA))[0] == 200 and FR.face_service.tolerance == 0.4
FR.face_service.tolerance = 0.363
print('1 tolerancia OK')

# 2) listado y búsqueda de usuarios
assert j(c.get('/api/users/', headers=HU))[0] == 403
assert j(c.get('/api/users/search?email=otro@x.com', headers=HU))[0] == 403
assert j(c.get(f'/api/users/{id_otro}', headers=HU))[0] == 403
assert j(c.get(f'/api/users/{id_user}', headers=HU))[0] == 200
assert j(c.get('/api/users/', headers=HA))[0] == 200 and j(c.get('/api/users/search?email=otro@x.com', headers=HA))[0] == 200
print('2 usuarios OK')

# 3) perfil: asignación masiva
st, d = j(c.put('/api/users/profile', json={'firstname': 'Nuevo', 'verified': False, 'email': 'robado@x.com', 'googleid': 'g', 'base64vector': 'X'}, headers=HU))
assert st == 200 and d['user']['firstname'] == 'Nuevo' and d['user']['email'] == 'user@x.com' and d['user']['verified'] is True and d['user']['googleid'] is None, d
with app.app_context():
    assert User.query.get(id_user).base64vector == 'v'
assert j(c.put(f'/api/users/{id_user}', json={'email': 'x@x.com'}, headers=HU))[1]['user']['email'] == 'user@x.com'
assert j(c.put('/api/users/profile', json={'password': 'nueva-clave-1'}, headers=HU))[0] == 403
assert j(c.put('/api/users/profile', json={'password': 'nueva-clave-1', 'current_password': 'mala'}, headers=HU))[0] == 403
assert j(c.put('/api/users/profile', json={'password': 'nueva-clave-1', 'current_password': 'pw12345'}, headers=HU))[0] == 200
assert j(c.post('/api/auth/login', json={'email': 'user@x.com', 'password': 'nueva-clave-1'}))[0] == 200
print('3 perfil OK')

# 4) API key solo como hash
st, d = j(c.post('/api/apps/', json={'name_app': 'CRM'}, headers=HU)); crm = d['app']
assert crm['api_key'].startswith('noox_') and crm['api_key_prefix'] == crm['api_key'][:10]
with app.app_context():
    fila = App.query.get(crm['id']); assert fila.api_key.startswith('h1:') and crm['api_key'] not in fila.api_key
lista = j(c.get('/api/apps/', headers=HU))[1]['apps']
assert all('api_key' not in a and a['api_key_prefix'] for a in lista), lista
assert 'api_key' not in j(c.get(f"/api/apps/{crm['id']}", headers=HU))[1]['app']
def AH(a, clave=None): return {'X-API-Key': clave or a['api_key'], 'X-App-ID': str(a['id'])}
vu = lambda a, email='user@x.com', clave=None: c.post('/api/face/verify-user', json={'user_email': email, 'face_image': 'x'}, headers=AH(a, clave))
assert j(vu(crm, clave='mala'))[0] == 401
assert c.post('/api/face/verify-user', json={'user_email': 'user@x.com', 'face_image': 'x'}, headers={'X-API-Key': 'x', 'X-App-ID': '999'}).status_code == 401
st, d = j(c.post(f"/api/apps/{crm['id']}/regenerate-key", headers=HU)); nueva = d['app']['api_key']
assert nueva != crm['api_key'] and nueva.startswith('noox_')
assert j(vu(crm))[0] == 401, 'la clave anterior debe dejar de servir'
crm['api_key'] = nueva
# migración de claves antiguas en texto plano
with app.app_context():
    db.session.execute(db.text("INSERT INTO apps (name_app, owner, api_key, is_verified, requires_totp) VALUES ('Vieja', 1, 'noox_clave_antigua_en_claro', 0, 0)"))
    db.session.commit()
    from migrations import hash_existing_api_keys
    with contextlib.redirect_stdout(io.StringIO()):
        assert hash_existing_api_keys(db) == 1
    vieja = App.query.filter_by(name_app='Vieja').first(); assert vieja.api_key.startswith('h1:') and vieja.check_api_key('noox_clave_antigua_en_claro')
print('4 API keys OK')

# 5) pertenencia usuario-aplicación
st, d = j(vu(crm)); assert st == 403 and d['code'] == 'NOT_A_MEMBER', d
st, d = j(c.post(f"/api/apps/{crm['id']}/users", json={'email': 'user@x.com'}, headers=HU)); assert st == 201, d
assert j(c.post(f"/api/apps/{crm['id']}/users", json={'email': 'user@x.com'}, headers=HU))[0] == 400, 'duplicado'
assert j(c.post(f"/api/apps/{crm['id']}/users", json={'email': 'nadie@x.com'}, headers=HU))[0] == 404
st, d = j(vu(crm)); assert st == 200 and d['authenticated'] is True, d
miembros = j(c.get(f"/api/apps/{crm['id']}/users", headers=HU))[1]['app_users']
assert miembros[0]['email'] == 'user@x.com', miembros
assert j(c.put(f"/api/apps/{crm['id']}/users/{id_user}", json={'status': 'disable'}, headers=HU))[0] == 200
assert j(vu(crm))[0] == 403, 'un usuario deshabilitado no entra'
j(c.put(f"/api/apps/{crm['id']}/users/{id_user}", json={'status': 'enable'}, headers=HU))
# el código por correo tampoco sirve a quien no es miembro
CAP = io.StringIO()
with contextlib.redirect_stdout(CAP):
    r = c.post('/api/otp/request', json={'user_email': 'otro@x.com'}, headers=AH(crm))
assert r.status_code == 200 and 'MAIL_CONSOLE' not in CAP.getvalue(), 'no debe enviar a quien no es miembro'
assert c.post('/api/otp/verify', json={'user_email': 'otro@x.com', 'code': '123456'}, headers=AH(crm)).status_code == 401
print('5 pertenencia OK')

# 6) límite de intentos
for _ in range(10): c.post('/api/auth/login', json={'email': 'otro@x.com', 'password': 'mala'})
st, d = j(c.post('/api/auth/login', json={'email': 'otro@x.com', 'password': 'pw12345'})); assert st == 429 and d['retry_after'] > 0, (st, d)
FAKE['ok'] = False
for _ in range(5): j(c.post('/api/auth/face-login', json={'email': 'user@x.com', 'face_image': 'x'}))
assert j(c.post('/api/auth/face-login', json={'email': 'user@x.com', 'face_image': 'x'}))[0] == 429
for _ in range(5): j(vu(crm))
st, d = j(vu(crm)); assert st == 429, (st, d)
FAKE['ok'] = True
throttle.FACE.reset(f"vu:{crm['id']}:user@x.com")
assert j(vu(crm))[0] == 200, 'un acierto vuelve a funcionar tras reiniciar el contador'
print('6 límites OK')

# 7) configuración del servidor
def cfg(entorno):
    env = {k: v for k, v in os.environ.items() if k not in ('SECRET_KEY', 'FLASK_DEBUG', 'HOST')}
    env.update(entorno)
    out = subprocess.run([sys.executable, '-c', 'from config import Config as C; print(len(C.SECRET_KEY), C.DEBUG, C.HOST)'],
                         cwd=BACK, env=env, capture_output=True, text=True)
    return out.stdout.split(), out.stderr
(n, dbg, host), err = cfg({})
assert n == '64' and dbg == 'False' and host == '127.0.0.1', (n, dbg, host)
assert os.path.exists(os.path.join(BACK, 'instance', 'secret_key'))
(n2, _, _), _ = cfg({}); assert n2 == '64'
assert cfg({'SECRET_KEY': 'mi-clave'})[0][0] == '8'
(_, dbg, host), err = cfg({'FLASK_DEBUG': 'true', 'HOST': '0.0.0.0'})
assert dbg == 'True' and host == '127.0.0.1' and 'solo se permite en loopback' in err, (dbg, host, err)
(_, dbg, host), _ = cfg({'HOST': '0.0.0.0'}); assert dbg == 'False' and host == '0.0.0.0'
print('7 configuración OK')

# 8) una imagen sin rostro es un error del cliente (400), no del servidor (500)
from face_recognition_service import FaceError
def sin_rostro(v, i): raise FaceError('No se detectó ningún rostro en la imagen')
FR.face_service.verify_user_face = sin_rostro
throttle.FACE.reset(f"vu:{crm['id']}:user@x.com")
st, d = j(vu(crm)); assert st == 400 and d['code'] == 'FACE_ERROR' and 'rostro' in d['message'], (st, d)
print('8 FaceError OK')
print('ENDURECIMIENTO OK')
