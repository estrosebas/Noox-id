/*!
 * NooxFace SDK: captura facial guiada que NooxID sirve a las apps que lo integran.
 *
 *   <script src="https://TU-NOOXID/sdk/noox-face.js"></script>
 *   const cam = NooxFace.mount(document.getElementById('camara'), { onCapture: (fotoDataUrl) => { ... } });
 *
 * Todo (este script, MediaPipe y el modelo BlazeFace) se descarga del propio servidor de NooxID: la app cliente
 * no instala nada ni depende de un CDN. MediaPipe solo GUÍA el encuadre; la identidad la decide el servidor
 * (YuNet + SFace) al recibir la foto. Sin prueba de vida.
 */
(function () {
  'use strict';

  var script = document.currentScript;
  var ORIGIN = script && script.src ? new URL(script.src).origin : '';
  var SDK = ORIGIN + '/sdk';
  var LADO = 720; // lado del JPEG cuadrado que se envía

  // ------------------------------------------------------------------ calidad y estabilidad (portado de la app React)
  function clamp01(v) { return Math.max(0, Math.min(1, v)); }
  function lectura(estado, mensaje) { return { estado: estado, mensaje: mensaje }; }

  // Nitidez 0-1 del 60 % central del rostro (varianza del laplaciano a escala fija)
  function nitidez(img, box) {
    var side = 64, gray = new Float32Array(side * side), x, y, dx, dy;
    for (y = 0; y < side; y++) {
      for (x = 0; x < side; x++) {
        var px = box.originX + box.width * (0.2 + (0.6 * (x + 0.5)) / side);
        var py = box.originY + box.height * (0.2 + (0.6 * (y + 0.5)) / side);
        var x0 = Math.floor(px), y0 = Math.floor(py), luz = 0;
        for (dy = 0; dy <= 1; dy++) {
          for (dx = 0; dx <= 1; dx++) {
            var nx = Math.min(img.width - 1, Math.max(0, x0 + dx));
            var ny = Math.min(img.height - 1, Math.max(0, y0 + dy));
            var i = (ny * img.width + nx) * 4;
            var wx = dx ? px - x0 : 1 - (px - x0), wy = dy ? py - y0 : 1 - (py - y0);
            luz += wx * wy * (0.299 * img.data[i] + 0.587 * img.data[i + 1] + 0.114 * img.data[i + 2]);
          }
        }
        gray[y * side + x] = luz;
      }
    }
    var smooth = new Float32Array(gray.length), w = [1, 2, 1];
    for (y = 1; y < side - 1; y++) {
      for (x = 1; x < side - 1; x++) {
        var v = 0;
        for (dy = -1; dy <= 1; dy++) for (dx = -1; dx <= 1; dx++) v += gray[(y + dy) * side + x + dx] * w[dy + 1] * w[dx + 1];
        smooth[y * side + x] = v / 16;
      }
    }
    var sum = 0, sq = 0, n = 0;
    for (y = 2; y < side - 2; y++) {
      for (x = 2; x < side - 2; x++) {
        var k = y * side + x;
        var edge = smooth[k - 1] + smooth[k + 1] + smooth[k - side] + smooth[k + side] - 4 * smooth[k];
        sum += edge; sq += edge * edge; n++;
      }
    }
    var variance = Math.max(0, sq / n - Math.pow(sum / n, 2));
    return clamp01(Math.log1p(variance) / Math.log1p(300));
  }

  function evaluar(detecciones, img) {
    if (!detecciones.length) return lectura('buscando', 'Coloca tu rostro dentro del óvalo');
    if (detecciones.length > 1) return lectura('varias', 'Debe aparecer una sola persona');
    var box = detecciones[0].boundingBox;
    if (!box || ![box.originX, box.originY, box.width, box.height].every(isFinite) || box.width <= 0 || box.height <= 0) {
      return lectura('buscando', 'No vemos tu rostro con claridad');
    }
    var alto = box.height / img.height, ancho = box.width / img.width;
    var margen = Math.min(box.originX / img.width, box.originY / img.height,
      (img.width - box.originX - box.width) / img.width, (img.height - box.originY - box.height) / img.height);
    if (alto > 0.80 || ancho > 0.70) return lectura('cerca', 'Aléjate un poco para que se vea tu cara completa');
    if (margen < 0.04) return lectura('descentrado', 'Mueve tu rostro al centro para que no quede cortado');
    if (alto < 0.35 || ancho < 0.25) return lectura('lejos', 'Acércate un poco para ver bien tu rostro');
    var conf = detecciones[0].categories && detecciones[0].categories[0] ? detecciones[0].categories[0].score : NaN;
    var det = isFinite(conf) ? clamp01(conf) : 0.5;
    var res = lectura('listo', 'Rostro detectado. Mantente quieto un momento…');
    res.puntuacion = 100 * (0.85 * nitidez(img, box) + 0.15 * det);
    res.posicion = { x: (box.originX + box.width / 2) / img.width, y: (box.originY + box.height / 2) / img.height, escala: box.width / img.width };
    return res;
  }

  // Exige ~2 s de cuadros aptos, ≥10 lecturas y ≥3 seguidas sin saltos bruscos.
  function crearEstabilidad(duracion) {
    duracion = duracion || 2000;
    var recuperables = { descentrado: 1, cerca: 1, lejos: 1 };
    var acumulado = 0, anterior = null, ultimoApto = null, lecturas = 0, consecutivas = 0, mejor = -Infinity, pausada = false, posAnt = null;
    function salida(o) {
      var base = { lista: false, pausada: false, mejora: false, descartarCandidato: false,
        progreso: Math.min(clamp01(acumulado / duracion), clamp01(lecturas / 10)) };
      for (var k in o) base[k] = o[k];
      return base;
    }
    function reiniciar() { acumulado = 0; anterior = null; ultimoApto = null; lecturas = 0; consecutivas = 0; mejor = -Infinity; pausada = false; posAnt = null; }
    return {
      reiniciar: reiniciar,
      actualizar: function (l, ahora) {
        if (ultimoApto !== null && ahora - ultimoApto > 1500) reiniciar();
        var p = l.posicion;
        if (l.estado !== 'listo' || !p || l.puntuacion === undefined) {
          if (recuperables[l.estado] && ultimoApto !== null) {
            pausada = true; consecutivas = 0; mejor = -Infinity; anterior = ahora;
            return salida({ pausada: true, descartarCandidato: true });
          }
          reiniciar();
          return salida({ descartarCandidato: true });
        }
        var brusco = posAnt !== null && (Math.hypot(p.x - posAnt.x, p.y - posAnt.y) > 0.05 || Math.abs(p.escala / posAnt.escala - 1) > 0.18);
        var descartar = pausada || brusco;
        if (descartar) { mejor = -Infinity; consecutivas = 0; }
        if (anterior !== null && !pausada && !brusco) acumulado += Math.min(450, ahora - anterior);
        anterior = ahora; ultimoApto = ahora; posAnt = p; pausada = false;
        lecturas++; consecutivas++;
        var mejora = l.puntuacion > mejor;
        if (mejora) mejor = l.puntuacion;
        return salida({ lista: acumulado >= duracion && lecturas >= 10 && consecutivas >= 3, mejora: mejora, descartarCandidato: descartar });
      }
    };
  }

  // ------------------------------------------------------------------ estilos (se inyectan una vez; prefijo nxf-)
  var CSS = [
    '.nxf{--nxf-ok:#16a34a;--nxf-warn:#d97706;--nxf-bad:#dc2626;--nxf-idle:#9ca3af;font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#1f2937;max-width:380px;margin:0 auto}',
    '.nxf *{box-sizing:border-box}',
    '.nxf-stage{position:relative;width:100%;aspect-ratio:1/1;border-radius:18px;overflow:hidden;background:#0b1220;box-shadow:0 8px 30px rgba(15,23,42,.25)}',
    '.nxf-stage video,.nxf-stage img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}',
    '.nxf-stage svg{position:absolute;inset:0;width:100%;height:100%}',
    '.nxf-cover{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:20px;text-align:center;color:#cbd5e1;background:rgba(11,18,32,.88)}',
    '.nxf-cover.nxf-err{color:#fecaca}',
    '.nxf-spin{width:28px;height:28px;border-radius:50%;border:3px solid rgba(255,255,255,.25);border-top-color:#fff;animation:nxf-r 1s linear infinite}',
    '@keyframes nxf-r{to{transform:rotate(360deg)}}',
    '.nxf-msg{margin:14px 0 8px;min-height:21px;text-align:center;font-weight:500}',
    '.nxf-bar{height:6px;border-radius:3px;background:#e5e7eb;overflow:hidden}',
    '.nxf-bar i{display:block;height:100%;width:0;background:var(--nxf-idle);transition:width .15s,background .2s}',
    '.nxf-row{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:12px}',
    '.nxf-btn{font:inherit;font-weight:600;padding:9px 16px;border:0;border-radius:10px;background:#2563eb;color:#fff;cursor:pointer}',
    '.nxf-btn.nxf-sec{background:#eef2ff;color:#1e3a8a}',
    '.nxf-btn:hover{filter:brightness(1.07)}',
    '.nxf select{font:inherit;padding:8px 10px;border-radius:10px;border:1px solid #d1d5db;background:#fff;max-width:100%}',
    '.nxf [hidden]{display:none!important}'
  ].join('');

  function inyectarEstilos() {
    if (document.getElementById('nxf-css')) return;
    var s = document.createElement('style');
    s.id = 'nxf-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  var COLORES = { listo: 'var(--nxf-ok)', buscando: 'var(--nxf-idle)', varias: 'var(--nxf-bad)', cerca: 'var(--nxf-warn)', lejos: 'var(--nxf-warn)', descentrado: 'var(--nxf-warn)' };

  function mensajeCamara(e) {
    var n = e && e.name;
    if (n === 'NotAllowedError' || n === 'SecurityError') return 'No diste permiso para usar la cámara. Habilítala desde el candado de la barra de direcciones.';
    if (n === 'NotFoundError' || n === 'DevicesNotFoundError') return 'No encontramos ninguna cámara en este dispositivo.';
    if (n === 'NotReadableError' || n === 'TrackStartError') return 'Otra aplicación está usando la cámara. Ciérrala e inténtalo de nuevo.';
    return 'No pudimos abrir la cámara. Revisa los permisos e inténtalo de nuevo.';
  }

  // MediaPipe se carga una sola vez, desde NooxID (sin CDN)
  var visionPromesa = null;
  function cargarVision() {
    if (!visionPromesa) {
      visionPromesa = import(SDK + '/vendor/vision_bundle.mjs').then(function (vision) {
        return vision.FilesetResolver.forVisionTasks(SDK + '/mediapipe/wasm').then(function (archivos) {
          return { vision: vision, archivos: archivos };
        });
      }).catch(function (e) { visionPromesa = null; throw e; });
    }
    return visionPromesa;
  }

  // ------------------------------------------------------------------ componente
  function mount(contenedor, opciones) {
    opciones = opciones || {};
    inyectarEstilos();
    contenedor.innerHTML =
      '<div class="nxf">' +
      '<div class="nxf-stage">' +
      '<video autoplay muted playsinline></video><img alt="Foto capturada" hidden>' +
      '<svg viewBox="0 0 100 100" hidden><defs><mask id="nxf-m"><rect width="100" height="100" fill="#fff"/><ellipse cx="50" cy="50" rx="30" ry="38" fill="#000"/></mask></defs>' +
      '<rect width="100" height="100" fill="rgba(0,0,0,.45)" mask="url(#nxf-m)"/><ellipse class="nxf-oval" cx="50" cy="50" rx="30" ry="38" fill="none" stroke="#9ca3af" stroke-width="1.2" stroke-dasharray="3 2"/></svg>' +
      '<div class="nxf-cover" hidden></div>' +
      '</div>' +
      '<p class="nxf-msg" aria-live="polite"></p>' +
      '<div class="nxf-bar"><i></i></div>' +
      '<div class="nxf-row"><select aria-label="Cámara" hidden></select>' +
      '<button type="button" class="nxf-btn nxf-sec nxf-manual" hidden>Capturar ahora</button>' +
      '<button type="button" class="nxf-btn nxf-sec nxf-otra" hidden>Tomar otra</button></div></div>';

    var q = function (s) { return contenedor.querySelector(s); };
    var video = q('video'), foto = q('img'), svg = q('svg'), oval = q('.nxf-oval'), cover = q('.nxf-cover');
    var msg = q('.nxf-msg'), barra = q('.nxf-bar i'), selector = q('select'), btnManual = q('.nxf-manual'), btnOtra = q('.nxf-otra');

    var stream = null, detector = null, raf = null, generacion = 0, lienzo = null, mejor = null;
    var estabilidad = crearEstabilidad(), ultimoCuadro = -1, ultimaCorrida = 0, listo = false;

    function portada(texto, error, spinner) {
      cover.hidden = !texto;
      cover.className = 'nxf-cover' + (error ? ' nxf-err' : '');
      cover.innerHTML = (spinner ? '<div class="nxf-spin"></div>' : '') + '<div></div>';
      if (texto) cover.lastChild.textContent = texto;
    }
    function pintar(estado, texto, progreso) {
      var color = COLORES[estado] || 'var(--nxf-idle)';
      msg.style.color = color;
      msg.textContent = texto;
      barra.style.width = Math.round(progreso * 100) + '%';
      barra.style.background = color;
      oval.setAttribute('stroke', color === 'var(--nxf-ok)' ? '#16a34a' : color.indexOf('warn') > 0 ? '#d97706' : color.indexOf('bad') > 0 ? '#dc2626' : '#9ca3af');
      oval.setAttribute('stroke-dasharray', progreso > 0 ? '' : '3 2');
    }
    function soltar() {
      if (raf) cancelAnimationFrame(raf);
      raf = null;
      if (detector) { try { detector.close(); } catch (e) { /* ya cerrado */ } detector = null; }
      if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
      video.srcObject = null;
    }
    function detener() {
      generacion++;
      soltar();
      estabilidad.reiniciar();
      mejor = null;
    }

    function cuadrado() {
      var lado = Math.min(video.videoWidth, video.videoHeight), salida = Math.min(LADO, lado);
      if (!lienzo) lienzo = document.createElement('canvas');
      if (lienzo.width !== salida) { lienzo.width = salida; lienzo.height = salida; }
      lienzo.getContext('2d', { willReadFrequently: true }).drawImage(video,
        (video.videoWidth - lado) / 2, (video.videoHeight - lado) / 2, lado, lado, 0, 0, salida, salida);
      return lienzo;
    }

    function entregar(origen) {
      var data = (mejor || origen).toDataURL('image/jpeg', 0.92);
      detener();
      foto.src = data; foto.hidden = false; video.hidden = true; svg.setAttribute('hidden', '');
      btnManual.hidden = true; selector.hidden = true; btnOtra.hidden = false;
      pintar('listo', 'Foto capturada', 1);
      if (opciones.onCapture) opciones.onCapture(data);
    }

    function bucle(gen) {
      function tick() {
        if (gen !== generacion || !detector) return;
        var ahora = performance.now();
        if (video.readyState < 2 || !video.videoWidth || ahora - ultimaCorrida < 120 || video.currentTime === ultimoCuadro) {
          raf = requestAnimationFrame(tick); return;
        }
        ultimaCorrida = ahora; ultimoCuadro = video.currentTime;
        try {
          var c = cuadrado();
          var out = detector.detectForVideo(c, ahora);
          var l = evaluar(out.detections || [], c.getContext('2d').getImageData(0, 0, c.width, c.height));
          var e = estabilidad.actualizar(l, ahora);
          pintar(l.estado, l.mensaje, e.progreso);
          if (e.descartarCandidato) mejor = null;
          if (e.mejora) {
            mejor = mejor || document.createElement('canvas');
            mejor.width = c.width; mejor.height = c.height;
            mejor.getContext('2d').drawImage(c, 0, 0);
          }
          if (e.lista) { entregar(c); return; }
        } catch (err) {
          console.warn('[NooxFace] análisis no disponible', err);
          pintar('buscando', 'La detección automática falló. Usa «Capturar ahora».', 0);
          btnManual.hidden = false;
          return;
        }
        raf = requestAnimationFrame(tick);
      }
      raf = requestAnimationFrame(tick);
    }

    function cargarDetector(gen) {
      pintar('buscando', 'Cargando detector facial…', 0);
      return cargarVision().then(function (m) {
        function opts(delegate) {
          return { baseOptions: { modelAssetPath: SDK + '/mediapipe/blaze_face_short_range.tflite', delegate: delegate },
            runningMode: 'VIDEO', minDetectionConfidence: 0.6 };
        }
        return m.vision.FaceDetector.createFromOptions(m.archivos, opts('GPU')).catch(function () {
          return m.vision.FaceDetector.createFromOptions(m.archivos, opts('CPU')); // algunos equipos no inicializan WebGL
        });
      }).then(function (d) {
        if (gen !== generacion) { d.close(); return; }
        detector = d;
        pintar('buscando', 'Coloca tu rostro dentro del óvalo', 0);
        bucle(gen);
      }).catch(function (e) {
        if (gen !== generacion) return;
        console.warn('[NooxFace] MediaPipe no pudo iniciar', e);
        pintar('buscando', 'No se pudo iniciar la detección automática. Captura la foto manualmente.', 0);
        btnManual.hidden = false; // el servidor valida igual
      });
    }

    function listarCamaras() {
      return navigator.mediaDevices.enumerateDevices().then(function (ds) {
        var camaras = ds.filter(function (d) { return d.kind === 'videoinput'; });
        selector.innerHTML = '';
        camaras.forEach(function (d, i) {
          var o = document.createElement('option');
          o.value = d.deviceId; o.textContent = d.label || 'Cámara ' + (i + 1);
          selector.appendChild(o);
        });
        var actual = stream && stream.getVideoTracks()[0] && stream.getVideoTracks()[0].getSettings().deviceId;
        if (actual) selector.value = actual;
        selector.hidden = camaras.length < 2;
      }).catch(function () { /* se puede capturar sin listar */ });
    }

    function iniciar(deviceId) {
      detener();
      var gen = generacion;
      foto.hidden = true; video.hidden = false; svg.setAttribute('hidden', ''); btnOtra.hidden = true; btnManual.hidden = true;
      pintar('buscando', '', 0);
      portada('Iniciando cámara…', false, true);
      ultimoCuadro = -1;
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        portada('Este navegador no permite usar la cámara (requiere HTTPS o localhost).', true);
        return Promise.resolve();
      }
      var video_ = { width: { ideal: 1280 }, height: { ideal: 720 } };
      if (deviceId) video_.deviceId = { exact: deviceId }; else video_.facingMode = 'user';
      return navigator.mediaDevices.getUserMedia({ video: video_, audio: false }).then(function (s) {
        if (gen !== generacion) { s.getTracks().forEach(function (t) { t.stop(); }); return; }
        stream = s;
        video.srcObject = s;
        return Promise.resolve(video.play()).catch(function () { /* autoplay lo resuelve */ }).then(function () {
          if (gen !== generacion) return;
          portada('');
          svg.removeAttribute('hidden');
          listarCamaras();
          return cargarDetector(gen);
        });
      }).catch(function (e) {
        if (gen !== generacion) return;
        portada(mensajeCamara(e), true);
        var b = document.createElement('button');
        b.type = 'button'; b.className = 'nxf-btn'; b.textContent = 'Reintentar';
        b.onclick = function () { iniciar(); };
        cover.appendChild(b);
        if (opciones.onError) opciones.onError(e);
      });
    }

    selector.addEventListener('change', function () { iniciar(selector.value); });
    btnManual.addEventListener('click', function () {
      if (video.videoWidth) entregar(cuadrado());
    });
    btnOtra.addEventListener('click', function () { iniciar(selector.value || undefined); });

    return {
      start: function () { return iniciar(); },
      stop: function () { detener(); portada(''); },
      retake: function () { return iniciar(selector.value || undefined); },
      destroy: function () { detener(); contenedor.innerHTML = ''; }
    };
  }

  window.NooxFace = { version: '1.0.0', baseUrl: ORIGIN, mount: mount };
})();
