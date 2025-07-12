"""
NooxID - Sistema de autenticación e identificación facial

Este es un backend desarrollado con Flask y SQLAlchemy que proporciona:
- Gestión de usuarios con autenticación tradicional y facial
- Sistema de aplicaciones con API keys
- Reconocimiento y comparación facial basado en face_recognition
- CRUDs completos para todas las entidades

Instalación:
1. pip install -r requirements.txt
2. Configurar base de datos MySQL en .env
3. Crear base de datos y tablas ejecutando create_db.py
4. Ejecutar el servidor con: python app.py

Uso:
- API REST con endpoints documentados
- Autenticación JWT para endpoints internos
- API keys para endpoints públicos de reconocimiento facial
"""

from app import create_app

if __name__ == '__main__':
    app = create_app()
    print("🚀 NooxID Backend iniciado")
    print("📱 Reconocimiento facial disponible")
    print("🔑 Gestión de usuarios y aplicaciones")
    print("🌐 Servidor corriendo en http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
"""
app.run(
    debug=True,
    host='0.0.0.0',
    port=5041,
    ssl_context=(
        '/etc/letsencrypt/live/attendanceperu.ooguy.com/fullchain.pem',
        '/etc/letsencrypt/live/attendanceperu.ooguy.com/privkey.pem'
    )
)
"""