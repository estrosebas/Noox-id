# 🚀 NooxID - Sistema de Autenticación Facial

![NooxID Logo](https://img.shields.io/badge/NooxID-Facial_Auth-blue?style=for-the-badge&logo=security&logoColor=white)

## 📋 Descripción

**NooxID** es un sistema completo de autenticación multi-modal que incluye reconocimiento facial, autenticación tradicional y gestión de aplicaciones. Desarrollado con React (frontend) y Flask (backend).

## ✨ Características Principales

### 🔐 Autenticación Multi-Modal
- **Email/Password**: Login tradicional con validación
- **Google OAuth**: Integración con servicios de Google (preparado)  
- **Reconocimiento Facial**: Login usando análisis de rostro

### 👁️ Reconocimiento Facial Avanzado
- Procesamiento en tiempo real con OpenCV
- Encoding y comparación de rostros
- Tolerancia configurable
- Captura desde cámara web o upload de archivos

### 📱 Gestión de Aplicaciones
- CRUD completo de aplicaciones
- API keys automáticas con regeneración
- Control de acceso y verificación
- Dashboard de estadísticas

### 🎨 UI/UX Moderno
- Dark theme con animaciones fluidas
- Componentes responsivos
- Estados de carga y manejo de errores
- Navegación intuitiva

## 🏗️ Arquitectura

### Backend (`noox-id-back/`)
- **Framework**: Flask + SQLAlchemy
- **Base de Datos**: MySQL
- **Reconocimiento Facial**: OpenCV + face_recognition
- **Autenticación**: JWT tokens
- **API**: RESTful con documentación Postman

### Frontend (`noox-id/`)
- **Framework**: React + TypeScript
- **Build Tool**: Vite
- **Estado**: Context API
- **Animaciones**: Framer Motion
- **Iconos**: Lucide React
- **Estilos**: CSS Modules

## 🚀 Inicio Rápido

### Prerequisitos
- Python 3.8+ con pip
- Node.js 16+ con npm
- MySQL Server

### Opción 1: Script Automático (Windows)
```bash
# Ejecutar el script de inicio
start-noox.bat
```

### Opción 2: Script Automático (Linux/Mac)
```bash
# Hacer el script ejecutable
chmod +x start-noox.sh

# Ejecutar el script
./start-noox.sh
```

### Opción 3: Manual

#### Backend
```bash
cd noox-id-back

# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
python create_db.py

# Iniciar servidor
python main.py
```

#### Frontend
```bash
cd noox-id

# Instalar dependencias
npm install

# Iniciar desarrollo
npm run dev
```

## 🌐 URLs

- **Frontend**: http://localhost:5173/
- **Backend**: http://localhost:5000/
- **Health Check**: http://localhost:5000/health

## 📁 Estructura del Proyecto

```
DeNuevo-ptrm/
├── noox-id-back/                 # Backend Flask
│   ├── app.py                    # Aplicación principal
│   ├── models.py                 # Modelos SQLAlchemy
│   ├── crud.py                   # Operaciones CRUD
│   ├── face_recognition_service.py # Servicio de reconocimiento facial
│   ├── routes/                   # Endpoints de la API
│   ├── requirements.txt          # Dependencias Python
│   ├── create_db.py             # Script de base de datos
│   ├── NooxID_API_Tests.postman_collection.json # Tests Postman
│   ├── TESTING_GUIDE.md         # Guía de testing
│   └── README.md                # Documentación backend
├── noox-id/                     # Frontend React
│   ├── src/
│   │   ├── components/          # Componentes React
│   │   ├── contexts/           # Context API
│   │   ├── services/           # Servicios API
│   │   └── styles/            # Estilos CSS
│   ├── package.json           # Dependencias Node
│   ├── INTEGRATION_GUIDE.md   # Guía de integración
│   └── README.md             # Documentación frontend
├── start-noox.bat            # Script de inicio Windows
├── start-noox.sh             # Script de inicio Linux/Mac
└── README.md                 # Este archivo
```

## 🧪 Testing

### Postman Collection
```bash
# Importar en Postman:
# 1. Colección: noox-id-back/NooxID_API_Tests.postman_collection.json
# 2. Ambiente: noox-id-back/NooxID_Development.postman_environment.json

# Ver guía completa en:
noox-id-back/TESTING_GUIDE.md
```

### Frontend Testing
```bash
cd noox-id

# Build de producción
npm run build

# Linting
npm run lint
```

## 📚 Documentación

- **[Guía de Testing](noox-id-back/TESTING_GUIDE.md)**: Tests automatizados con Postman
- **[Guía de Integración](noox-id/INTEGRATION_GUIDE.md)**: Integración frontend-backend completa
- **[README Backend](noox-id-back/README.md)**: Documentación del API
- **[README Frontend](noox-id/README.md)**: Documentación de React

## 🔧 Configuración

### Variables de Entorno

#### Backend (`.env`)
```bash
# Base de datos
DATABASE_URL=mysql://usuario:password@localhost/nooxid
SECRET_KEY=tu_clave_secreta_aqui

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
```

#### Frontend (`.env`)
```bash
# API Backend
VITE_API_URL=http://localhost:5000

# Configuración de app
VITE_APP_NAME=NooxID
VITE_APP_VERSION=1.0.0
```

## 🔗 Endpoints Principales

### Autenticación
- `POST /api/auth/register` - Registro de usuario
- `POST /api/auth/login` - Login tradicional
- `POST /api/auth/face-login` - Login facial
- `POST /api/auth/google-auth` - Autenticación Google
- `GET /api/auth/verify-token` - Verificar token

### Usuarios
- `GET /api/users/profile` - Perfil del usuario
- `PUT /api/users/profile` - Actualizar perfil
- `POST /api/users/upload-face` - Subir imagen facial
- `POST /api/users/verify-face` - Verificar rostro

### Aplicaciones
- `GET /api/apps` - Listar apps del usuario
- `POST /api/apps` - Crear nueva app
- `PUT /api/apps/{id}` - Actualizar app
- `DELETE /api/apps/{id}` - Eliminar app
- `POST /api/apps/{id}/regenerate-key` - Regenerar API key

### Reconocimiento Facial
- `POST /api/face/compare` - Comparar dos rostros
- `POST /api/face/verify-user` - Verificar usuario por rostro
- `POST /api/face/set-tolerance` - Configurar tolerancia

## 🛠️ Desarrollo

### Tecnologías Utilizadas

#### Backend
- ![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
- ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-323232?style=flat-square&logo=sqlalchemy&logoColor=white)
- ![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white)
- ![OpenCV](https://img.shields.io/badge/OpenCV-27338e?style=flat-square&logo=OpenCV&logoColor=white)
- ![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=JSON%20web%20tokens&logoColor=white)

#### Frontend
- ![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
- ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
- ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)
- ![Framer Motion](https://img.shields.io/badge/Framer%20Motion-0055FF?style=flat-square&logo=framer&logoColor=white)

### Comandos de Desarrollo

```bash
# Backend
cd noox-id-back
python -m flask run --debug    # Modo desarrollo
python main.py                 # Modo producción

# Frontend
cd noox-id
npm run dev                     # Servidor desarrollo
npm run build                   # Build producción
npm run preview                 # Preview build
```

## 🔒 Seguridad

- **JWT Tokens**: Autenticación stateless
- **Password Hashing**: Bcrypt para contraseñas
- **CORS**: Configurado para desarrollo
- **Input Validation**: Validación en frontend y backend
- **SQL Injection**: Protección con SQLAlchemy ORM

## 📊 Base de Datos

### Tablas Principales
- **users**: Información de usuarios
- **apps**: Aplicaciones registradas
- **userinapp**: Relación usuario-aplicación
- **tokentoaccess**: Tokens de acceso

Ver schema completo en: `noox-id-back/models.py`

## 🚀 Deployment

### Desarrollo Local
1. Clonar repositorio
2. Ejecutar `start-noox.bat` (Windows) o `start-noox.sh` (Linux/Mac)
3. Abrir http://localhost:5173/

### Producción
- Backend: Configurar WSGI server (Gunicorn, uWSGI)
- Frontend: Build estático (`npm run build`)
- Base de datos: MySQL/PostgreSQL en producción
- Reverse proxy: Nginx recomendado

## 🤝 Contribución

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Licencia

Este proyecto es privado y no tiene licencia pública.

## 👨‍💻 Autor

Desarrollado con ❤️ para autenticación moderna y segura.

---

## 🎯 Estado del Proyecto

- ✅ **Backend completo** - API funcional con todos los endpoints
- ✅ **Frontend integrado** - UI moderna con funcionalidad real
- ✅ **Autenticación multi-modal** - Email, Google OAuth (preparado), Facial
- ✅ **Reconocimiento facial** - OpenCV con tolerancia configurable
- ✅ **Gestión de apps** - CRUD completo con API keys
- ✅ **Tests automatizados** - Colección Postman con validaciones
- ✅ **Documentación completa** - Guías y documentación técnica

**🚀 ¡El proyecto está listo para usar y expandir!**
