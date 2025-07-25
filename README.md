# NooxID - Manual de Usuario e Instalación

## Descripción General

NooxID es una plataforma de autenticación y gestión de usuarios con reconocimiento facial, compuesta por:
- **Frontend**: SPA en React + TypeScript (carpeta `noox-id`)
- **Backend**: API REST en Flask + SQLAlchemy + face_recognition (carpeta `noox-id-back`)

Permite autenticación tradicional, Google y facial, gestión de usuarios, apps y API keys.

---

## Instalación y Uso Local

### 1. Requisitos
- Python 3.9+
- Node.js 18+
- MySQL Server
- Git

### 2. Clonar el repositorio
```bash
git clone <URL_DEL_REPO>
cd DeNuevo-ptrm
```

### 3. Backend (noox-id-back)
```bash
cd noox-id-back
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

Configura `.env` con tus datos de MySQL y clave secreta:
```
DATABASE_URL=mysql+pymysql://usuario:password@localhost/nooxid
SECRET_KEY=clave-secreta
FLASK_ENV=development
```

Crea la base de datos y tablas:
```bash
mysql -u root -p -e "CREATE DATABASE nooxid;"
python create_db.py
```

Inicia el backend:
```bash
python main.py
```

### 4. Frontend (noox-id)
```bash
cd ../noox-id
npm install
npm run dev
```

Accede a `http://localhost:5173` para usar la app.

---

## Manual de Usuario

1. **Registro**: Ingresa tus datos y una imagen facial. Puedes usar email/password o Google.
2. **Login**: Accede con email/password, Google o reconocimiento facial.
3. **Dashboard**: Gestiona tu perfil, apps y usuarios. Sube nuevas imágenes faciales.
4. **API**: Integra tus apps usando las API keys generadas desde el dashboard.

---

## Despliegue en Producción (Linux Ubuntu)

### 1. Requisitos
- Dominio apuntando a tu servidor
- Apache2
- Certbot (Let's Encrypt)
- tmux
- Python 3.9+, Node.js 18+, MySQL

### 2. Backend (Flask) con Apache2 + WSGI

#### a) Instala dependencias
```bash
sudo apt update && sudo apt install python3-venv python3-pip apache2 libapache2-mod-wsgi-py3 tmux certbot python3-certbot-apache mysql-server
```

#### b) Configura entorno y dependencias
```bash
cd /ruta/DeNuevo-ptrm/noox-id-back
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### c) Configura variables en `.env` (usa claves seguras y FLASK_ENV=production)

#### d) Configura Apache2 para servir solo el frontend en el puerto 5071
Crea `/etc/apache2/sites-available/nooxid-frontend.conf`:
```
<VirtualHost *:5071>
    ServerName tu-dominio.com
    DocumentRoot /ruta/DeNuevo-ptrm/noox-id/dist
    <Directory /ruta/DeNuevo-ptrm/noox-id/dist>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog ${APACHE_LOG_DIR}/nooxid_front_error.log
    CustomLog ${APACHE_LOG_DIR}/nooxid_front_access.log combined
</VirtualHost>
```

Habilita el sitio y el puerto, y reinicia Apache:
```bash
sudo a2ensite nooxid-frontend
sudo sed -i '/^Listen 5071$/d' /etc/apache2/ports.conf && echo 'Listen 5071' | sudo tee -a /etc/apache2/ports.conf
sudo systemctl reload apache2
```

Ahora el frontend estará disponible en `http://tu-dominio.com:5071/`.

### 3. Certificado SSL con Certbot
```bash
sudo certbot --apache -d tu-dominio.com
```

### 4. Frontend (Vite/React) en producción
```bash
cd /ruta/DeNuevo-ptrm/noox-id
npm install
npm run build
```

Configura Apache para servir `/dist` como sitio estático o usa un servicio como Vercel/Netlify.

### 5. Mantén procesos activos con tmux
```bash
tmux new -s nooxid
# Inicia backend o frontend manualmente si no usas Apache/WSGI
python main.py
# o
npm run preview
# Para salir de tmux sin detener procesos: Ctrl+B luego D
```

---

## Seguridad y Buenas Prácticas
- Usa claves y contraseñas seguras en `.env`
- No subas `.env`, `uploads/`, ni `node_modules/` a GitHub
- Haz respaldos periódicos de la base de datos
- Mantén actualizado el sistema y dependencias

---

## Estructura de Carpetas
```
DeNuevo-ptrm/
├── noox-id-back/   # Backend Flask
├── noox-id/        # Frontend React
└── README.md       # Este manual
```

---

**NooxID** - Autenticación facial y gestión de usuarios.
