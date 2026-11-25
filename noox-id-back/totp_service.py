"""Segundo factor TOTP (RFC 6238) para NooxID.

Implementado con la biblioteca estándar (hmac/hashlib), sin dependencias nuevas, y compatible con
Google Authenticator, Microsoft Authenticator, Authy, 1Password, etc. (SHA-1, 6 dígitos, 30 s).

- El secreto se guarda cifrado (Fernet, clave derivada de SECRET_KEY): TOTP necesita el secreto en
  claro para validar, así que no se puede guardar como hash; el cifrado protege un volcado de la BD.
- Cada código solo sirve una vez (se guarda el último intervalo aceptado).
- Tras 5 intentos fallidos en 5 minutos el usuario queda bloqueado temporalmente. El contador vive
  en memoria del proceso: sirve para el prototipo; con varios procesos habría que moverlo a Redis/BD.
"""
import base64
import hashlib
import hmac
import io
import os
import struct
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import quote

import jwt
from cryptography.fernet import Fernet, InvalidToken

from config import Config

ISSUER = 'NooxID'
DIGITS = 6
PERIOD = 30          # segundos por intervalo
WINDOW = 1           # se aceptan ±1 intervalo (tolerancia al desfase de reloj)
MAX_FAILURES = 5
LOCK_SECONDS = 300
CHALLENGE_MINUTES = 5
CHALLENGE_PURPOSE = 'totp_challenge'


# ------------------------------------------------------------------ secreto y cifrado
def generate_secret():
    """Secreto aleatorio de 160 bits en base32 (formato que esperan las apps autenticadoras)."""
    return base64.b32encode(os.urandom(20)).decode('ascii').rstrip('=')


def _fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256(Config.SECRET_KEY.encode('utf-8')).digest())
    return Fernet(key)


def encrypt_secret(secret):
    return _fernet().encrypt(secret.encode('ascii')).decode('ascii')


def decrypt_secret(token):
    try:
        return _fernet().decrypt(token.encode('ascii')).decode('ascii')
    except InvalidToken:
        return None   # SECRET_KEY cambió o el dato está dañado


def provisioning_uri(secret, account):
    """URI otpauth:// que las apps autenticadoras leen desde el código QR."""
    label = quote(f'{ISSUER}:{account}')
    return (f'otpauth://totp/{label}?secret={secret}&issuer={quote(ISSUER)}'
            f'&algorithm=SHA1&digits={DIGITS}&period={PERIOD}')


def qr_data_url(uri):
    """Código QR del URI como imagen SVG (data URL), listo para un <img>. Sin dependencia de Pillow."""
    import qrcode
    from qrcode.image.svg import SvgPathImage
    img = qrcode.make(uri, image_factory=SvgPathImage, box_size=10, border=2)
    buffer = io.BytesIO()
    img.save(buffer)
    return 'data:image/svg+xml;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


# ------------------------------------------------------------------ cálculo y verificación
def _code_for_step(secret, step):
    key = base64.b32decode(secret + '=' * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10 ** DIGITS).zfill(DIGITS)


def current_step(now=None):
    return int((time.time() if now is None else now) // PERIOD)


def verify_code(secret, code, last_step=0, now=None):
    """Devuelve el intervalo (int) en que coincidió el código, o None si no es válido.

    Rechaza códigos de un intervalo ya usado (<= last_step) para impedir la reutilización.
    """
    code = ''.join(str(code or '').split())
    if len(code) != DIGITS or not code.isdigit():
        return None
    step_now = current_step(now)
    matched = None
    for step in range(step_now - WINDOW, step_now + WINDOW + 1):
        # comparación en tiempo constante, recorriendo siempre toda la ventana
        if hmac.compare_digest(_code_for_step(secret, step), code) and step > last_step:
            matched = step
    return matched


# ------------------------------------------------------------------ bloqueo por intentos fallidos
_lock = threading.Lock()
_failures = {}   # user_id -> [timestamps]


def _recent(user_id, now):
    return [t for t in _failures.get(user_id, []) if now - t < LOCK_SECONDS]


def lock_remaining(user_id):
    """Segundos de bloqueo restantes (0 si puede intentar)."""
    now = time.time()
    with _lock:
        recent = _recent(user_id, now)
        _failures[user_id] = recent
        if len(recent) >= MAX_FAILURES:
            return int(LOCK_SECONDS - (now - recent[0])) + 1
    return 0


def register_failure(user_id):
    now = time.time()
    with _lock:
        recent = _recent(user_id, now)
        recent.append(now)
        _failures[user_id] = recent


def clear_failures(user_id):
    with _lock:
        _failures.pop(user_id, None)


# ------------------------------------------------------------------ reto entre rostro y TOTP
def create_challenge(user_id, app_id):
    """Token corto que prueba que el usuario ya pasó el rostro en esta app; se canjea con el código TOTP."""
    payload = {
        'purpose': CHALLENGE_PURPOSE,
        'user_id': user_id,
        'app_id': app_id,
        'exp': datetime.utcnow() + timedelta(minutes=CHALLENGE_MINUTES),
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')


def read_challenge(token):
    """Devuelve el payload del reto o lanza jwt.InvalidTokenError / ExpiredSignatureError."""
    payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
    if payload.get('purpose') != CHALLENGE_PURPOSE:
        raise jwt.InvalidTokenError('Token de propósito incorrecto')
    return payload
