from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)  # Nullable para usuarios de Google
    googleid = db.Column(db.String(255), unique=True, nullable=True)
    base64imageprofile = db.Column(db.Text, nullable=True)  # MEDIUMTEXT
    base64vector = db.Column(db.Text, nullable=True)  # MEDIUMTEXT - Vector facial
    ProfilePickPath = db.Column(db.String(500), nullable=True)
    # Segundo factor TOTP. El secreto se guarda cifrado (ver totp_service) y nunca sale en to_dict().
    totp_secret = db.Column(db.Text, nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    totp_last_step = db.Column(db.BigInteger, default=0, nullable=False, server_default='0')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    owned_apps = db.relationship('App', backref='owner_user', lazy=True)
    user_apps = db.relationship('UserInApp', backref='user', lazy=True)
    access_tokens = db.relationship('TokenToAccess', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'verified': self.verified,
            'email': self.email,
            'googleid': self.googleid,
            'ProfilePickPath': self.ProfilePickPath,
            'totp_enabled': bool(self.totp_enabled),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class App(db.Model):
    __tablename__ = 'apps'
    
    id = db.Column(db.Integer, primary_key=True)
    name_app = db.Column(db.String(200), nullable=False)
    owner = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    api_key = db.Column(db.String(255), unique=True, nullable=False)
    last_edit = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    IconAppPath = db.Column(db.String(500), nullable=True)
    # Si es True, tras validar el rostro se exige además un código TOTP (p. ej. app de administración).
    requires_totp = db.Column(db.Boolean, default=False, nullable=False, server_default='0')

    # Relaciones
    user_apps = db.relationship('UserInApp', backref='app', lazy=True)
    
    def __init__(self, **kwargs):
        super(App, self).__init__(**kwargs)
        if not self.api_key:
            self.api_key = self.generate_api_key()
    
    def generate_api_key(self):
        return f"noox_{secrets.token_urlsafe(32)}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name_app': self.name_app,
            'owner': self.owner,
            'api_key': self.api_key,
            'last_edit': self.last_edit.isoformat() if self.last_edit else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_verified': self.is_verified,
            'IconAppPath': self.IconAppPath,
            'requires_totp': bool(self.requires_totp)
        }

class UserInApp(db.Model):
    __tablename__ = 'userinapp'
    
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    id_app = db.Column(db.Integer, db.ForeignKey('apps.id'), nullable=False)
    status = db.Column(db.Enum('enable', 'disable', name='status_enum'), default='enable', nullable=False)
    registerAt = db.Column(db.DateTime, default=datetime.utcnow)
    TokenToAcces = db.Column(db.Integer, db.ForeignKey('tokentoaccess.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'id_usuario': self.id_usuario,
            'id_app': self.id_app,
            'status': self.status,
            'registerAt': self.registerAt.isoformat() if self.registerAt else None,
            'TokenToAcces': self.TokenToAcces
        }

class EmailOtp(db.Model):
    """Código de un solo uso enviado por correo (se guarda su hash, no el código)."""
    __tablename__ = 'email_otps'

    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    # 'register' = enviado al registrarse; 'login' = código de acceso. Decide qué pasa al verificar un correo nuevo.
    purpose = db.Column(db.String(10), default='login', nullable=False, server_default='login')
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TokenToAccess(db.Model):
    __tablename__ = 'tokentoaccess'
    
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    profilePick = db.Column(db.Boolean, default=False, nullable=False)
    email = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relación inversa
    user_in_apps = db.relationship('UserInApp', backref='access_token', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'id_usuario': self.id_usuario,
            'profilePick': self.profilePick,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
