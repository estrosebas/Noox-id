// Interfaz de la demo. La integración con NooxID está en noox-client.js; aquí solo hay pantalla.
const $ = (id) => document.getElementById(id);
let cliente = null;
let reto = null;          // challenge_token cuando la app exige TOTP
let stream = null;

// ------------------------------------------------------------------ configuración
function leerConfig() {
  return { baseUrl: $('baseUrl').value.trim(), appId: $('appId').value.trim(), apiKey: $('apiKey').value.trim() };
}

function crearCliente() {
  const c = leerConfig();
  if (!c.baseUrl || !c.appId || !c.apiKey) { mostrar('error', 'Completa la URL, el ID de la app y la API key.'); return null; }
  cliente = new NooxClient(c);
  return cliente;
}

function cargarGuardado() {
  const g = JSON.parse(sessionStorage.getItem('noox-demo') || '{}');
  for (const k of ['baseUrl', 'appId', 'apiKey', 'email']) if (g[k]) $(k).value = g[k];
}

$('guardar').addEventListener('click', () => {
  sessionStorage.setItem('noox-demo', JSON.stringify({ ...leerConfig(), email: $('email').value.trim() }));
  $('guardado').textContent = 'Guardado (se borra al cerrar la pestaña).';
});

// ------------------------------------------------------------------ registro de llamadas y resultado
function registrar(titulo, { status, data }) {
  const seguro = JSON.stringify(data, (k, v) => (k === 'challenge_token' && v ? v.slice(0, 16) + '…' : v), 2);
  const prev = $('log').textContent === '—' ? '' : $('log').textContent + '\n\n';
  $('log').textContent = prev + `${titulo} → HTTP ${status}\n${seguro}`;
  $('log').scrollTop = $('log').scrollHeight;
}

function mostrar(tipo, texto, detalle) {
  $('resultado').hidden = false;
  const iconos = { ok: '✅', error: '⛔', info: 'ℹ️' };
  $('estado').className = 'estado ' + tipo;
  $('estado').innerHTML = `<span class="icono">${iconos[tipo]}</span><div><strong></strong><small></small></div>`;
  $('estado').querySelector('strong').textContent = texto;
  $('estado').querySelector('small').textContent = detalle || '';
}

// Lee la respuesta de NooxID: lo único que importa es `authenticated`
function procesar(res) {
  const d = res.data;
  if (d.authenticated) {
    $('paso-totp').hidden = true;
    mostrar('ok', 'Acceso concedido', `Usuario ${d.user_id} autenticado en la app ${d.app_id} (${d.method || 'totp'}).`);
  } else if (d.totp_required) {
    reto = d.challenge_token;
    $('paso-totp').hidden = false;
    $('totp').focus();
    mostrar('info', 'Falta el segundo factor', 'Ingresa el código de tu app autenticadora.');
  } else if (d.totp_setup_required) {
    mostrar('error', 'Acceso denegado', d.message);
  } else {
    const motivo = d.message || (d.verification && !d.verification.verified ? 'El rostro no coincide.' : 'No se pudo verificar.');
    mostrar('error', 'Acceso denegado', `${motivo} (HTTP ${res.status})`);
  }
}

async function llamar(titulo, fn) {
  if (!crearCliente()) return;
  try {
    const res = await fn(cliente);
    registrar(titulo, res);
    return res;
  } catch (e) {
    mostrar('error', 'No se pudo conectar con NooxID', `${e.message}. ¿Está el servidor encendido y la URL correcta?`);
  }
}

const correo = () => $('email').value.trim();

// ------------------------------------------------------------------ pestañas
document.querySelectorAll('.tab').forEach((t) => t.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach((x) => x.classList.toggle('activa', x === t));
  $('tab-rostro').hidden = t.dataset.tab !== 'rostro';
  $('tab-codigo').hidden = t.dataset.tab !== 'codigo';
}));

// ------------------------------------------------------------------ rostro
$('camara').addEventListener('click', async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
    $('video').srcObject = stream;
    $('capturar').disabled = false;
    $('camara').textContent = 'Cámara activa';
  } catch (e) {
    mostrar('error', 'No se pudo abrir la cámara', e.message);
  }
});

$('capturar').addEventListener('click', async () => {
  if (!correo()) return mostrar('error', 'Escribe el correo del usuario.');
  const v = $('video'), c = $('canvas');
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0);
  const foto = c.toDataURL('image/jpeg', 0.9);
  const res = await llamar('POST /api/face/verify-user', (n) => n.verifyFace(correo(), foto));
  if (res) procesar(res);
});

// ------------------------------------------------------------------ código por correo
$('pedirCodigo').addEventListener('click', async () => {
  if (!correo()) return mostrar('error', 'Escribe el correo del usuario.');
  const res = await llamar('POST /api/otp/request', (n) => n.requestEmailCode(correo()));
  if (res) mostrar(res.status === 200 ? 'info' : 'error', res.data.message || 'Revisa la respuesta.', res.status === 200 ? 'Escribe el código que llegó al correo.' : '');
});

$('verificarCodigo').addEventListener('click', async () => {
  const res = await llamar('POST /api/otp/verify', (n) => n.verifyEmailCode(correo(), $('codigo').value.trim()));
  if (res) procesar(res);
});

// ------------------------------------------------------------------ segundo factor
$('verificarTotp').addEventListener('click', async () => {
  const res = await llamar('POST /api/face/verify-totp', (n) => n.verifyTotp(reto, $('totp').value.trim()));
  if (res) procesar(res);
});

cargarGuardado();
