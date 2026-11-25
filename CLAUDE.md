# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visión general

NooxID: plataforma de autenticación con reconocimiento facial. Monorepo con dos proyectos independientes (sin workspace raíz); la documentación del proyecto está en español (README.md raíz, `noox-id-back/README.md`, `noox-id-back/TESTING_GUIDE.md`, `noox-id/INTEGRATION_GUIDE.md`).

- `noox-id-back/`: API REST Flask + SQLAlchemy (MySQL) + OpenCV (YuNet + SFace).
- `noox-id/`: SPA React 19 + TypeScript + Vite (framer-motion, lucide-react).

## Comandos

Ambos servidores a la vez: `./start-servers.sh` (o `start-servers.bat` en Windows; mata los puertos 5000/5173 con `npx kill-port` y arranca ambos).

Backend (`noox-id-back/`, puerto 5000):
```bash
pip install -r requirements.txt     # opencv-python 4.13: los pesos .onnx ya están en models/sface_yunet/
python create_db.py                 # crea tablas (la BD MySQL `nooxid` debe existir antes)
python main.py                      # servidor de desarrollo (equivale a app.py)
```
Configuración por `.env` (`DATABASE_URL`, `SECRET_KEY`); ver `config.py` para valores por defecto. No hay suite de tests automatizada: las pruebas son la colección Postman `NooxID_API_Tests.postman_collection.json` + `NooxID_Development.postman_environment.json` (ver `TESTING_GUIDE.md`).

Frontend (`noox-id/`, puerto 5173):
```bash
npm install
npm run dev
npm run build      # tsc -b && vite build
npm run lint
```
No hay tests de frontend configurados. La URL de la API se toma de `VITE_API_URL` (por defecto `http://localhost:5000`).

## Arquitectura

### Backend
- `app.py::create_app()` es la factory: configura CORS, inicializa `db`, crea la carpeta `uploads/`, registra blueprints y ejecuta `db.create_all()` al arrancar. `main.py` solo importa la factory y ejecuta el servidor (hay un bloque comentado con SSL/puerto 5041 para producción).
- Blueprints en `routes/` con prefijos: `/api/auth` (register, login, face-login, verify-token, google-auth), `/api/users`, `/api/apps` (incluye tokens de acceso), `/api/face`.
- Dos modos de autenticación: JWT (`Authorization: Bearer`) para endpoints internos del dashboard, y API key (`X-API-Key` + `X-App-ID`) para apps externas que usan reconocimiento facial.
- `models.py`: `User`, `App`, `UserInApp`, `TokenToAccess`. La imagen de perfil y el vector facial se guardan como base64 en columnas `Text` del propio `User` (`base64imageprofile`, `base64vector`), no como archivos.
- `face_recognition_service.py` encapsula YuNet (detección) + SFace (embedding de 128 float32 en base64, normalizado L2). Similitud coseno con umbral `FACE_RECOGNITION_THRESHOLD` (0.363); `distance = 1 - coseno`. El parámetro/endpoint `tolerance` ahora es ese umbral (mayor = más estricto). Vectores antiguos de dlib (1024 bytes) se rechazan con `FaceError` pidiendo re-registro. Pesos en `models/sface_yunet/` (copiados de `clubmejia/modeloJose`).
- `crud.py` centraliza el acceso a datos usado por las rutas.
- CORS: los orígenes permitidos están en `Config.CORS_ORIGINS` (`config.py`; añade más con la variable `CORS_ORIGINS`); además un `before_request` responde los preflight `OPTIONS` con `Access-Control-Allow-Origin: *`.

### Acceso, factores y permisos (backend)
- Primer factor: rostro (`/api/face/verify-user`) o código por correo (`/api/otp/*`, `email_otp_service.py`, SMTP por `.env` en `mailer.py`). Segundo factor opcional por app (`App.requires_totp`): TOTP en `totp_service.py`, reto JWT corto y canje en `/api/face/verify-totp`. Las apps cliente deben mirar `authenticated` (`auth_flow.app_auth_response`).
- El registro envía un código al correo y la cuenta no entra hasta verificarlo (`EMAIL_NOT_VERIFIED`). Verificar por otra vía una cuenta sin verificar borra contraseña y rostro previos (`email_otp_service.mark_verified`).
- Un usuario solo se autentica en una app si está en `UserInApp` habilitado (`auth_flow.is_member`). Las API keys se guardan solo como hash (`models.App`); el texto se entrega una vez al crear/regenerar.
- Roles y permisos en tablas (`Role`, `Permission`, `role_permissions`, `user_roles`; `rbac.py`, `permissions.py`, `authz.py`). Las rutas piden permisos, no roles (`users.list`, `face.threshold.update`, `roles.manage`…). El primer admin: `python manage.py make-admin correo`.
- Límite de intentos en memoria (`throttle.py`) y migraciones mínimas de columnas al arrancar (`migrations.py`). Sin `SECRET_KEY` se genera una en `instance/secret_key`.
- `demo-app/` es una mini app HTML/JS/CSS que integra NooxID con una API key (ver su README); `noox-id/INTEGRATION_GUIDE.md` documenta cada flujo.

### Frontend
- `App.tsx` no usa router: alterna `landing` → `auth` → `dashboard` con estado local, y `AuthContext` (`contexts/AuthContext.tsx`) decide si mostrar el dashboard.
- Capa de servicios en `src/services/`: `api.ts` define `API_CONFIG` (todos los endpoints, deben coincidir con los blueprints del backend), tipos compartidos, `getAuthHeaders` (token JWT en `localStorage` bajo `noox_token`), `ApiError` y `handleApiResponse`. Los demás (`authService`, `userService`, `appService`, `faceService`, `tokenService`) construyen sobre ello.
- Captura facial: `components/FaceCamera.tsx` + `hooks/useFaceCapture.ts` + `utils/faceQuality.ts`. MediaPipe BlazeFace (archivos locales en `public/mediapipe/`, sin CDN; el WASM debe coincidir con la versión exacta de `@mediapipe/tasks-vision`) guía el encuadre y autocaptura tras ~2 s estables; solo orienta, el backend decide la identidad. Lo usan `AuthPage` (login facial) y `FaceSection`.
- Secciones del dashboard en `components/sections/`. Existen pares duplicados `X.tsx` / `XNew.tsx` (`AuthPage`, `AppsSection`, `FaceSection`, `ProfileSection`); `App.tsx` y `Dashboard` indican cuál está en uso; verificar el import antes de editar una de las dos.
