"""Prueba automática de NooxID. Ejecuta: python tests/prueba_aviso_acceso.py
Usa una base SQLite temporal y un SMTP simulado: no toca tu base de datos ni envía correos.
Termina con una línea «... OK» si todo pasa."""
import os, sys, tempfile, re, time
BACK = str(__import__('pathlib').Path(__file__).resolve().parents[1])
os.chdir(BACK); sys.path.insert(0, BACK)
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'a.db').replace(chr(92), '/')
os.environ.update(MAIL_HOST='smtp.test', MAIL_PORT='587', MAIL_USERNAME='u', MAIL_PASSWORD='p', MAIL_FROM='NooxID <no@x.com>')

import smtplib
SENT = []
class FakeSMTP:
    def __init__(self, host, port, timeout=None): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self): pass
    def login(self, u, p): pass
    def send_message(self, m): SENT.append(m)
smtplib.SMTP = FakeSMTP

import contextlib, io
from app import create_app
import totp_service as T
from config import Config
import routes.face_recognition_routes as FR
from models import db, User
with contextlib.redirect_stdout(io.StringIO()):
    app = create_app()
c = app.test_client()
Config.OTP_EMAIL_RESEND_SECONDS = 0
FAKE = {'ok': True}
FR.face_service.verify_user_face = lambda v, i: {'verified': FAKE['ok'], 'distance': .3, 'confidence': .7}
def j(r): return r.status_code, r.get_json()
def accesos(): time.sleep(0.4); return [m for m in SENT if 'Nuevo acceso' in m['Subject']]
def codigo():
    m = [x for x in SENT if 'Nuevo acceso' not in x['Subject']][-1]
    return re.search(r'es: (\d{6})', m.get_content()).group(1)

j(c.post('/api/auth/register', json={'firstname': 'Ana', 'lastname': 'P', 'email': 'ana@x.com', 'password': 'pw12345'}))
with app.app_context():
    u = User.query.filter_by(email='ana@x.com').first(); u.verified = True; u.base64vector = 'v'; db.session.commit()
H = {'Authorization': 'Bearer ' + j(c.post('/api/auth/login', json={'email': 'ana@x.com', 'password': 'pw12345'}))[1]['token']}
crm = c.post('/api/apps/', json={'name_app': 'CRM Ventas'}, headers=H).get_json()['app']
adm = c.post('/api/apps/', json={'name_app': 'Panel Admin', 'requires_totp': True}, headers=H).get_json()['app']
for a in (crm, adm): c.post(f"/api/apps/{a['id']}/users", json={'email': 'ana@x.com'}, headers=H)
def AH(a): return {'X-API-Key': a['api_key'], 'X-App-ID': str(a['id'])}
assert accesos() == [], 'registrarse y crear apps no es un acceso'

# 1) app sin TOTP, por código de correo: un aviso con el nombre de la app
c.post('/api/otp/request', json={'user_email': 'ana@x.com'}, headers=AH(crm))
st, d = j(c.post('/api/otp/verify', json={'user_email': 'ana@x.com', 'code': codigo()}, headers=AH(crm))); assert d['authenticated'], d
av = accesos(); assert len(av) == 1, len(av)
m = av[0]; cuerpo = m.get_content()
assert m['To'] == 'ana@x.com' and 'CRM Ventas' in m['Subject'] and 'CRM Ventas' in cuerpo and 'código enviado por correo' in cuerpo and 'UTC' in cuerpo and 'Hola Ana' in cuerpo, cuerpo
print('1 aviso por código OK')

# 2) app sin TOTP, por rostro
st, d = j(c.post('/api/face/verify-user', json={'user_email': 'ana@x.com', 'face_image': 'x'}, headers=AH(crm))); assert d['authenticated']
av = accesos(); assert len(av) == 2 and 'reconocimiento facial' in av[1].get_content() and 'TOTP' not in av[1].get_content()
print('2 aviso por rostro OK')

# 3) rostro que NO coincide: no hay aviso
FAKE['ok'] = False
j(c.post('/api/face/verify-user', json={'user_email': 'ana@x.com', 'face_image': 'x'}, headers=AH(crm))); FAKE['ok'] = True
assert len(accesos()) == 2, 'un intento fallido no genera aviso'

# 4) app con TOTP: tras el rostro todavía no hay acceso (ni aviso); al canjear el TOTP sí, con ambos factores
d = c.post('/api/totp/setup', headers=H).get_json(); sec = d['secret']; step = T.current_step()
assert c.post('/api/totp/enable', json={'code': T._code_for_step(sec, step)}, headers=H).status_code == 200
st, d = j(c.post('/api/face/verify-user', json={'user_email': 'ana@x.com', 'face_image': 'x'}, headers=AH(adm))); assert d['totp_required']
assert len(accesos()) == 2, 'sin TOTP aún no hay acceso'
st, d = j(c.post('/api/face/verify-totp', json={'challenge_token': d['challenge_token'], 'totp_code': T._code_for_step(sec, step + 1)}, headers=AH(adm))); assert d['authenticated'], d
av = accesos(); assert len(av) == 3, len(av)
cu = av[2].get_content(); assert 'Panel Admin' in av[2]['Subject'] and 'reconocimiento facial y código TOTP' in cu, cu
print('4 aviso tras TOTP OK')

# 5) desactivado por configuración
Config.ACCESS_NOTIFY = False
c.post('/api/face/verify-user', json={'user_email': 'ana@x.com', 'face_image': 'x'}, headers=AH(crm))
assert len(accesos()) == 3; Config.ACCESS_NOTIFY = True

# 6) si el correo falla, el acceso igual se concede
def boom(self, m): raise smtplib.SMTPException('caído')
FakeSMTP.send_message = boom
st, d = j(c.post('/api/face/verify-user', json={'user_email': 'ana@x.com', 'face_image': 'x'}, headers=AH(crm)))
assert st == 200 and d['authenticated'] is True
time.sleep(0.4)
print('AVISO OK')
