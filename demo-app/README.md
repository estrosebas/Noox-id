# Demo: una app que inicia sesión con NooxID

Mini app en HTML, JS y CSS puros (sin build) para probar una API key de NooxID de punta a punta.

- `noox-client.js`: **la integración completa** (30 líneas, comentarios incluidos): un POST con `X-API-Key` y `X-App-ID`.
- `app.js`, `index.html`, `styles.css`: solo la pantalla.

## Cómo probarla

1. Arranca el backend de NooxID (`python main.py` en `noox-id-back/`, puerto 5000) y el panel.
2. En el panel, crea una app en *Aplicaciones vinculadas* y **copia la API key** (se muestra una sola vez).
3. En esa misma tarjeta, *Usuarios autorizados > Gestionar*, agrega el correo del empleado que va a probar.
   Opcional: activa el interruptor TOTP de la app para probar el segundo factor.
4. Sirve esta carpeta:

   ```powershell
   cd demo-app
   python -m http.server 8080
   ```

5. Abre <http://localhost:8080>, pega el ID de la app y la API key, escribe el correo y prueba **Rostro** o
   **Código por correo**. Si la app exige TOTP, después aparece el paso del código del autenticador.

El backend permite el origen `http://localhost:8080` por defecto (CORS). Para otro origen usa `CORS_ORIGINS`
en el `.env` del backend.

## Qué es lo único que debe mirar tu app

El campo `authenticated` de la respuesta. Es `true` solo cuando el usuario pasó todos los factores que la app
exige. `totp_required` indica que falta el segundo paso (`verify-totp` con el `challenge_token`).

> ⚠️ La API key en el navegador es solo para esta demo. En producción, las llamadas se hacen desde el servidor de
> tu app.
