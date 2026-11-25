from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configurar CORS para permitir requests desde el frontend React
    CORS(app, 
         origins=Config.CORS_ORIGINS,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'X-API-Key', 'X-App-ID'],
         supports_credentials=True,
         expose_headers=['Content-Type', 'Authorization'])
    
    # Manejar preflight requests manualmente
    @app.before_request
    def handle_preflight():
        from flask import request
        if request.method == "OPTIONS":
            from flask import make_response
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,X-API-Key,X-App-ID")
            response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
            return response
    
    # Inicializar extensiones
    db.init_app(app)
    
    # Crear directorio de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Registrar blueprints
    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.app_routes import app_bp
    from routes.face_recognition_routes import face_bp
    from routes.totp_routes import totp_bp
    from routes.otp_routes import otp_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(app_bp, url_prefix='/api/apps')
    app.register_blueprint(face_bp, url_prefix='/api/face')
    app.register_blueprint(totp_bp, url_prefix='/api/totp')
    app.register_blueprint(otp_bp, url_prefix='/api/otp')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Crear tablas si no existen y añadir columnas nuevas a las ya existentes (TOTP)
    with app.app_context():
        from sqlalchemy import inspect
        from migrations import ensure_schema, grandfather_existing_users, hash_existing_api_keys
        tabla_otp_existia = inspect(db.engine).has_table('email_otps')
        db.create_all()
        agregadas = ensure_schema(db)
        hash_existing_api_keys(db)
        import rbac
        rbac.seed()
        if not rbac.users_with_role('admin'):
            print('[NooxID] No hay administradores. Crea el primero con: python manage.py make-admin correo@empresa.com')
        # primera vez que se aplica la verificación de correo: tabla nueva o columna `purpose` recién añadida
        grandfather_existing_users(db, (not tabla_otp_existia) or 'email_otps.purpose' in agregadas)
    
    @app.route('/')
    def health_check():
        return {'status': 'OK', 'message': 'NooxID API está funcionando'}
    
    @app.route('/api/health')
    def api_health():
        return {'status': 'OK', 'service': 'NooxID API', 'version': '1.0.0'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
