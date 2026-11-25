"""Código de un solo uso por correo: alternativa al rostro, siempre habilitada (sin contraseña).

- /api/otp/request y /api/otp/verify: para apps externas (X-API-Key + X-App-ID). Devuelven la misma
  respuesta que /api/face/verify-user, de modo que si la app exige TOTP el flujo sigue con /face/verify-totp.
- /api/otp/login/request y /api/otp/login/verify: inicio de sesión en el propio panel de NooxID (JWT).
"""
from datetime import datetime, timedelta

import jwt
from flask import Blueprint, request, jsonify

import mailer
import email_otp_service as otp
from auth_flow import app_auth_response
from config import Config
from models import User
from routes.face_recognition_routes import verify_api_key

otp_bp = Blueprint('otp', __name__)

GENERIC_SENT = 'Si el correo está registrado, enviamos un código. Revisa tu bandeja.'


def _send_code(email, app_name=None):
    """Envía el código sin revelar si el correo existe. Devuelve (respuesta, estado)."""
    user = User.query.filter_by(email=email).first()
    if not mailer.is_configured():
        return jsonify({'success': False, 'message': 'El envío de correo no está configurado en el servidor'}), 503
    if user:
        try:
            otp.issue(user, app_name)
        except otp.OtpRateLimited as e:
            return jsonify({'success': False, 'retry_after': e.retry_after,
                            'message': f'Espera {e.retry_after} s antes de pedir otro código'}), 429
        except mailer.MailError:
            return jsonify({'success': False, 'message': 'No se pudo enviar el correo. Inténtalo más tarde'}), 502
    return jsonify({'success': True, 'message': GENERIC_SENT,
                    'expires_in_minutes': Config.OTP_EMAIL_TTL_MINUTES}), 200


# ------------------------------------------------------------------ apps externas (API key)
@otp_bp.route('/request', methods=['POST'])
def request_code():
    app, error_response, status_code = verify_api_key()
    if error_response:
        return error_response, status_code
    data = request.get_json(silent=True) or {}
    if not data.get('user_email'):
        return jsonify({'success': False, 'message': 'user_email requerido'}), 400
    return _send_code(data['user_email'], app['name_app'])


@otp_bp.route('/verify', methods=['POST'])
def verify_code():
    app, error_response, status_code = verify_api_key()
    if error_response:
        return error_response, status_code
    data = request.get_json(silent=True) or {}
    if not data.get('user_email') or not data.get('code'):
        return jsonify({'success': False, 'message': 'user_email y code requeridos'}), 400

    user = User.query.filter_by(email=data['user_email']).first()
    ok = bool(user) and otp.verify(user, data['code'])
    if not ok:
        return jsonify({'success': False, 'authenticated': False,
                        'message': 'Código incorrecto o vencido'}), 401
    return jsonify(app_auth_response(user, app, True, 'email_otp')), 200


# ------------------------------------------------------------------ panel de NooxID (JWT)
@otp_bp.route('/login/request', methods=['POST'])
def login_request():
    data = request.get_json(silent=True) or {}
    if not data.get('email'):
        return jsonify({'success': False, 'message': 'Correo requerido'}), 400
    return _send_code(data['email'])


@otp_bp.route('/login/verify', methods=['POST'])
def login_verify():
    data = request.get_json(silent=True) or {}
    if not data.get('email') or not data.get('code'):
        return jsonify({'success': False, 'message': 'Correo y código requeridos'}), 400

    user = User.query.filter_by(email=data['email']).first()
    if not (user and otp.verify(user, data['code'])):
        return jsonify({'success': False, 'message': 'Código incorrecto o vencido'}), 401

    token = jwt.encode({'user_id': user.id, 'email': user.email,
                        'exp': datetime.utcnow() + timedelta(days=7)}, Config.SECRET_KEY, algorithm='HS256')
    return jsonify({'success': True, 'message': 'Inicio de sesión con código exitoso',
                    'token': token, 'user': user.to_dict()}), 200
