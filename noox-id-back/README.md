# NooxID Backend

Sistema de autenticación e identificación facial desarrollado con Flask, SQLAlchemy y OpenCV (YuNet + SFace).

## 🚀 Características

- **Autenticación múltiple**: Tradicional (email/password), Google OAuth y reconocimiento facial
- **Gestión de usuarios**: CRUD completo con perfiles y imágenes faciales
- **Sistema de aplicaciones**: Gestión de apps con API keys para integración
- **Reconocimiento facial**: Comparación y verificación de rostros en tiempo real
- **API REST**: Endpoints documentados para todas las funcionalidades
- **Base de datos MySQL**: Esquema optimizado para escalabilidad

## 📦 Instalación

1. **Clonar e instalar dependencias**:
```bash
cd noox-id-back
pip install -r requirements.txt
```

2. **Configurar base de datos**:
Editar el archivo `.env`:
```env
DATABASE_URL=mysql+pymysql://root:password@localhost/nooxid
SECRET_KEY=tu-clave-secreta-aqui
FLASK_ENV=development
```

3. **Crear base de datos**:
```bash
python create_db.py
```

4. **Ejecutar servidor**:
```bash
python main.py
```

El servidor estará disponible en `http://localhost:5000`

## 🗄️ Esquema de Base de Datos

### Tabla `users`
- `id` (INT, PK)
- `firstname` (VARCHAR)
- `lastname` (VARCHAR)
- `verified` (BOOLEAN)
- `email` (VARCHAR, UNIQUE)
- `password` (VARCHAR, hashed)
- `googleid` (VARCHAR, UNIQUE)
- `base64imageprofile` (MEDIUMTEXT)
- `base64vector` (MEDIUMTEXT) - Vector facial
- `ProfilePickPath` (VARCHAR)

### Tabla `apps`
- `id` (INT, PK)
- `name_app` (VARCHAR)
- `owner` (INT, FK to users.id)
- `api_key` (VARCHAR, UNIQUE)
- `last_edit` (DATETIME)
- `created_at` (DATETIME)
- `is_verified` (BOOLEAN)
- `IconAppPath` (VARCHAR)

### Tabla `userinapp`
- `id` (INT, PK)
- `id_usuario` (INT, FK to users.id)
- `id_app` (INT, FK to apps.id)
- `status` (ENUM: 'enable', 'disable')
- `registerAt` (DATETIME)
- `TokenToAcces` (INT, FK to tokentoaccess.id)

### Tabla `tokentoaccess`
- `id` (INT, PK)
- `id_usuario` (INT, FK to users.id)
- `profilePick` (BOOLEAN)
- `email` (BOOLEAN)
- `created_at` (DATETIME)
- `expires_at` (DATETIME)

## 🔗 API Endpoints

### Autenticación (`/api/auth`)
- `POST /register` - Registrar nuevo usuario
- `POST /login` - Iniciar sesión tradicional
- `POST /face-login` - Iniciar sesión con reconocimiento facial
- `POST /verify-token` - Verificar token JWT
- `POST /google-auth` - Autenticación con Google

### Usuarios (`/api/users`)
- `GET /` - Listar usuarios (paginado)
- `GET /<id>` - Obtener usuario por ID
- `GET /profile` - Obtener perfil actual
- `PUT /profile` - Actualizar perfil actual
- `POST /upload-face` - Subir imagen facial
- `POST /verify-face` - Verificar rostro actual
- `GET /search` - Buscar usuarios

### Aplicaciones (`/api/apps`)
- `POST /` - Crear aplicación
- `GET /` - Listar apps del usuario
- `GET /<id>` - Obtener app por ID
- `PUT /<id>` - Actualizar aplicación
- `DELETE /<id>` - Eliminar aplicación
- `POST /<id>/regenerate-key` - Regenerar API key
- `POST /<id>/users` - Agregar usuario a app
- `GET /<id>/users` - Listar usuarios de app

### Reconocimiento Facial (`/api/face`)
- `POST /compare` - Comparar dos rostros (requiere API key)
- `POST /verify-user` - Verificar usuario por rostro (requiere API key)
- `POST /extract-encoding` - Extraer encoding facial (requiere API key)
- `POST /process-profile-image` - Procesar imagen de perfil
- `GET|POST /tolerance` - Gestionar tolerancia de reconocimiento

## 🔑 Autenticación

### JWT Tokens (Endpoints internos)
```bash
Authorization: Bearer <jwt-token>
```

### API Keys (Endpoints públicos de reconocimiento)
```bash
X-API-Key: <api-key>
X-App-ID: <app-id>
```

## 💡 Uso del Reconocimiento Facial

### 1. Registrar usuario con imagen facial:
```python
import requests
import base64

# Convertir imagen a base64
with open("imagen.jpg", "rb") as img_file:
    img_base64 = base64.b64encode(img_file.read()).decode()

data = {
    "firstname": "Juan",
    "lastname": "Pérez", 
    "email": "juan@example.com",
    "password": "password123",
    "base64imageprofile": img_base64
}

response = requests.post("http://localhost:5000/api/auth/register", json=data)
```

### 2. Comparar dos rostros:
```python
data = {
    "face1": img1_base64,
    "face2": img2_base64
}

headers = {
    "X-API-Key": "noox_tu_api_key",
    "X-App-ID": "1"
}

response = requests.post("http://localhost:5000/api/face/compare", json=data, headers=headers)
```

### 3. Verificar usuario por rostro:
```python
data = {
    "user_email": "juan@example.com",
    "face_image": img_base64
}

response = requests.post("http://localhost:5000/api/face/verify-user", json=data, headers=headers)
```

## 🛠️ Desarrollo

### Estructura del proyecto:
```
noox-id-back/
├── app.py              # Aplicación Flask principal
├── models.py           # Modelos SQLAlchemy
├── crud.py             # Operaciones CRUD
├── config.py           # Configuración
├── face_recognition_service.py  # Servicio de reconocimiento facial
├── routes/             # Rutas de la API
│   ├── auth_routes.py
│   ├── user_routes.py
│   ├── app_routes.py
│   └── face_recognition_routes.py
├── requirements.txt    # Dependencias
├── .env               # Variables de entorno
└── create_db.py       # Script creación DB
```

### Agregar nuevas funcionalidades:
1. Crear nuevos modelos en `models.py`
2. Agregar operaciones CRUD en `crud.py`
3. Crear rutas en el directorio `routes/`
4. Registrar blueprints en `app.py`

## 🔒 Seguridad

- Contraseñas hasheadas con bcrypt
- Tokens JWT con expiración
- API keys generadas aleatoriamente
- Validación de permisos por usuario/aplicación
- Manejo seguro de imágenes en base64

## 📊 Monitoreo

- Logs de actividad
- Métricas de reconocimiento facial
- Estado de aplicaciones y usuarios
- Validación de tokens de acceso

## 🚀 Producción

Para despliegue en producción:

1. Cambiar `FLASK_ENV=production` en `.env`
2. Usar servidor WSGI como Gunicorn
3. Configurar proxy reverso (Nginx)
4. Habilitar HTTPS
5. Configurar base de datos en la nube
6. Implementar respaldos automáticos

---

**NooxID** - Sistema de autenticación facial de próxima generación 🔐👁️
