"""
Creación de la base de datos NooxID

Ejecutar este script para crear las tablas iniciales
"""

from app import create_app
from models import db

def create_database():
    """Crear todas las tablas de la base de datos"""
    app = create_app()
    
    with app.app_context():
        print("🗄️ Creando tablas de la base de datos...")
        db.create_all()
        print("✅ Tablas creadas exitosamente:")
        print("   - users")
        print("   - apps") 
        print("   - userinapp")
        print("   - tokentoaccess")
        print("🎉 Base de datos NooxID lista para usar!")

if __name__ == '__main__':
    create_database()
