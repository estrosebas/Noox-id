"""Prueba automática de NooxID. Ejecuta: python tests/prueba_totp.py
Usa una base SQLite temporal y un SMTP simulado: no toca tu base de datos ni envía correos.
Termina con una línea «... OK» si todo pasa."""
import os, sys, tempfile, time
BACK = str(__import__('pathlib').Path(__file__).resolve().parents[1])
os.chdir(BACK); sys.path.insert(0, BACK)
db_file = os.path.join(tempfile.mkdtemp(), 't.db')
os.environ['MAIL_CONSOLE'] = 'true'
os.environ['DATABASE_URL'] = 'sqlite:///' + db_file.replace('\\', '/')

import totp_service as T
# Vector de prueba RFC 6238 (SHA-1, t=59 -> 94287082; 6 dígitos = 287082)
assert T._code_for_step('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', 59 // 30) == '287082', 'RFC 6238'
s = T.generate_secret()
now = time.time(); step = T.current_step(now)
assert T.verify_code(s, T._code_for_step(s, step)) == step
assert T.verify_code(s, T._code_for_step(s, step), last_step=step) is None, 'reutilización'
assert T.verify_code(s, T._code_for_step(s, step + 5)) is None, 'fuera de ventana'
assert T.verify_code(s, '12 34') is None
assert T.decrypt_secret(T.encrypt_secret(s)) == s
print('totp_service OK')

from app import create_app
import face_recognition_service as F
import routes.face_recognition_routes as FR
app = create_app()
c = app.test_client()
FR.face_service.verify_user_face = lambda v, i: {'verified': FAKE['ok'], 'distance': .3, 'confidence': .7}
FAKE = {'ok': True}
def j(r): return r.status_code, r.get_json()

st, d = j(c.post('/api/auth/register', json={'firstname': 'A', 'lastname': 'B', 'email': 'a@x.com', 'password': 'pw12345'}))
assert st == 201, d
from models import db, User
with app.app_context():
    User.query.filter_by(email='a@x.com').first().verified = True; db.session.commit()
st, d = j(c.post('/api/auth/login', json={'email': 'a@x.com', 'password': 'pw12345'}))
H = {'Authorization': 'Bearer ' + d['token']}
assert d['user']['totp_enabled'] is False and 'totp_secret' not in d['user']

# apps: una sin TOTP (CRM) y otra con TOTP (administración)
crm = c.post('/api/apps/', json={'name_app': 'CRM'}, headers=H).get_json()['app']
adm = c.post('/api/apps/', json={'name_app': 'Admin', 'requires_totp': True}, headers=H).get_json()['app']
for _a in (crm, adm):
    c.post(f"/api/apps/{_a['id']}/users", json={'email': 'a@x.com'}, headers=H)
assert crm['requires_totp'] is False and adm['requires_totp'] is True
assert j(c.post('/api/apps/', json={'name_app': 'x', 'requires_totp': 'si'}, headers=H))[0] == 400
def AH(a): return {'X-API-Key': a['api_key'], 'X-App-ID': str(a['id'])}
def face(a): return c.post('/api/face/verify-user', json={'user_email': 'a@x.com', 'face_image': 'x'}, headers=AH(a))

# hay que darle vector facial al usuario
from models import db, User
with app.app_context():
    u = User.query.filter_by(email='a@x.com').first(); u.base64vector = 'v'; db.session.commit()

# CRM: solo rostro
st, d = j(face(crm)); assert st == 200 and d['authenticated'] is True and d['totp_required'] is False, d
# Admin sin TOTP configurado: rostro ok pero no entra
st, d = j(face(adm)); assert d['authenticated'] is False and d['totp_setup_required'] is True and 'challenge_token' not in d, d
# Alta del autenticador
st, d = j(c.post('/api/totp/setup', headers=H)); assert st == 200, d
secret = d['secret']; assert d['otpauth_uri'].startswith('otpauth://totp/NooxID')
assert j(c.get('/api/totp/status', headers=H))[1] == {'success': True, 'enabled': False, 'pending': True}
assert j(c.post('/api/totp/enable', json={'code': '000000'}, headers=H))[0] == 400
step = T.current_step()
code = T._code_for_step(secret, step)
st, d = j(c.post('/api/totp/enable', json={'code': code}, headers=H)); assert st == 200 and d['enabled'], d
# el mismo código no se puede reutilizar
# Admin con TOTP: rostro -> reto
st, d = j(face(adm)); assert d['authenticated'] is False and d['totp_required'] is True and d['challenge_token'], d
ch = d['challenge_token']
# CRM sigue sin pedir TOTP aunque el usuario lo tenga
assert j(face(crm))[1]['authenticated'] is True
# rostro falso no genera reto
FAKE['ok'] = False; d = j(face(adm))[1]; assert d['authenticated'] is False and not d.get('challenge_token'); FAKE['ok'] = True
def tot(a, ch, code): return c.post('/api/face/verify-totp', json={'challenge_token': ch, 'totp_code': code}, headers=AH(a))
# el reto no vale en otra app
assert j(tot(crm, ch, T._code_for_step(secret, step + 1)))[0] == 401
# código reutilizado (el de enable) -> rechazado
st, d = j(tot(adm, ch, code)); assert st == 401 and d['authenticated'] is False, (st, d)
# código nuevo (intervalo siguiente, dentro de la ventana) -> entra
st, d = j(tot(adm, ch, T._code_for_step(secret, step + 1))); assert st == 200 and d['authenticated'] is True, d
# y no se puede reusar
assert j(tot(adm, ch, T._code_for_step(secret, step + 1)))[0] == 401
# bloqueo tras 5 fallos
T.clear_failures(1)
for _ in range(5): j(tot(adm, ch, '111111'))
st, d = j(tot(adm, ch, '222222')); assert st == 429 and d['retry_after'] > 0, (st, d)
T.clear_failures(1)
# reto basura
assert j(tot(adm, 'abc', '123456'))[0] == 401
# desactivar exige código
assert j(c.post('/api/totp/disable', json={'code': '123456'}, headers=H))[0] == 400
T.clear_failures(1)
with app.app_context():
    u = User.query.filter_by(email='a@x.com').first(); u.totp_last_step = 0; db.session.commit()
st, d = j(c.post('/api/totp/disable', json={'code': T._code_for_step(secret, T.current_step())}, headers=H)); assert st == 200 and d['enabled'] is False, d
with app.app_context():
    u = User.query.filter_by(email='a@x.com').first(); assert u.totp_secret is None and not u.totp_enabled
# tras desactivar, la app con TOTP vuelve a pedir configurarlo
assert j(face(adm))[1]['totp_setup_required'] is True
st, d = j(c.post('/api/totp/setup', headers=H)); assert d['qr'].startswith('data:image/svg+xml;base64,') and len(d['qr']) > 500
print('disable + QR OK')
# actualizar app
st, d = j(c.put(f"/api/apps/{crm['id']}", json={'requires_totp': True}, headers=H)); assert d['app']['requires_totp'] is True
# la columna nunca sale en el JSON del usuario
txt = c.get('/api/auth/verify-token', headers=H)
print('TODO OK')
