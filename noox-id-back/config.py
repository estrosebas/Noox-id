import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
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
