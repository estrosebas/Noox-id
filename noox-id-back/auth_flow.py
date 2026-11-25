"""Respuesta común a las apps cliente después del primer factor (rostro o código por correo)."""
import totp_service


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
            response['challenge_token'] = totp_service.create_challenge(user.id, app['id'])
            response['message'] = 'Primer factor verificado. Falta el código del autenticador.'
        else:
            response['totp_setup_required'] = True
            response['message'] = ('Esta aplicación exige el autenticador (TOTP) y el usuario aún no '
                                   'lo ha configurado en NooxID.')
    return response
