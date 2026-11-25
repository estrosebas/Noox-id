"""Código de un solo uso enviado por correo: alternativa al rostro, siempre disponible.

- El código (6 dígitos) se guarda como HMAC-SHA256 con SECRET_KEY, nunca en claro.
- Vence a los OTP_EMAIL_TTL_MINUTES; se invalida al usarse o al pedir uno nuevo.
- Límites: intentos por código, espera entre envíos y envíos por hora, para impedir fuerza bruta
  y que el endpoint se use para inundar de correos a un usuario.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from config import Config
from models import db, EmailOtp
import mailer


class OtpRateLimited(Exception):
    def __init__(self, retry_after):
        super().__init__('Demasiadas solicitudes de código')
        self.retry_after = retry_after


def _hash(user_id, code):
    msg = f'{user_id}:{code}'.encode('utf-8')
    return hmac.new(Config.SECRET_KEY.encode('utf-8'), msg, hashlib.sha256).hexdigest()


def issue(user, app_name=None):
    """Genera y envía un código nuevo. Lanza OtpRateLimited, MailNotConfigured o MailError."""
    now = datetime.utcnow()
    recent = (EmailOtp.query.filter_by(id_usuario=user.id)
              .filter(EmailOtp.created_at > now - timedelta(hours=1))
              .order_by(EmailOtp.created_at.desc()).all())
    if recent:
        wait = Config.OTP_EMAIL_RESEND_SECONDS - (now - recent[0].created_at).total_seconds()
        if wait > 0:
            raise OtpRateLimited(int(wait) + 1)
    if len(recent) >= Config.OTP_EMAIL_MAX_PER_HOUR:
        raise OtpRateLimited(int(3600 - (now - recent[-1].created_at).total_seconds()) + 1)

    # un solo código vigente por usuario
    EmailOtp.query.filter_by(id_usuario=user.id, used=False).update({'used': True})

    code = f'{secrets.randbelow(10 ** 6):06d}'
    row = EmailOtp(id_usuario=user.id, code_hash=_hash(user.id, code),
                   expires_at=now + timedelta(minutes=Config.OTP_EMAIL_TTL_MINUTES))
    db.session.add(row)
    db.session.commit()

    destino = f' en {app_name}' if app_name else ''
    try:
        mailer.send_mail(
            user.email,
            'Tu código de acceso a NooxID',
            f'Tu código para ingresar{destino} con NooxID es: {code}\n\n'
            f'Vence en {Config.OTP_EMAIL_TTL_MINUTES} minutos y solo sirve una vez.\n'
            'Si no lo pediste, ignora este mensaje: nadie puede entrar a tu cuenta sin el código.\n'
        )
    except Exception:
        db.session.delete(row)   # que un envío fallido no gaste el cupo del usuario
        db.session.commit()
        raise
    return row


def verify(user, code):
    """True si el código es el vigente. Cuenta el intento y lo consume al acertar."""
    code = ''.join(str(code or '').split())
    if len(code) != 6 or not code.isdigit():
        return False
    row = (EmailOtp.query.filter_by(id_usuario=user.id, used=False)
           .order_by(EmailOtp.created_at.desc()).first())
    if not row or row.expires_at < datetime.utcnow():
        return False
    row.attempts += 1
    if row.attempts > Config.OTP_EMAIL_MAX_ATTEMPTS:
        row.used = True
        db.session.commit()
        return False
    ok = hmac.compare_digest(row.code_hash, _hash(user.id, code))
    if ok:
        row.used = True
    db.session.commit()
    return ok
