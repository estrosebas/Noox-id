"""Prueba automática de NooxID. Ejecuta: python tests/prueba_registro.py
Usa una base SQLite temporal y un SMTP simulado: no toca tu base de datos ni envía correos.
Termina con una línea «... OK» si todo pasa."""
import os, sys, tempfile, re, io, contextlib
BACK = str(__import__('pathlib').Path(__file__).resolve().parents[1])
os.chdir(BACK); sys.path.insert(0, BACK)
db_path = os.path.join(tempfile.mkdtemp(), 'r.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + db_path.replace('\\', '/')
os.environ['MAIL_CONSOLE'] = 'true'
os.environ['GOOGLE_CLIENT_ID'] = 'cli'

# --- 1) migración sobre una base ANTERIOR: usuarios existentes quedan verificados y se añade `purpose`
import sqlite3
con = sqlite3.connect(db_path)
con.executescript("""
CREATE TABLE users (id INTEGER PRIMARY KEY, firstname VARCHAR(100) NOT NULL, lastname VARCHAR(100) NOT NULL,
 verified BOOLEAN NOT NULL, email VARCHAR(255) NOT NULL UNIQUE, password VARCHAR(255), googleid VARCHAR(255),
 base64imageprofile TEXT, base64vector TEXT, ProfilePickPath VARCHAR(500), created_at DATETIME, updated_at DATETIME,
 totp_secret TEXT, totp_enabled BOOLEAN NOT NULL DEFAULT 0, totp_last_step BIGINT NOT NULL DEFAULT 0);
CREATE TABLE email_otps (id INTEGER PRIMARY KEY, id_usuario INTEGER NOT NULL, code_hash VARCHAR(64) NOT NULL,
 expires_at DATETIME NOT NULL, attempts INTEGER NOT NULL, used BOOLEAN NOT NULL, created_at DATETIME);
INSERT INTO users (id, firstname, lastname, verified, email) VALUES (1,'Viejo','U',0,'viejo@x.com');
""")
con.commit(); con.close()

from app import create_app
import email_otp_service as OTP
from config import Config
from models import db, User, EmailOtp
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    app = create_app()
c = app.test_client()
assert 'email_otps.purpose' in buf.getvalue() and '1 usuario' in buf.getvalue(), buf.getvalue()
with app.app_context():
    assert User.query.filter_by(email='viejo@x.com').first().verified is True
# segunda vez: no vuelve a verificar a nadie
with app.app_context():
    db.session.add(User(firstname='Z', lastname='Z', email='nuevo0@x.com', verified=False)); db.session.commit()
with contextlib.redirect_stdout(io.StringIO()):
    app = create_app(); c = app.test_client()
with app.app_context():
    assert User.query.filter_by(email='nuevo0@x.com').first().verified is False
print('migración OK')

CAPT = io.StringIO()
def pedir_codigo(fn):
    CAPT.seek(0); CAPT.truncate()
    with contextlib.redirect_stdout(CAPT):
        r = fn()
    m = re.search(r': (\d{6})', CAPT.getvalue())
    return r, (m.group(1) if m else None)
def j(r): return r.status_code, r.get_json()
Config.OTP_EMAIL_RESEND_SECONDS = 0
def reg(email, pw='pw12345', **kw):
    return c.post('/api/auth/register', json={'firstname': 'N', 'lastname': 'A', 'email': email, 'password': pw, **kw})

# --- registro: crea cuenta sin verificar y envía el código
r, code = pedir_codigo(lambda: reg('ana@x.com'))
st, d = j(r); assert st == 201 and d['verification_required'] and d['verification_sent'] and code, d
assert 'Verifica tu correo' in CAPT.getvalue()
# no se puede entrar sin verificar: contraseña, y tampoco con el rostro
st, d = j(c.post('/api/auth/login', json={'email': 'ana@x.com', 'password': 'pw12345'})); assert st == 403 and d['code'] == 'EMAIL_NOT_VERIFIED', d
st, d = j(c.post('/api/auth/face-login', json={'email': 'ana@x.com', 'face_image': 'x'})); assert st == 403 and d['code'] == 'EMAIL_NOT_VERIFIED', d
# tampoco una app externa
H0 = {'Authorization': 'Bearer ' + 'x'}
# código incorrecto
assert j(c.post('/api/otp/login/verify', json={'email': 'ana@x.com', 'code': '000000'}))[0] == 401
# código correcto: entra (JWT) y el correo queda verificado, la contraseña del registro SE CONSERVA
st, d = j(c.post('/api/otp/login/verify', json={'email': 'ana@x.com', 'code': code})); assert st == 200 and d['token'] and d['user']['verified'] is True, d
st, d = j(c.post('/api/auth/login', json={'email': 'ana@x.com', 'password': 'pw12345'})); assert st == 200, d

# --- reenvío del código de registro (purpose register) conserva la contraseña
reg('beto@x.com')
r, code = pedir_codigo(lambda: c.post('/api/otp/register/resend', json={'email': 'beto@x.com'}))
assert r.status_code == 200 and code
assert j(c.post('/api/otp/login/verify', json={'email': 'beto@x.com', 'code': code}))[0] == 200
assert j(c.post('/api/auth/login', json={'email': 'beto@x.com', 'password': 'pw12345'}))[0] == 200
# reenviar a una cuenta ya verificada: responde igual y no envía nada
r, code = pedir_codigo(lambda: c.post('/api/otp/register/resend', json={'email': 'beto@x.com'}))
assert r.status_code == 200 and code is None

# --- PRE-SECUESTRO: un atacante registra el correo de la víctima con su contraseña y su rostro
reg('victima@x.com', pw='contraseña-del-atacante')
with app.app_context():
    u = User.query.filter_by(email='victima@x.com').first(); u.base64vector = 'rostro-atacante'; db.session.commit()
# la víctima entra después con un código de ACCESO (purpose login): se verifica y se borra lo del atacante
r, code = pedir_codigo(lambda: c.post('/api/otp/login/request', json={'email': 'victima@x.com'}))
assert code and 'código de acceso' in CAPT.getvalue()
assert j(c.post('/api/otp/login/verify', json={'email': 'victima@x.com', 'code': code}))[0] == 200
assert j(c.post('/api/auth/login', json={'email': 'victima@x.com', 'password': 'contraseña-del-atacante'}))[0] == 401
with app.app_context():
    u = User.query.filter_by(email='victima@x.com').first()
    assert u.verified and u.password is None and u.base64vector is None
# lo mismo si la víctima verifica con Google
reg('v2@x.com', pw='atacante2')
import google_auth_service as G
G._fetch_tokeninfo = lambda t: dict(aud='cli', iss='accounts.google.com', email_verified='true', email='v2@x.com', sub='s-v2')
st, d = j(c.post('/api/auth/google-auth', json={'id_token': 'ok'})); assert st == 200 and d['user']['verified'], d
assert j(c.post('/api/auth/login', json={'email': 'v2@x.com', 'password': 'atacante2'}))[0] == 401

# --- registrar de nuevo un correo SIN verificar reemplaza los datos pendientes (la víctima se registra de verdad)
reg('pend@x.com', pw='viejo-pw')
r, code = pedir_codigo(lambda: reg('pend@x.com', pw='nuevo-pw'))
assert r.status_code == 201 and code
assert j(c.post('/api/otp/login/verify', json={'email': 'pend@x.com', 'code': code}))[0] == 200
assert j(c.post('/api/auth/login', json={'email': 'pend@x.com', 'password': 'nuevo-pw'}))[0] == 200
assert j(c.post('/api/auth/login', json={'email': 'pend@x.com', 'password': 'viejo-pw'}))[0] == 401
# registrar un correo YA verificado: rechazado
assert reg('ana@x.com').status_code == 400
# sin correo configurado: no se registra
Config.MAIL_CONSOLE = False; Config.MAIL_HOST = ''
st, d = j(reg('sin@x.com')); assert st == 503, d
with app.app_context():
    assert User.query.filter_by(email='sin@x.com').first() is None
Config.MAIL_CONSOLE = True
# app externa con usuario no verificado
reg('app@x.com')
Hh = {'Authorization': 'Bearer ' + j(c.post('/api/auth/google-auth', json={'id_token': 'ok'}))[1]['token']}
app_d = c.post('/api/apps/', json={'name_app': 'CRM'}, headers=Hh).get_json()['app']
st, d = j(c.post('/api/face/verify-user', json={'user_email': 'app@x.com', 'face_image': 'x'},
                 headers={'X-API-Key': app_d['api_key'], 'X-App-ID': str(app_d['id'])}))
assert st == 403 and d['code'] == 'EMAIL_NOT_VERIFIED', (st, d)
print('REGISTRO OK')
