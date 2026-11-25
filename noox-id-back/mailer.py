"""Envío de correo por SMTP, configurado solo con variables de entorno (ver .env.example)."""
import smtplib
from email.message import EmailMessage

from config import Config


class MailNotConfigured(Exception):
    """Faltan MAIL_HOST / MAIL_FROM en el entorno."""


class MailError(Exception):
    """El servidor SMTP rechazó o no pudo entregar el mensaje."""


def is_configured():
    return Config.MAIL_CONSOLE or bool(Config.MAIL_HOST and Config.MAIL_FROM)


def send_mail(to, subject, text):
    if Config.MAIL_CONSOLE:
        print(f'[MAIL_CONSOLE] Para: {to}\nAsunto: {subject}\n{text}\n', flush=True)
        return
    if not (Config.MAIL_HOST and Config.MAIL_FROM):
        raise MailNotConfigured('El envío de correo no está configurado (MAIL_HOST, MAIL_FROM).')

    msg = EmailMessage()
    msg['From'] = Config.MAIL_FROM
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(text)

    try:
        if Config.MAIL_USE_SSL:
            server = smtplib.SMTP_SSL(Config.MAIL_HOST, Config.MAIL_PORT, timeout=Config.MAIL_TIMEOUT)
        else:
            server = smtplib.SMTP(Config.MAIL_HOST, Config.MAIL_PORT, timeout=Config.MAIL_TIMEOUT)
        with server:
            if Config.MAIL_USE_TLS and not Config.MAIL_USE_SSL:
                server.starttls()
            if Config.MAIL_USERNAME:
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        raise MailError(str(e)) from e
