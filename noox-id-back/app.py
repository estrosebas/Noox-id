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
         origins=['http://localhost:5173', 'http://127.0.0.1:5173', 'https://attendanceperu.ooguy.com'],
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
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(app_bp, url_prefix='/api/apps')
    app.register_blueprint(face_bp, url_prefix='/api/face')
    
    # Crear tablas si no existen
    with app.app_context():
        db.create_all()
    
    @app.route('/')
    def health_check():
        return {'status': 'OK', 'message': 'NooxID API está funcionando'}
    
    @app.route('/api/health')
    def api_health():
        return {'status': 'OK', 'service': 'NooxID API', 'version': '1.0.0'}
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
