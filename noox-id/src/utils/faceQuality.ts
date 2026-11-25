// Evaluación de encuadre/nitidez y estabilidad para la autocaptura facial.
// Portado de la lógica de captura del proyecto clubmejia (calidadCaptura.js).
// Esto orienta al usuario; NO prueba identidad ni vida. El backend (YuNet+SFace)
// vuelve a validar la foto.

export type CaptureState =
  | 'buscando' | 'varias' | 'cerca' | 'lejos' | 'descentrado' | 'listo';

export interface Box { originX: number; originY: number; width: number; height: number }
export interface Detection { boundingBox?: Box; categories?: { score: number }[] }

export interface Reading {
  estado: CaptureState;
  mensaje: string;
  puntuacion?: number;
  posicion?: { x: number; y: number; escala: number };
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const result = (estado: CaptureState, mensaje: string): Reading => ({ estado, mensaje });

/** Nitidez 0-1 del 60 % central del rostro (varianza del laplaciano a escala fija). */
function faceSharpness(img: ImageData, box: Box): number {
  const side = 64;
  const gray = new Float32Array(side * side);
  for (let y = 0; y < side; y++) {
    for (let x = 0; x < side; x++) {
      const px = box.originX + box.width * (0.2 + (0.6 * (x + 0.5)) / side);
      const py = box.originY + box.height * (0.2 + (0.6 * (y + 0.5)) / side);
      const x0 = Math.floor(px), y0 = Math.floor(py);
      let luz = 0;
      for (let dy = 0; dy <= 1; dy++) {
        for (let dx = 0; dx <= 1; dx++) {
          const nx = Math.min(img.width - 1, Math.max(0, x0 + dx));
          const ny = Math.min(img.height - 1, Math.max(0, y0 + dy));
          const i = (ny * img.width + nx) * 4;
          const wx = dx ? px - x0 : 1 - (px - x0);
          const wy = dy ? py - y0 : 1 - (py - y0);
          luz += wx * wy * (0.299 * img.data[i] + 0.587 * img.data[i + 1] + 0.114 * img.data[i + 2]);
        }
      }
      gray[y * side + x] = luz;
    }
  }
  const smooth = new Float32Array(gray.length);
  const w = [1, 2, 1];
  for (let y = 1; y < side - 1; y++) {
    for (let x = 1; x < side - 1; x++) {
      let v = 0;
      for (let dy = -1; dy <= 1; dy++)
        for (let dx = -1; dx <= 1; dx++) v += gray[(y + dy) * side + x + dx] * w[dy + 1] * w[dx + 1];
      smooth[y * side + x] = v / 16;
    }
  }
  let sum = 0, sq = 0, n = 0;
  for (let y = 2; y < side - 2; y++) {
    for (let x = 2; x < side - 2; x++) {
      const i = y * side + x;
      const edge = smooth[i - 1] + smooth[i + 1] + smooth[i - side] + smooth[i + side] - 4 * smooth[i];
      sum += edge; sq += edge * edge; n++;
    }
  }
  const variance = Math.max(0, sq / n - (sum / n) ** 2);
  return clamp01(Math.log1p(variance) / Math.log1p(300));
}

export function evaluateCapture(detections: Detection[], img: ImageData): Reading {
  if (!detections.length) return result('buscando', 'Coloca tu rostro dentro del óvalo');
  if (detections.length > 1) return result('varias', 'Debe aparecer una sola persona');
  const box = detections[0].boundingBox;
  if (!box || ![box.originX, box.originY, box.width, box.height].every(Number.isFinite)
      || box.width <= 0 || box.height <= 0) {
    return result('buscando', 'No vemos tu rostro con claridad');
  }
  const alto = box.height / img.height;
  const ancho = box.width / img.width;
  const margen = Math.min(
    box.originX / img.width, box.originY / img.height,
    (img.width - box.originX - box.width) / img.width,
    (img.height - box.originY - box.height) / img.height);
  if (alto > 0.80 || ancho > 0.70) return result('cerca', 'Aléjate un poco para que se vea tu cara completa');
  if (margen < 0.04) return result('descentrado', 'Mueve tu rostro al centro para que no quede cortado');
  if (alto < 0.35 || ancho < 0.25) return result('lejos', 'Acércate un poco para ver bien tu rostro');

  const confianza = detections[0].categories?.[0]?.score;
  const deteccion = Number.isFinite(confianza) ? clamp01(confianza as number) : 0.5;
  const nitidez = faceSharpness(img, box);
  return {
    ...result('listo', 'Rostro detectado. Mantente quieto un momento…'),
    puntuacion: 100 * (0.85 * nitidez + 0.15 * deteccion), // solo para elegir la mejor toma
    posicion: {
      x: (box.originX + box.width / 2) / img.width,
      y: (box.originY + box.height / 2) / img.height,
      escala: box.width / img.width,
    },
  };
}

export interface StabilityOutput {
  lista: boolean;
  progreso: number;
  pausada: boolean;
  /** El cuadro actual es el mejor visto en el tramo estable: conviene guardarlo. */
  mejora: boolean;
  /** El candidato guardado ya no es válido (cambio brusco, pausa o reinicio). */
  descartarCandidato: boolean;
}

/**
 * Acumula tiempo de cuadros aptos: exige `duracion` ms, ≥10 lecturas y ≥3 seguidas
 * sin saltos bruscos. Correcciones breves de encuadre pausan el avance sin perderlo.
 */
export function createStability(duracion = 2000) {
  const recuperables = new Set<CaptureState>(['descentrado', 'cerca', 'lejos']);
  let acumulado = 0, anterior: number | null = null, ultimoApto: number | null = null;
  let lecturas = 0, consecutivas = 0, mejor = -Infinity, pausada = false;
  let posAnterior: Reading['posicion'] | null = null;

  const out = (o: Partial<StabilityOutput> = {}): StabilityOutput => ({
    lista: false, pausada: false, mejora: false, descartarCandidato: false,
    progreso: Math.min(clamp01(acumulado / duracion), clamp01(lecturas / 10)), ...o,
  });
  const reset = () => {
    acumulado = 0; anterior = null; ultimoApto = null; lecturas = 0; consecutivas = 0;
    mejor = -Infinity; pausada = false; posAnterior = null;
  };

  return {
    reset,
    update(lectura: Reading, ahora: number): StabilityOutput {
      if (ultimoApto !== null && ahora - ultimoApto > 1500) reset();
      const p = lectura.posicion;
      if (lectura.estado !== 'listo' || !p || lectura.puntuacion === undefined) {
        if (recuperables.has(lectura.estado) && ultimoApto !== null) {
          pausada = true; consecutivas = 0; mejor = -Infinity; anterior = ahora;
          return out({ pausada: true, descartarCandidato: true });
        }
        reset();
        return out({ descartarCandidato: true });
      }
      const prev = posAnterior;
      const brusco = prev != null && (
        Math.hypot(p.x - prev.x, p.y - prev.y) > 0.05
        || Math.abs(p.escala / prev.escala - 1) > 0.18);
      const descartar = pausada || brusco;
      if (descartar) { mejor = -Infinity; consecutivas = 0; }
      if (anterior !== null && !pausada && !brusco) acumulado += Math.min(450, ahora - anterior);
      anterior = ahora; ultimoApto = ahora; posAnterior = p; pausada = false;
      lecturas++; consecutivas++;
      const mejora = lectura.puntuacion > mejor;
      if (mejora) mejor = lectura.puntuacion;
      return out({ lista: acumulado >= duracion && lecturas >= 10 && consecutivas >= 3,
        mejora, descartarCandidato: descartar });
    },
  };
}
