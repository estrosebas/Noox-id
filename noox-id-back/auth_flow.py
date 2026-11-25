"""Respuesta común a las apps cliente después del primer factor (rostro o código por correo), y aviso de acceso."""
import sys
import threading
from datetime import datetime

import mailer
import totp_service
from config import Config
from models import UserInApp

METODOS = {'face': 'reconocimiento facial', 'email_otp': 'código enviado por correo'}


def avisar_acceso(user, app_nombre, metodo, con_totp):
    """Avisa por correo al dueño de la cuenta de que se accedió a una aplicación con ella.

    Va en un hilo aparte para no demorar la respuesta; si el correo falla solo se registra, nunca se rechaza el acceso.
    El aviso no impide un acceso ajeno, pero permite que el dueño lo detecte (útil porque el código por correo
    significa que quien controle la bandeja puede entrar a las apps que no exigen TOTP).
    """
    if not Config.ACCESS_NOTIFY or not mailer.is_configured():
        return None
    forma = METODOS.get(metodo, 'verificación de identidad') + (' y código TOTP' if con_totp else '')
    destino = user.email
    cuerpo = (
        f'Hola {user.firstname},\n\n'
        f'Se inició sesión con tu cuenta en la aplicación «{app_nombre}» a través de NooxID.\n\n'
        f'  Cuándo:  {datetime.utcnow().strftime("%d/%m/%Y %H:%M")} UTC\n'
        f'  Cómo:    {forma}\n'
        f'  Cuenta:  {destino}\n\n'
        'Si fuiste tú, no tienes que hacer nada.\n'
        'Si no reconoces este acceso, avisa de inmediato al administrador de tu organización.\n'
    )

    def enviar():
        try:
            mailer.send_mail(destino, f'Nuevo acceso a {app_nombre} con NooxID', cuerpo)
        except Exception as e:   # un fallo del correo no debe afectar al acceso
            print(f'[NooxID] No se pudo enviar el aviso de acceso: {e}', file=sys.stderr)

    hilo = threading.Thread(target=enviar, daemon=True)
    hilo.start()
    return hilo


def is_member(user_id, app_id):
    """El usuario debe estar registrado y habilitado en la aplicación para autenticarse en ella."""
    return UserInApp.query.filter_by(id_usuario=user_id, id_app=app_id, status='enable').first() is not None


def app_auth_response(user, app, factor_ok, method):
    """Construye la respuesta de /face/verify-user y /otp/verify.

    `authenticated` es lo que debe mirar la app cliente. Sin TOTP coincide con el primer factor; con
    TOTP queda en False hasta canjear el reto en /face/verify-totp.
    """
    requires_totp = bool(app.get('requires_totp'))
    response = {
        'success': True,
        'user_id': user.id,
        'app_id': app['id'],
        'method': method,
        'authenticated': bool(factor_ok) and not requires_totp,
        'requires_totp': requires_totp,
        'totp_required': False,
        'totp_setup_required': False,
    }
    if factor_ok and requires_totp:
        if user.totp_enabled:
            response['totp_required'] = True
            response['challenge_token'] = totp_service.create_challenge(user.id, app['id'], method)
            response['message'] = 'Primer factor verificado. Falta el código del autenticador.'
        else:
            response['totp_setup_required'] = True
            response['message'] = ('Esta aplicación exige el autenticador (TOTP) y el usuario aún no '
                                   'lo ha configurado en NooxID.')
    if response['authenticated']:
        avisar_acceso(user, app['name_app'], method, False)
    return response
