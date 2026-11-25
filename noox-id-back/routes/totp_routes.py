from flask import Blueprint, request, jsonify
from datetime import datetime

import totp_service
from models import db, User
from routes.app_routes import verify_token_decorator

totp_bp = Blueprint('totp', __name__)


def _current_user():
    return User.query.get(request.current_user_id)


def _check_code(user, secret, code):
    """Valida un código aplicando bloqueo y anti-reutilización. Devuelve (ok, respuesta_error)."""
    wait = totp_service.lock_remaining(user.id)
    if wait:
        return False, (jsonify({'success': False,
                                'message': f'Demasiados intentos fallidos. Espera {wait} s e inténtalo de nuevo.',
                                'retry_after': wait}), 429)
    step = totp_service.verify_code(secret, code, last_step=user.totp_last_step or 0)
    if step is None:
        totp_service.register_failure(user.id)
        return False, (jsonify({'success': False, 'message': 'Código incorrecto o vencido'}), 400)
    totp_service.clear_failures(user.id)
    user.totp_last_step = step
    return True, None


@totp_bp.route('/status', methods=['GET'])
@verify_token_decorator
def status():
    user = _current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
    return jsonify({'success': True, 'enabled': bool(user.totp_enabled),
                    'pending': bool(user.totp_secret and not user.totp_enabled)}), 200


@totp_bp.route('/setup', methods=['POST'])
@verify_token_decorator
def setup():
    """Genera un secreto nuevo (aún sin activar). El usuario lo escanea y confirma con /enable."""
    try:
        user = _current_user()
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        if user.totp_enabled:
            return jsonify({'success': False,
                            'message': 'El autenticador ya está activo. Desactívalo antes de configurar otro.'}), 409

        secret = totp_service.generate_secret()
        user.totp_secret = totp_service.encrypt_secret(secret)
        user.totp_enabled = False
        user.totp_last_step = 0
        user.updated_at = datetime.utcnow()
        db.session.commit()

        uri = totp_service.provisioning_uri(secret, user.email)
        return jsonify({
            'success': True,
            'secret': secret,   # para ingresarlo a mano si no se puede escanear el QR
            'otpauth_uri': uri,
            'qr': totp_service.qr_data_url(uri),
            'message': 'Escanea el código QR con tu app autenticadora y confirma con un código'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@totp_bp.route('/enable', methods=['POST'])
@verify_token_decorator
def enable():
    """Activa el autenticador comprobando un código generado con el secreto pendiente."""
    try:
        user = _current_user()
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        if user.totp_enabled:
            return jsonify({'success': False, 'message': 'El autenticador ya está activo'}), 409
        if not user.totp_secret:
            return jsonify({'success': False, 'message': 'Primero inicia la configuración'}), 400

        secret = totp_service.decrypt_secret(user.totp_secret)
        if not secret:
            return jsonify({'success': False, 'message': 'Secreto ilegible: reinicia la configuración'}), 500

        data = request.get_json(silent=True) or {}
        ok, error = _check_code(user, secret, data.get('code'))
        if not ok:
            db.session.rollback()
            return error

        user.totp_enabled = True
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'enabled': True, 'message': 'Autenticador activado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@totp_bp.route('/disable', methods=['POST'])
@verify_token_decorator
def disable():
    """Desactiva el autenticador; exige un código vigente para que una sesión robada no pueda quitarlo."""
    try:
        user = _current_user()
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        if not user.totp_enabled:
            return jsonify({'success': False, 'message': 'El autenticador no está activo'}), 400

        secret = totp_service.decrypt_secret(user.totp_secret or '')
        if not secret:
            return jsonify({'success': False, 'message': 'Secreto ilegible'}), 500

        data = request.get_json(silent=True) or {}
        ok, error = _check_code(user, secret, data.get('code'))
        if not ok:
            db.session.rollback()
            return error

        user.totp_enabled = False
        user.totp_secret = None
        user.totp_last_step = 0
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'enabled': False, 'message': 'Autenticador desactivado'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
