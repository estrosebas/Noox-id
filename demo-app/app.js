// Pantalla de la demo. La integración con NooxID está en noox-client.js; la cámara viene del SDK que sirve NooxID.
const $ = (id) => document.getElementById(id);
let cliente = null;       // NooxClient
let camara = null;        // controlador de NooxFace
let reto = null;          // challenge_token cuando la app exige TOTP
let primerMetodo = null;  // cómo pasó el primer factor (rostro o código)
let metodo = 'rostro';

// ------------------------------------------------------------------ vistas y pasos
function vista(nombre) {
  for (const v of document.querySelectorAll('.vista')) v.hidden = v.id !== 'v-' + nombre;
  const orden = ['conexion', 'primero', 'segundo', 'acceso'];
  const actual = { conexion: 'conexion', login: 'primero', totp: 'segundo', ok: 'acceso' }[nombre];
  const i = orden.indexOf(actual);
  document.querySelectorAll('#pasos li').forEach((li) => {
    const k = orden.indexOf(li.dataset.paso);
    li.classList.toggle('hecho', k < i || (nombre === 'ok' && k <= i));
    li.classList.toggle('activo', k === i && nombre !== 'ok');
    li.classList.remove('omitido');
  });
  if (nombre === 'ok' && !reto) document.querySelector('[data-paso="segundo"]').classList.replace('hecho', 'omitido');
}

function aviso(id, tipo, titulo, detalle) {
  const el = $(id);
  el.hidden = !titulo;
  el.className = 'mensaje ' + tipo;
  el.innerHTML = '<div><strong></strong><small></small></div>';
  el.querySelector('strong').textContent = titulo || '';
  el.querySelector('small').textContent = detalle || '';
}

function registrar(titulo, { status, data }) {
  const seguro = JSON.stringify(data, (k, v) => (k === 'challenge_token' && v ? v.slice(0, 16) + '…' : v), 2);
  const previo = $('log').textContent === '—' ? '' : $('log').textContent + '\n\n';
  $('log').textContent = previo + `${titulo} → HTTP ${status}\n${seguro}`;
  $('log').scrollTop = $('log').scrollHeight;
}

// ------------------------------------------------------------------ conexión
function estadoConexion(estado, texto) {
  $('chipConexion').dataset.estado = estado;
  $('chipConexion').querySelector('span').textContent = texto;
}

function cargarSdk(baseUrl) {
  return new Promise((resolve, reject) => {
    if (window.NooxFace) return resolve();
    const s = document.createElement('script');
    s.src = baseUrl + '/sdk/noox-face.js';
    s.onload = resolve;
    s.onerror = () => reject(new Error('No se pudo descargar el SDK desde NooxID'));
    document.head.appendChild(s);
  });
}

$('conectar').addEventListener('click', async () => {
  const baseUrl = $('baseUrl').value.trim().replace(/\/+$/, ''), appId = $('appId').value.trim(), apiKey = $('apiKey').value.trim();
  if (!baseUrl || !appId || !apiKey) return ($('msgConexion').textContent = 'Completa los tres campos.');
  $('msgConexion').textContent = 'Conectando…';
  try {
    const salud = await fetch(baseUrl + '/api/health').then((r) => r.json());
    if (salud.status !== 'OK') throw new Error('NooxID no respondió como se esperaba');
    await cargarSdk(baseUrl);
    cliente = new NooxClient({ baseUrl, appId, apiKey });
    $('snipUrl').textContent = baseUrl;
    estadoConexion('ok', `Conectado · app ${appId} · ${apiKey.slice(0, 10)}…`);
    $('msgConexion').textContent = '';
    vista('login');
  } catch (e) {
    estadoConexion('error', 'Error de conexión');
    $('msgConexion').textContent = `${e.message}. ¿Está encendido el servidor y la URL es correcta?`;
  }
});

// ------------------------------------------------------------------ resultado de NooxID: solo importa `authenticated`
const correo = () => $('email').value.trim();

function procesar(res, origen) {
  const d = res.data;
  if (d.authenticated) {
    mostrarExito(d);
  } else if (d.totp_required) {
    reto = d.challenge_token;
    primerMetodo = d.method;
    vista('totp');
    $('totp').value = '';
    $('totp').focus();
  } else {
    const motivo = d.message || (d.verification && !d.verification.verified ? 'El rostro no coincide con el registrado.' : 'No se pudo verificar.');
    aviso(origen === 'totp' ? 'aviso-totp' : 'aviso-login', 'error', 'Acceso denegado', `${motivo} (HTTP ${res.status})`);
    if (origen === 'rostro' && camara) camara.retake();
  }
}

function mostrarExito(d) {
  const nombres = { face: 'Rostro', email_otp: 'Código por correo' };
  $('okDetalle').textContent = reto ? 'Rostro o código verificado, y segundo factor TOTP confirmado.' : 'Verificación completada con un solo factor, como exige esta app.';
  const filas = [['Usuario', '#' + d.user_id], ['App', '#' + d.app_id], ['Primer factor', nombres[d.method || primerMetodo] || 'Verificado'], ['Segundo factor', reto ? 'TOTP' : 'No exigido']];
  $('okDatos').innerHTML = filas.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('');
  vista('ok');
}

async function llamar(titulo, fn) {
  try {
    const res = await fn(cliente);
    registrar(titulo, res);
    return res;
  } catch (e) {
    aviso('aviso-login', 'error', 'No se pudo conectar con NooxID', e.message);
  }
}

// ------------------------------------------------------------------ método: rostro / código
document.querySelectorAll('.seg').forEach((b) => b.addEventListener('click', () => {
  metodo = b.dataset.metodo;
  document.querySelectorAll('.seg').forEach((x) => x.classList.toggle('activo', x === b));
  $('m-rostro').hidden = metodo !== 'rostro';
  $('m-codigo').hidden = metodo !== 'codigo';
  aviso('aviso-login', 'info', '');
  if (metodo !== 'rostro' && camara) camara.stop();
}));

$('activarCamara').addEventListener('click', () => {
  if (!correo()) return aviso('aviso-login', 'error', 'Escribe tu correo primero');
  aviso('aviso-login', 'info', '');
  $('activarCamara').hidden = true;
  camara = NooxFace.mount($('camara'), {
    onCapture: async (foto) => {
      const res = await llamar('POST /api/face/verify-user', (n) => n.verifyFace(correo(), foto));
      if (res) procesar(res, 'rostro');
    },
  });
  camara.start();
});

$('pedirCodigo').addEventListener('click', async () => {
  if (!correo()) return aviso('aviso-login', 'error', 'Escribe tu correo primero');
  const res = await llamar('POST /api/otp/request', (n) => n.requestEmailCode(correo()));
  if (!res) return;
  $('msgCodigo').textContent = res.status === 200 ? 'Código enviado. Revisa tu correo.' : '';
  aviso('aviso-login', res.status === 200 ? 'info' : 'error', res.data.message || 'Respuesta inesperada');
});

$('verificarCodigo').addEventListener('click', async () => {
  const res = await llamar('POST /api/otp/verify', (n) => n.verifyEmailCode(correo(), $('codigo').value.trim()));
  if (res) procesar(res, 'codigo');
});

// ------------------------------------------------------------------ segundo factor
$('verificarTotp').addEventListener('click', async () => {
  const res = await llamar('POST /api/face/verify-totp', (n) => n.verifyTotp(reto, $('totp').value.trim()));
  if (res) procesar(res, 'totp');
});

$('salir').addEventListener('click', () => {
  reto = null;
  primerMetodo = null;
  if (camara) { camara.destroy(); camara = null; }
  $('activarCamara').hidden = false;
  $('codigo').value = '';
  aviso('aviso-login', 'info', '');
  vista('login');
});

vista('conexion');
