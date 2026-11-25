import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _clave_secreta():
    """SECRET_KEY del entorno o, si falta, una clave aleatoria guardada en instance/secret_key (fuera de git).

    Nunca se usa un valor por defecto público: con él cualquiera podría forjar JWT y descifrar los secretos TOTP.
    Se persiste en un archivo para que no cambie en cada reinicio (si cambiara, caducarían las sesiones y los
    secretos TOTP guardados quedarían ilegibles). En producción define SECRET_KEY en el entorno.
    """
    clave = os.environ.get('SECRET_KEY')
    if clave:
        return clave
    ruta = Path(__file__).resolve().parent / 'instance' / 'secret_key'
    if ruta.exists():
        return ruta.read_text(encoding='utf-8').strip()
    ruta.parent.mkdir(exist_ok=True)
    clave = secrets.token_hex(32)
    ruta.write_text(clave, encoding='utf-8')
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass
    print(f'[NooxID] SECRET_KEY no definida: se generó una clave aleatoria en {ruta}. '
          'En producción defínela en el entorno.', file=sys.stderr)
    return clave


def _booleano(nombre, defecto=False):
    return os.environ.get(nombre, str(defecto)).strip().lower() in ('1', 'true', 'yes', 'si', 'sí')


# Servidor de desarrollo: sin depurador salvo que se pida, y el depurador solo en loopback
# (con host 0.0.0.0 el depurador de Werkzeug permite ejecutar código desde la red).
_DEBUG = _booleano('FLASK_DEBUG')
_HOST = os.environ.get('HOST', '127.0.0.1')
if _DEBUG and _HOST not in ('127.0.0.1', 'localhost', '::1'):
    print('[NooxID] FLASK_DEBUG solo se permite en loopback: se usa HOST=127.0.0.1.', file=sys.stderr)
    _HOST = '127.0.0.1'

class Config:
    SECRET_KEY = _clave_secreta()

    DEBUG = _DEBUG
    HOST = _HOST
    PORT = int(os.environ.get('PORT', '5000'))

    # Orígenes del navegador permitidos por CORS. CORS_ORIGINS (separados por coma) añade los tuyos.
    CORS_ORIGINS = [
        'http://localhost:5173', 'http://localhost:5174', 'http://127.0.0.1:5173',
        'http://localhost:8080', 'http://127.0.0.1:8080',   # demo-app (python -m http.server 8080)
        'https://attendanceperu.ooguy.com',
    ] + [o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()]
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:password@localhost/nooxid'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de archivos
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Correo saliente (código de acceso por correo, alternativa al rostro). Ver .env.example
    MAIL_HOST = os.environ.get('MAIL_HOST', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_FROM = os.environ.get('MAIL_FROM', '') or os.environ.get('MAIL_USERNAME', '')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'    # STARTTLS (puerto 587)
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'   # SSL directo (puerto 465)
    MAIL_TIMEOUT = int(os.environ.get('MAIL_TIMEOUT', '10'))
    # Solo desarrollo: imprime el código en la consola del servidor en vez de enviar el correo
    MAIL_CONSOLE = os.environ.get('MAIL_CONSOLE', 'false').lower() == 'true'

    # Inicio de sesión con Google: ID de cliente OAuth (sin él, /api/auth/google-auth queda deshabilitado)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

    # Código de un solo uso por correo
    OTP_EMAIL_TTL_MINUTES = int(os.environ.get('OTP_EMAIL_TTL_MINUTES', '10'))
    OTP_EMAIL_MAX_ATTEMPTS = int(os.environ.get('OTP_EMAIL_MAX_ATTEMPTS', '5'))
    OTP_EMAIL_RESEND_SECONDS = int(os.environ.get('OTP_EMAIL_RESEND_SECONDS', '60'))
    OTP_EMAIL_MAX_PER_HOUR = int(os.environ.get('OTP_EMAIL_MAX_PER_HOUR', '5'))

    # Configuración de reconocimiento facial
    FACE_RECOGNITION_TOLERANCE = 0.6
    FACE_RECOGNITION_MODEL = 'hog'  # 'hog' o 'cnn'
