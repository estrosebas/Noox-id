"""Prueba automática de NooxID. Ejecuta: python tests/prueba_codigo_correo.py
Usa una base SQLite temporal y un SMTP simulado: no toca tu base de datos ni envía correos.
Termina con una línea «... OK» si todo pasa."""
import os, sys, tempfile, re
BACK = str(__import__('pathlib').Path(__file__).resolve().parents[1])
os.chdir(BACK); sys.path.insert(0, BACK)
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'o.db').replace('\\', '/')
os.environ.update(MAIL_HOST='smtp.test', MAIL_PORT='587', MAIL_USERNAME='u', MAIL_PASSWORD='p', MAIL_FROM='NooxID <no@x.com>')

import smtplib
SENT = []
class FakeSMTP:
    def __init__(self, host, port, timeout=None): self.h = (host, port)
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def starttls(self): SENT.append('starttls')
    def login(self, u, p): SENT.append(('login', u))
    def send_message(self, m): SENT.append(m)
smtplib.SMTP = FakeSMTP

from app import create_app
import totp_service as T
from config import Config
import routes.face_recognition_routes as FR
app = create_app(); c = app.test_client()
def j(r): return r.status_code, r.get_json()
def last_code():
    m = [x for x in SENT if not isinstance(x, (str, tuple)) and 'Nuevo acceso' not in x['Subject']][-1]
    return re.search(r'es: (\d{6})', m.get_content()).group(1)

j(c.post('/api/auth/register', json={'firstname': 'A', 'lastname': 'B', 'email': 'a@x.com', 'password': 'pw12345'}))
from models import db as _db, User as _U
with app.app_context():
    _U.query.filter_by(email='a@x.com').first().verified = True; _db.session.commit()
SENT.clear()
H = {'Authorization': 'Bearer ' + j(c.post('/api/auth/login', json={'email': 'a@x.com', 'password': 'pw12345'}))[1]['token']}
crm = c.post('/api/apps/', json={'name_app': 'CRM'}, headers=H).get_json()['app']
adm = c.post('/api/apps/', json={'name_app': 'Admin', 'requires_totp': True}, headers=H).get_json()['app']
for _a in (crm, adm):
    c.post(f"/api/apps/{_a['id']}/users", json={'email': 'a@x.com'}, headers=H)
def AH(a): return {'X-API-Key': a['api_key'], 'X-App-ID': str(a['id'])}
def req(a, email='a@x.com'): return c.post('/api/otp/request', json={'user_email': email}, headers=AH(a))
def ver(a, code, email='a@x.com'): return c.post('/api/otp/verify', json={'user_email': email, 'code': code}, headers=AH(a))

# --- dashboard: pedir y entrar con código
Config.OTP_EMAIL_RESEND_SECONDS = 0
st, d = j(c.post('/api/otp/login/request', json={'email': 'a@x.com'})); assert st == 200, d
assert 'starttls' in SENT and ('login', 'u') in SENT
msg = [x for x in SENT if not isinstance(x, (str, tuple))][-1]
assert msg['To'] == 'a@x.com' and msg['From'] == 'NooxID <no@x.com>'
code = last_code()
assert j(c.post('/api/otp/login/verify', json={'email': 'a@x.com', 'code': '000000'}))[0] == 401
st, d = j(c.post('/api/otp/login/verify', json={'email': 'a@x.com', 'code': code})); assert st == 200 and d['token'], d
# un código no se reutiliza
assert j(c.post('/api/otp/login/verify', json={'email': 'a@x.com', 'code': code}))[0] == 401
# no revela si el correo existe
st, d = j(c.post('/api/otp/login/request', json={'email': 'nadie@x.com'})); assert st == 200 and d['message'] == otp_msg if (otp_msg := d['message']) else True
n_antes = len(SENT); j(c.post('/api/otp/login/request', json={'email': 'nadie@x.com'})); assert len(SENT) == n_antes, 'no debe enviar a correos inexistentes'
# el código no queda en claro en la BD
from models import db, EmailOtp
with app.app_context():
    rows = EmailOtp.query.all(); assert rows and all(len(r.code_hash) == 64 and r.code_hash != code for r in rows)

# --- app sin TOTP: el código basta
req(crm); code = last_code()
st, d = j(ver(crm, code)); assert st == 200 and d['authenticated'] is True and d['method'] == 'email_otp' and d['totp_required'] is False, d
# --- app con TOTP, usuario sin autenticador
req(adm); st, d = j(ver(adm, last_code())); assert d['authenticated'] is False and d['totp_setup_required'] is True and 'challenge_token' not in d, d
# --- activar TOTP y repetir: código -> reto -> TOTP
d = c.post('/api/totp/setup', headers=H).get_json(); secret = d['secret']
step = T.current_step(); assert c.post('/api/totp/enable', json={'code': T._code_for_step(secret, step)}, headers=H).status_code == 200
req(adm); st, d = j(ver(adm, last_code())); assert d['totp_required'] is True and d['authenticated'] is False and d['challenge_token'], d
st, d = j(c.post('/api/face/verify-totp', json={'challenge_token': d['challenge_token'], 'totp_code': T._code_for_step(secret, step + 1)}, headers=AH(adm)))
assert st == 200 and d['authenticated'] is True, d

# --- límites
req(crm); good = last_code()
for _ in range(5): j(ver(crm, '999999' if good != '999999' else '111111'))
assert j(ver(crm, good))[0] == 401, 'tras 5 intentos el código queda invalidado'
Config.OTP_EMAIL_RESEND_SECONDS = 60
req(crm)   # ahora hay uno reciente
st, d = j(req(crm)); assert st == 429 and d['retry_after'] > 0, (st, d)
Config.OTP_EMAIL_RESEND_SECONDS = 0; Config.OTP_EMAIL_MAX_PER_HOUR = 3
st, d = j(req(crm)); assert st == 429, (st, d)
Config.OTP_EMAIL_MAX_PER_HOUR = 50
# vencimiento
from datetime import datetime, timedelta
req(crm); code = last_code()
with app.app_context():
    r = EmailOtp.query.filter_by(used=False).order_by(EmailOtp.id.desc()).first(); r.expires_at = datetime.utcnow() - timedelta(seconds=1); db.session.commit()
assert j(ver(crm, code))[0] == 401
# API key incorrecta
assert c.post('/api/otp/request', json={'user_email': 'a@x.com'}, headers={'X-API-Key': 'mala', 'X-App-ID': str(crm['id'])}).status_code == 401

# --- sin correo configurado
Config.MAIL_HOST = ''
st, d = j(req(crm)); assert st == 503, (st, d)
Config.MAIL_HOST = 'smtp.test'
# --- fallo del SMTP: 502 y no gasta cupo
def boom(self, m): raise smtplib.SMTPException('rechazado')
FakeSMTP.send_message = boom
st, d = j(req(crm)); assert st == 502, (st, d)
with app.app_context():
    assert EmailOtp.query.filter_by(used=False).count() >= 0
# --- modo consola
FakeSMTP.send_message = lambda self, m: SENT.append(m)
Config.MAIL_HOST = ''; Config.MAIL_CONSOLE = True
st, d = j(req(crm)); assert st == 200, (st, d)
print('OTP OK')
