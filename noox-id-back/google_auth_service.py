"""Verificación de un ID token de Google (Sign in with Google).

El servidor NUNCA debe fiarse del correo o del googleid que envía el cliente: solo del token que firma
Google. Aquí se valida con el endpoint oficial `tokeninfo` (Google comprueba firma y vigencia) y se
comprueba que el token fue emitido para ESTA aplicación (aud == GOOGLE_CLIENT_ID).
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from config import Config

TOKENINFO_URL = 'https://oauth2.googleapis.com/tokeninfo'
ISSUERS = ('accounts.google.com', 'https://accounts.google.com')


class GoogleNotConfigured(Exception):
    pass


class GoogleTokenInvalid(Exception):
    pass


def _fetch_tokeninfo(id_token):
    url = TOKENINFO_URL + '?' + urllib.parse.urlencode({'id_token': id_token})
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:      # 400 = token inválido o vencido
        raise GoogleTokenInvalid('Google rechazó el token') from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise RuntimeError('No se pudo contactar a Google') from e


def verify_id_token(id_token):
    """Devuelve {'sub', 'email', 'firstname', 'lastname'} del token o lanza GoogleTokenInvalid."""
    if not Config.GOOGLE_CLIENT_ID:
        raise GoogleNotConfigured('GOOGLE_CLIENT_ID no está configurado')
    if not isinstance(id_token, str) or not id_token:
        raise GoogleTokenInvalid('Token ausente')

    claims = _fetch_tokeninfo(id_token)
    if claims.get('aud') != Config.GOOGLE_CLIENT_ID:
        raise GoogleTokenInvalid('El token no fue emitido para esta aplicación')
    if claims.get('iss') not in ISSUERS:
        raise GoogleTokenInvalid('Emisor inválido')
    if str(claims.get('email_verified')).lower() != 'true' or not claims.get('email'):
        raise GoogleTokenInvalid('Google no verificó el correo de esta cuenta')
    if not claims.get('sub'):
        raise GoogleTokenInvalid('Token sin identificador')

    return {
        'sub': claims['sub'],
        'email': claims['email'],
        'firstname': claims.get('given_name') or claims.get('name') or '',
        'lastname': claims.get('family_name') or '',
    }
