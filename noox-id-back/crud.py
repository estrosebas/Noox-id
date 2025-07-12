from models import db, User, App, UserInApp, TokenToAccess
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import bcrypt

class UserCRUD:
    @staticmethod
    def create_user(data):
        """Crear un nuevo usuario"""
        try:
            # Hashear la contraseña si se proporciona
            password_hash = None
            if data.get('password'):
                password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user = User(
                firstname=data['firstname'],
                lastname=data['lastname'],
                email=data['email'],
                password=password_hash,
                googleid=data.get('googleid'),
                verified=data.get('verified', False),
                base64imageprofile=data.get('base64imageprofile'),
                base64vector=data.get('base64vector'),
                ProfilePickPath=data.get('ProfilePickPath')
            )
            
            db.session.add(user)
            db.session.commit()
            return {'success': True, 'user': user.to_dict(), 'message': 'Usuario creado exitosamente'}
            
        except IntegrityError as e:
            db.session.rollback()
            return {'success': False, 'message': 'Email ya existe o error de integridad'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_user_by_id(user_id):
        """Obtener usuario por ID"""
        try:
            user = User.query.get(user_id)
            if user:
                return {'success': True, 'user': user.to_dict()}
            return {'success': False, 'message': 'Usuario no encontrado'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_user_by_email(email):
        """Obtener usuario por email"""
        try:
            user = User.query.filter_by(email=email).first()
            if user:
                return {'success': True, 'user': user.to_dict(), 'user_obj': user}
            return {'success': False, 'message': 'Usuario no encontrado'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_all_users(page=1, per_page=10):
        """Obtener todos los usuarios con paginación"""
        try:
            users = User.query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                'success': True,
                'users': [user.to_dict() for user in users.items],
                'total': users.total,
                'pages': users.pages,
                'current_page': page
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def update_user(user_id, data):
        """Actualizar usuario"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'message': 'Usuario no encontrado'}
            
            # Actualizar campos permitidos
            if 'firstname' in data:
                user.firstname = data['firstname']
            if 'lastname' in data:
                user.lastname = data['lastname']
            if 'email' in data:
                user.email = data['email']
            if 'verified' in data:
                user.verified = data['verified']
            if 'password' in data and data['password']:
                user.password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            if 'base64imageprofile' in data:
                user.base64imageprofile = data['base64imageprofile']
            if 'base64vector' in data:
                user.base64vector = data['base64vector']
            if 'ProfilePickPath' in data:
                user.ProfilePickPath = data['ProfilePickPath']
            
            user.updated_at = datetime.utcnow()
            db.session.commit()
            return {'success': True, 'user': user.to_dict(), 'message': 'Usuario actualizado exitosamente'}
            
        except IntegrityError:
            db.session.rollback()
            return {'success': False, 'message': 'Email ya existe'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def delete_user(user_id):
        """Eliminar usuario"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'message': 'Usuario no encontrado'}
            
            db.session.delete(user)
            db.session.commit()
            return {'success': True, 'message': 'Usuario eliminado exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def verify_password(email, password):
        """Verificar contraseña del usuario"""
        try:
            user = User.query.filter_by(email=email).first()
            if user and user.password:
                if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                    return {'success': True, 'user': user.to_dict()}
            return {'success': False, 'message': 'Credenciales inválidas'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

class AppCRUD:
    @staticmethod
    def create_app(data):
        """Crear una nueva aplicación"""
        try:
            app = App(
                name_app=data['name_app'],
                owner=data['owner'],
                is_verified=data.get('is_verified', False),
                IconAppPath=data.get('IconAppPath')
            )
            
            db.session.add(app)
            db.session.commit()
            return {'success': True, 'app': app.to_dict(), 'message': 'Aplicación creada exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_app_by_id(app_id):
        """Obtener aplicación por ID"""
        try:
            app = App.query.get(app_id)
            if app:
                return {'success': True, 'app': app.to_dict()}
            return {'success': False, 'message': 'Aplicación no encontrada'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_apps_by_owner(owner_id, page=1, per_page=10):
        """Obtener aplicaciones por propietario"""
        try:
            apps = App.query.filter_by(owner=owner_id).paginate(page=page, per_page=per_page, error_out=False)
            return {
                'success': True,
                'apps': [app.to_dict() for app in apps.items],
                'total': apps.total,
                'pages': apps.pages,
                'current_page': page
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_all_apps(page=1, per_page=10):
        """Obtener todas las aplicaciones"""
        try:
            apps = App.query.paginate(page=page, per_page=per_page, error_out=False)
            return {
                'success': True,
                'apps': [app.to_dict() for app in apps.items],
                'total': apps.total,
                'pages': apps.pages,
                'current_page': page
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def update_app(app_id, data):
        """Actualizar aplicación"""
        try:
            app = App.query.get(app_id)
            if not app:
                return {'success': False, 'message': 'Aplicación no encontrada'}
            
            if 'name_app' in data:
                app.name_app = data['name_app']
            if 'is_verified' in data:
                app.is_verified = data['is_verified']
            if 'IconAppPath' in data:
                app.IconAppPath = data['IconAppPath']
            
            app.last_edit = datetime.utcnow()
            db.session.commit()
            return {'success': True, 'app': app.to_dict(), 'message': 'Aplicación actualizada exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def delete_app(app_id):
        """Eliminar aplicación"""
        try:
            app = App.query.get(app_id)
            if not app:
                return {'success': False, 'message': 'Aplicación no encontrada'}
            
            db.session.delete(app)
            db.session.commit()
            return {'success': True, 'message': 'Aplicación eliminada exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def regenerate_api_key(app_id):
        """Regenerar API key de la aplicación"""
        try:
            app = App.query.get(app_id)
            if not app:
                return {'success': False, 'message': 'Aplicación no encontrada'}
            
            app.api_key = app.generate_api_key()
            app.last_edit = datetime.utcnow()
            db.session.commit()
            return {'success': True, 'app': app.to_dict(), 'message': 'API key regenerada exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}

class UserInAppCRUD:
    @staticmethod
    def create_user_in_app(data):
        """Crear relación usuario-aplicación"""
        try:
            user_in_app = UserInApp(
                id_usuario=data['id_usuario'],
                id_app=data['id_app'],
                status=data.get('status', 'enable'),
                TokenToAcces=data.get('TokenToAcces')
            )
            
            db.session.add(user_in_app)
            db.session.commit()
            return {'success': True, 'user_in_app': user_in_app.to_dict(), 'message': 'Relación creada exitosamente'}
            
        except IntegrityError:
            db.session.rollback()
            return {'success': False, 'message': 'El usuario ya está registrado en esta aplicación'}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_user_apps(user_id, page=1, per_page=10):
        """Obtener aplicaciones de un usuario"""
        try:
            user_apps = UserInApp.query.filter_by(id_usuario=user_id).paginate(page=page, per_page=per_page, error_out=False)
            return {
                'success': True,
                'user_apps': [ua.to_dict() for ua in user_apps.items],
                'total': user_apps.total,
                'pages': user_apps.pages,
                'current_page': page
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_app_users(app_id, page=1, per_page=10):
        """Obtener usuarios de una aplicación"""
        try:
            app_users = UserInApp.query.filter_by(id_app=app_id).paginate(page=page, per_page=per_page, error_out=False)
            return {
                'success': True,
                'app_users': [au.to_dict() for au in app_users.items],
                'total': app_users.total,
                'pages': app_users.pages,
                'current_page': page
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def update_user_in_app_status(user_id, app_id, status):
        """Actualizar estado de usuario en aplicación"""
        try:
            user_in_app = UserInApp.query.filter_by(id_usuario=user_id, id_app=app_id).first()
            if not user_in_app:
                return {'success': False, 'message': 'Relación no encontrada'}
            
            user_in_app.status = status
            db.session.commit()
            return {'success': True, 'user_in_app': user_in_app.to_dict(), 'message': 'Estado actualizado exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def delete_user_in_app(user_id, app_id):
        """Eliminar relación usuario-aplicación"""
        try:
            user_in_app = UserInApp.query.filter_by(id_usuario=user_id, id_app=app_id).first()
            if not user_in_app:
                return {'success': False, 'message': 'Relación no encontrada'}
            
            db.session.delete(user_in_app)
            db.session.commit()
            return {'success': True, 'message': 'Relación eliminada exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}

class TokenToAccessCRUD:
    @staticmethod
    def create_token(data):
        """Crear token de acceso"""
        try:
            # Calcular fecha de expiración (por defecto 30 días)
            expires_at = datetime.utcnow() + timedelta(days=data.get('days_to_expire', 30))
            
            token = TokenToAccess(
                id_usuario=data['id_usuario'],
                profilePick=data.get('profilePick', False),
                email=data.get('email', False),
                expires_at=expires_at
            )
            
            db.session.add(token)
            db.session.commit()
            return {'success': True, 'token': token.to_dict(), 'message': 'Token creado exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_token_by_id(token_id):
        """Obtener token por ID"""
        try:
            token = TokenToAccess.query.get(token_id)
            if token:
                return {'success': True, 'token': token.to_dict()}
            return {'success': False, 'message': 'Token no encontrado'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_user_tokens(user_id, page=1, per_page=10):
        """Obtener tokens de un usuario"""
        try:
            tokens = TokenToAccess.query.filter_by(id_usuario=user_id).paginate(page=page, per_page=per_page, error_out=False)
            return {
                'success': True,
                'tokens': [token.to_dict() for token in tokens.items],
                'total': tokens.total,
                'pages': tokens.pages,
                'current_page': page
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def update_token(token_id, data):
        """Actualizar token"""
        try:
            token = TokenToAccess.query.get(token_id)
            if not token:
                return {'success': False, 'message': 'Token no encontrado'}
            
            if 'profilePick' in data:
                token.profilePick = data['profilePick']
            if 'email' in data:
                token.email = data['email']
            if 'expires_at' in data:
                token.expires_at = data['expires_at']
            
            db.session.commit()
            return {'success': True, 'token': token.to_dict(), 'message': 'Token actualizado exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def delete_token(token_id):
        """Eliminar token"""
        try:
            token = TokenToAccess.query.get(token_id)
            if not token:
                return {'success': False, 'message': 'Token no encontrado'}
            
            db.session.delete(token)
            db.session.commit()
            return {'success': True, 'message': 'Token eliminado exitosamente'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def is_token_valid(token_id):
        """Verificar si un token es válido"""
        try:
            token = TokenToAccess.query.get(token_id)
            if not token:
                return {'success': False, 'valid': False, 'message': 'Token no encontrado'}
            
            is_valid = token.expires_at is None or token.expires_at > datetime.utcnow()
            return {
                'success': True, 
                'valid': is_valid, 
                'token': token.to_dict(),
                'message': 'Token válido' if is_valid else 'Token expirado'
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
