// Cliente mínimo de NooxID: esto es TODO lo que una app empresarial necesita para integrarlo.
// Cada llamada es un POST con dos cabeceras (X-API-Key y X-App-ID).
//
// ⚠️ Esta demo corre en el navegador, así que la API key queda a la vista. En una app real, estas llamadas
// se hacen desde TU servidor (la clave nunca debe llegar al navegador).

class NooxClient {
  constructor({ baseUrl, appId, apiKey }) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.appId = appId;
    this.apiKey = apiKey;
  }

  async post(path, body) {
    const res = await fetch(this.baseUrl + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': this.apiKey, 'X-App-ID': String(this.appId) },
      body: JSON.stringify(body),
    });
    return { status: res.status, data: await res.json().catch(() => ({})) };
  }

  // Primer factor: rostro (imagen en base64 o data URL) o código enviado al correo
  verifyFace(email, faceImage) { return this.post('/api/face/verify-user', { user_email: email, face_image: faceImage }); }
  requestEmailCode(email)      { return this.post('/api/otp/request', { user_email: email }); }
  verifyEmailCode(email, code) { return this.post('/api/otp/verify', { user_email: email, code }); }

  // Segundo factor, solo si la respuesta anterior trae totp_required y challenge_token
  verifyTotp(challengeToken, code) { return this.post('/api/face/verify-totp', { challenge_token: challengeToken, totp_code: code }); }
}
