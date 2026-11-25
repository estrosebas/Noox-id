# 🚀 Guía de Integración Frontend-Backend NooxID

## ✅ ¿Qué se ha implementado?

### 🔗 **Integración Completa**
Se ha implementado la integración completa entre el frontend React y el backend Flask, reemplazando toda la lógica de template con llamadas reales a la API.

### 🏗️ **Arquitectura Implementada**

#### **Backend (noox-id-back/)**
- ✅ Flask + SQLAlchemy + MySQL
- ✅ Endpoints completos para autenticación, usuarios, apps, reconocimiento facial
- ✅ Colección Postman con tests automatizados
- ✅ Base de datos con schema completo
- ✅ Servicio de reconocimiento facial con Python

#### **Frontend (noox-id/)**
- ✅ React + TypeScript + Vite
- ✅ Context API para manejo de estado de autenticación
- ✅ Servicios modulares para todas las APIs
- ✅ Componentes integrados con funcionalidad real
- ✅ UI moderna con animaciones (Framer Motion)

### 📁 **Servicios Implementados**

#### **1. AuthContext (src/contexts/AuthContext.tsx)**
Maneja el estado global de autenticación:
- ✅ Login tradicional (email/password)
- ✅ Login con Google OAuth
- ✅ Login con reconocimiento facial
- ✅ Registro de usuarios
- ✅ Verificación de tokens JWT
- ✅ Logout y limpieza de sesión
- ✅ Persistencia automática de tokens

#### **2. Servicios API (src/services/)**
- ✅ **authService.ts** - Autenticación y tokens
- ✅ **userService.ts** - CRUD usuarios, perfil, imágenes faciales
- ✅ **appService.ts** - Gestión de aplicaciones y API keys
- ✅ **faceService.ts** - Reconocimiento facial y comparación
- ✅ **tokenService.ts** - Tokens de acceso
- ✅ **api.ts** - Configuración, tipos y helpers

#### **3. Componentes Actualizados**

##### **AuthPage (src/components/AuthPage.tsx)**
- ✅ Login tradicional con validación
- ✅ Registro de usuarios con formulario completo
- ✅ Login facial (con email + imagen)
- ✅ Integración con Google OAuth (preparado)
- ✅ Manejo de errores y estados de carga
- ✅ UI con tabs para diferentes métodos

##### **ProfileSection (src/components/sections/ProfileSection.tsx)**
- ✅ Información real del usuario desde la API
- ✅ Estadísticas dinámicas (apps, verificación, etc.)
- ✅ Formulario de actualización de perfil
- ✅ Upload de imagen facial
- ✅ Estado de verificación en tiempo real

##### **AppsSection (src/components/sections/AppsSection.tsx)**
- ✅ Lista real de aplicaciones del usuario
- ✅ Crear, editar y eliminar aplicaciones
- ✅ Gestión de API keys (mostrar/ocultar, copiar, regenerar)
- ✅ Estados de verificación de apps
- ✅ Timestamps y metadata completa

##### **FaceSection (src/components/sections/FaceSection.tsx)**
- ✅ Captura desde cámara web
- ✅ Upload de imágenes faciales
- ✅ Verificación de rostros
- ✅ Configuración de tolerancia
- ✅ Preview de imágenes
- ✅ Resultados detallados de verificación

### 🔧 **Funcionalidades Clave**

#### **Autenticación Multi-Modal**
1. **Email/Password**: Login tradicional con validación
2. **Google**: botón oficial «Sign in with Google». El navegador envía el ID token que firma Google a
   `POST /api/auth/google-auth` (`{"id_token": "..."}`) y el servidor lo verifica con Google, comprueba que
   fue emitido para esta app (`aud`) y que el correo está verificado; el correo y el `googleid` salen del
   token, nunca de lo que mande el cliente. Requiere el mismo ID de cliente OAuth en `GOOGLE_CLIENT_ID`
   (backend, `.env`) y `VITE_GOOGLE_CLIENT_ID` (frontend); sin él el acceso con Google queda deshabilitado
   (503). Antes, este endpoint aceptaba cualquier correo sin verificar y permitía entrar a la cuenta de
   otra persona.
3. **Facial Recognition**: Login usando rostro + email

#### **Gestión de Aplicaciones**
- Crear aplicaciones con nombres personalizados
- API keys automáticas con regeneración
- Control de acceso y verificación
- Timestamps y metadata completa

#### **Reconocimiento Facial**
- Upload de imágenes desde archivo
- Captura en tiempo real desde cámara
- Verificación de rostros registrados
- Configuración de tolerancia de reconocimiento
- Procesamiento de imágenes en backend

#### **Segundo factor por aplicación (TOTP)**
Cada app puede exigir, además del rostro, un código del autenticador (Google Authenticator, Microsoft
Authenticator, Authy…). Es una opción por app: un CRM puede quedar solo con rostro y la app de
administración con rostro + TOTP.

- **Activarlo en la app:** al crear la app (casilla) o después con el interruptor de la tarjeta en
  *Aplicaciones vinculadas* (`PUT /api/apps/<id>` con `{"requires_totp": true}`).
- **El usuario configura su autenticador una vez** en *Autenticador (TOTP)*: escanea el QR y confirma con
  un código (`/api/totp/setup`, `/enable`, `/disable`; JWT).
- **Flujo para la app cliente (API key):**
  1. `POST /api/face/verify-user` con `user_email` y `face_image`. La respuesta trae `authenticated`.
     - App sin TOTP: `authenticated` es `true` si el rostro coincide. Fin.
     - App con TOTP y rostro correcto: `authenticated: false`, `totp_required: true` y un
       `challenge_token` (vale 5 min y solo para esa app).
     - Si el usuario no configuró el autenticador: `totp_setup_required: true` y no se emite reto.
  2. `POST /api/face/verify-totp` con `{"challenge_token": "...", "totp_code": "123456"}` y las mismas
     cabeceras `X-API-Key` + `X-App-ID`. Si el código es válido responde `authenticated: true`.
- **La app cliente debe decidir por `authenticated`**, no por `verification.verified` (que solo dice si el
  rostro coincidió).
- **Protecciones:** el secreto se guarda cifrado; cada código sirve una sola vez; 5 fallos en 5 minutos
  bloquean al usuario 5 minutos (HTTP 429, contador en memoria del proceso); desactivarlo exige un código.
- **Límites conocidos:** no hay códigos de recuperación (si el usuario pierde el teléfono hay que
  reiniciar su TOTP a mano en la base) y `/api/auth/face-login` del propio dashboard no pide TOTP.

#### **SDK de cámara servido por NooxID (MediaPipe)**
Las apps que integran NooxID no instalan MediaPipe ni el modelo: **los descargan directo de NooxID**.

```html
<script src="https://api.id.dominio.com/sdk/noox-face.js"></script>
<div id="camara"></div>
<script>
  const cam = NooxFace.mount(document.getElementById('camara'), {
    onCapture: (foto) => { /* foto = data URL JPEG → verifyFace(email, foto) */ },
  });
  cam.start();
</script>
```

- NooxID sirve `/sdk/noox-face.js`, `/sdk/vendor/vision_bundle.mjs` y `/sdk/mediapipe/…` (WASM y BlazeFace), públicos y
  con `Access-Control-Allow-Origin: *`. La app cliente no depende de ningún CDN.
- La cámara guía el encuadre (un solo rostro, completo, nítido, quieto ~2 s) y entrega la foto; **la identidad la decide
  el servidor** (YuNet + SFace). No hay prueba de vida.
- Los archivos de MediaPipe se buscan en `MEDIAPIPE_DIR`, en `static/sdk/mediapipe` (imagen Docker) o en
  `noox-id/public/mediapipe` (monorepo). Ejemplo completo: `demo-app/`.
- Despliegue con Docker, Oracle Cloud y plantillas de HestiaCP (HSTS): `deploy/README.md`.

#### **Endurecimiento de seguridad del backend**
Cambios que afectan a quien ya integró o desplegó NooxID:

- **API keys.** El servidor guarda solo su hash. El texto se entrega una única vez, al crear la app o al
  regenerar la clave (el panel lo muestra con un aviso para copiarla). Las claves anteriores siguen
  funcionando: se convierten a hash solo al arrancar. Si perdiste una, regenérala.
- **Pertenencia usuario-aplicación.** Un usuario solo puede autenticarse en una app (`verify-user`,
  `otp/request`, `otp/verify`) si el propietario lo autorizó: *Aplicaciones vinculadas > Usuarios autorizados*
  (o `POST /api/apps/<id>/users` con `{"email": "..."}`). Sin eso, `verify-user` responde 403
  `NOT_A_MEMBER`.
- **Roles y permisos (al estilo `spatie/laravel-permission`).** Los administradores viven en la base de
  datos, no en el `.env`: tablas `roles`, `permissions`, `role_permissions` y `user_roles`. El código
  pregunta por permisos (`users.list`, `users.search`, `users.view`, `face.threshold.update`,
  `roles.manage`), no por quién es el usuario, así que se pueden crear roles nuevos sin tocar las rutas.
  El rol `admin` y los permisos se crean solos al arrancar. El primer administrador se asigna por consola:

  ```powershell
  python manage.py make-admin correo@empresa.com   # el usuario debe estar registrado y verificado
  python manage.py assign correo@empresa.com <rol> # asignar otro rol
  python manage.py revoke correo@empresa.com <rol>
  python manage.py roles                           # roles y permisos
  python manage.py admins
  ```

  Con el permiso `roles.manage`: `GET /api/admin/roles`, `GET|POST /api/admin/users/<id>/roles` y
  `DELETE /api/admin/users/<id>/roles/<rol>` (nunca se quita al último administrador). Los permisos se
  aplican al instante con el mismo token y exigen correo verificado. Sin permiso: 403 con
  `required_permission`. Solo con `face.threshold.update` se cambia el umbral facial; antes lo podía cambiar
  cualquier usuario.
- **Perfil.** `PUT /api/users/profile` y `/<id>` aceptan solo nombre, apellido, imagen de perfil y
  contraseña (esta exige `current_password`). El correo, `verified`, `googleid` y el vector facial ya no se
  pueden editar por ahí.
- **Límite de intentos** (429 con `retry_after`): 10 fallos de contraseña en 15 min por correo; 5 fallos de
  rostro en 15 min por correo (login facial) y por app + correo (`verify-user`). Los contadores viven en la
  memoria del proceso.
- **Servidor.** Sin `SECRET_KEY` se genera una aleatoria en `instance/secret_key` (no se versiona), en vez de
  un valor público por defecto; el cambio invalida las sesiones y los secretos TOTP creados con la clave
  anterior. El depurador (`FLASK_DEBUG=true`) solo se activa en `127.0.0.1`; por defecto está apagado y el
  servidor escucha en `127.0.0.1` (usa `HOST=0.0.0.0` solo si lo necesitas).

#### **Verificación del correo al registrarse**
Al registrarse, NooxID envía un código de 6 dígitos al correo y la cuenta no puede iniciar sesión hasta
verificarlo (contraseña, rostro y apps externas devuelven 403 con `code: "EMAIL_NOT_VERIFIED"`).

- `POST /api/auth/register` responde 201 con `verification_required: true` y `verification_sent`. Si el
  correo no está configurado (`MAIL_*`, ver `.env.example`) responde 503 y no crea la cuenta; en
  desarrollo usa `MAIL_CONSOLE=true`.
- El usuario escribe el código en el paso «Verifica tu correo» (`POST /api/otp/login/verify`), que lo
  verifica y lo deja dentro. Reenvío: `POST /api/otp/register/resend`.
- **Anti pre-secuestro:** si el correo estaba registrado y sin verificar, quien se registra después lo
  reemplaza. Y si un correo sin verificar se verifica por otra vía (código de acceso o Google), se borran la
  contraseña y el rostro guardados antes, porque pudo registrarlos otra persona.
- **Usuarios que ya existían:** la primera vez que arranca esta versión se marcan como verificados (una sola
  vez), para no dejarlos fuera.

#### **Código por correo (alternativa al rostro, siempre habilitada)**
Sin contraseña: el usuario pide un código de 6 dígitos y lo recibe por correo. No se desactiva por app;
sirve cuando falla la cámara o el rostro no se reconoce.

- **Configuración (`noox-id-back/.env`, ver `.env.example`):** `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`,
  `MAIL_PASSWORD`, `MAIL_FROM`, `MAIL_USE_TLS` (587) o `MAIL_USE_SSL` (465). Para desarrollo,
  `MAIL_CONSOLE=true` imprime el código en la consola del servidor en vez de enviarlo. Sin correo
  configurado, los endpoints responden 503.
- **Panel de NooxID:** pestaña *Código* en la pantalla de acceso (`POST /api/otp/login/request` y
  `/api/otp/login/verify`, devuelve el JWT).
- **Apps externas (API key):** `POST /api/otp/request` con `{"user_email"}` y luego `POST /api/otp/verify`
  con `{"user_email", "code"}`. La respuesta tiene la misma forma que `verify-user` (`authenticated`,
  `totp_required`, `challenge_token`…), así que una app que exige TOTP sigue con `/api/face/verify-totp`.
- **Protecciones:** el código se guarda como HMAC (no en claro), vence a los 10 min, sirve una vez, admite 5
  intentos, hay 60 s entre envíos y 5 envíos por hora, y la solicitud responde igual exista o no el
  correo. Ajustable con `OTP_EMAIL_*`.
- **Límite conocido:** un correo no demuestra posesión de un dispositivo y puede interceptarse; NIST
  SP 800-63B-4 no admite el correo como autenticador fuera de banda. Es una alternativa de acceso, no un
  sustituto del segundo factor TOTP.

#### **Manejo de Estado**
- AuthContext global para autenticación
- Persistencia automática de tokens
- Actualización automática de perfil
- Manejo de errores unificado

### 🌐 **URLs y Endpoints**

#### **Frontend**
- **URL**: http://localhost:5173/
- **Navegación**: Landing → Auth → Dashboard
- **Secciones**: Profile, Apps, Face, Settings, etc.

#### **Backend**
- **URL**: http://localhost:5000/
- **Health Check**: GET /health
- **API Docs**: Ver colección Postman

### 📋 **Cómo usar**

#### **1. Iniciar Backend**
```bash
cd noox-id-back
python main.py
```

#### **2. Iniciar Frontend**
```bash
cd noox-id
npm run dev
```

#### **3. Flujo de Usuario**
1. **Landing Page** - Información del producto
2. **AuthPage** - Registro/Login (3 métodos disponibles)
3. **Dashboard** - Gestión completa de perfil y apps

### 🔍 **Testing**

#### **Postman Collection**
- ✅ Tests automatizados para todos los endpoints
- ✅ Variables de entorno configuradas
- ✅ Validaciones de respuesta automáticas
- ✅ Flujo completo end-to-end

#### **Frontend Testing**
- ✅ Compilación exitosa
- ✅ Integración funcional con backend
- ✅ Manejo de errores y estados de carga
- ✅ UI responsiva y accesible

### 🎯 **Características Implementadas**

#### **Autenticación Segura**
- ✅ JWT tokens con verificación
- ✅ Persistencia en localStorage
- ✅ Renovación automática de sesión
- ✅ Logout limpio

#### **Gestión de Usuarios**
- ✅ Perfil completo con foto
- ✅ Actualización de información
- ✅ Verificación de email (preparado)
- ✅ Estadísticas del usuario

#### **Aplicaciones y API Keys**
- ✅ CRUD completo de aplicaciones
- ✅ Generación automática de API keys
- ✅ Regeneración segura de claves
- ✅ Control de acceso por app

#### **Reconocimiento Facial Avanzado**
- ✅ Procesamiento en backend con OpenCV
- ✅ Encoding y comparación de rostros
- ✅ Tolerancia configurable
- ✅ Verificación en tiempo real

### 🔄 **Estados y Manejo de Errores**

#### **Estados de Carga**
- ✅ Spinners durante procesamiento
- ✅ Disabled buttons durante operaciones
- ✅ Overlay de carga para operaciones largas

#### **Manejo de Errores**
- ✅ Mensajes descriptivos de error
- ✅ Fallbacks para conexión perdida
- ✅ Validación en frontend y backend
- ✅ Logging para debugging

### 🎨 **UI/UX**

#### **Diseño Moderno**
- ✅ Dark theme consistente
- ✅ Animaciones fluidas (Framer Motion)
- ✅ Componentes responsivos
- ✅ Iconografía clara (Lucide React)

#### **Experiencia de Usuario**
- ✅ Navegación intuitiva
- ✅ Feedback visual inmediato
- ✅ Estados de carga claros
- ✅ Mensajes informativos

### 🔮 **Próximos Pasos Sugeridos**

#### **Funcionalidades Adicionales**
1. **Google OAuth Real** - Integrar con Google APIs
2. **Notificaciones Push** - Alertas en tiempo real
3. **Roles y Permisos** - Sistema de autorización
4. **Audit Logs** - Registro de actividad
5. **API Rate Limiting** - Control de uso
6. **Métricas y Analytics** - Dashboard de estadísticas

#### **Mejoras Técnicas**
1. **Tests Unitarios** - Jest + React Testing Library
2. **E2E Testing** - Cypress o Playwright
3. **PWA** - Service workers y manifest
4. **Docker** - Containerización completa
5. **CI/CD** - Pipeline de deployment
6. **Monitoring** - Logs y métricas

### 🏆 **¡Todo Listo!**

Tu aplicación NooxID ahora tiene:
- ✅ Backend completo y funcional
- ✅ Frontend integrado con UI moderna
- ✅ Autenticación multi-modal
- ✅ Reconocimiento facial avanzado
- ✅ Gestión completa de aplicaciones
- ✅ Tests automatizados
- ✅ Documentación completa

**¡El sistema está listo para usar y expandir!** 🚀
