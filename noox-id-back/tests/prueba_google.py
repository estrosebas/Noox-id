"""Prueba automática de NooxID. Ejecuta: python tests/prueba_google.py
Usa una base SQLite temporal y un SMTP simulado: no toca tu base de datos ni envía correos.
Termina con una línea «... OK» si todo pasa."""
import os, sys, tempfile
BACK = str(__import__('pathlib').Path(__file__).resolve().parents[1])
os.chdir(BACK); sys.path.insert(0, BACK)
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'g.db').replace('\\', '/')
os.environ['MAIL_CONSOLE'] = 'true'
os.environ['GOOGLE_CLIENT_ID'] = 'cliente-123.apps.googleusercontent.com'

import google_auth_service as G
from app import create_app
app = create_app(); c = app.test_client()
def j(r): return r.status_code, r.get_json()

TOKENS = {}
def fake(tok):
    if tok not in TOKENS: raise G.GoogleTokenInvalid('Google rechazó el token')
    return TOKENS[tok]
G._fetch_tokeninfo = fake
GOOD = dict(aud=os.environ['GOOGLE_CLIENT_ID'], iss='https://accounts.google.com', email_verified='true',
            email='ana@gmail.com', sub='sub-ana', given_name='Ana', family_name='Pérez')
TOKENS['ok'] = GOOD
TOKENS['otra_app'] = {**GOOD, 'aud': 'otro-cliente'}
TOKENS['sin_verificar'] = {**GOOD, 'email_verified': 'false'}
TOKENS['iss_malo'] = {**GOOD, 'iss': 'https://evil.com'}
TOKENS['sub_otro'] = {**GOOD, 'sub': 'sub-OTRO'}

# El ataque original: correo + googleid inventados, sin token -> ya no entra
st, d = j(c.post('/api/auth/google-auth', json={'email': 'victima@x.com', 'googleid': 'x'})); assert st == 401 and 'token' not in d, (st, d)
# token falso
assert j(c.post('/api/auth/google-auth', json={'id_token': 'inventado'}))[0] == 401
# token emitido para otra aplicación / correo sin verificar / emisor falso
for t in ('otra_app', 'sin_verificar', 'iss_malo'):
    assert j(c.post('/api/auth/google-auth', json={'id_token': t}))[0] == 401, t
# token válido: crea la cuenta con los datos DEL TOKEN (ignora los que mande el cliente)
st, d = j(c.post('/api/auth/google-auth', json={'id_token': 'ok', 'email': 'victima@x.com', 'googleid': 'x'}))
assert st == 200 and d['token'] and d['user']['email'] == 'ana@gmail.com' and d['user']['verified'] is True and d['user']['googleid'] == 'sub-ana', d
# segundo acceso: mismo usuario
st, d2 = j(c.post('/api/auth/google-auth', json={'id_token': 'ok'})); assert st == 200 and d2['user']['id'] == d['user']['id']
# misma cuenta con OTRO sub de Google -> rechazado
assert j(c.post('/api/auth/google-auth', json={'id_token': 'sub_otro'}))[0] == 403
# cuenta existente creada con contraseña: se vincula al primer Google verificado
j(c.post('/api/auth/register', json={'firstname': 'B', 'lastname': 'C', 'email': 'beto@gmail.com', 'password': 'pw12345'}))
TOKENS['beto'] = {**GOOD, 'email': 'beto@gmail.com', 'sub': 'sub-beto'}
st, d = j(c.post('/api/auth/google-auth', json={'id_token': 'beto'})); assert st == 200 and d['user']['googleid'] == 'sub-beto', d
# el token sirve para el panel
H = {'Authorization': 'Bearer ' + d['token']}
assert c.post('/api/auth/verify-token', headers=H).status_code == 200
# sin GOOGLE_CLIENT_ID -> deshabilitado
from config import Config
Config.GOOGLE_CLIENT_ID = ''
assert j(c.post('/api/auth/google-auth', json={'id_token': 'ok'}))[0] == 503
print('GOOGLE OK')
