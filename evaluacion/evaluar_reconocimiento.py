"""Evalúa el reconocimiento facial de NooxID (YuNet + SFace) con fotos reales.

Usa exactamente el mismo servicio que el backend (noox-id-back/face_recognition_service.py),
así que los números corresponden al sistema tal como está implementado.

Estructura esperada de las fotos (una carpeta por persona; usa códigos, no nombres):

    evaluacion/datos/fotos/
        P01/
            registro.jpg          <- foto de registro (enrolamiento). Si no existe, se usa la primera.
            luz-normal_01.jpg     <- intentos. El texto antes de "_" es la condición (opcional).
            luz-baja_01.jpg
        P02/
            ...

Protocolo por defecto ("nooxid"), igual que el login real:
  - genuino:  registro de P01 vs cada intento de P01
  - impostor: registro de P01 vs cada intento de cualquier otra persona (alguien que dice ser P01)
Con --protocolo todos se comparan todos los pares de fotos válidas.

Salidas (en --salida, por defecto evaluacion/resultados/):
  similitudes.csv, fallos_captura.csv, latencias.csv, resumen.md,
  figura_histograma.png/.svg, figura_far_frr.png/.svg

Uso:
  python evaluacion/evaluar_reconocimiento.py
  python evaluacion/evaluar_reconocimiento.py --fotos ruta/a/fotos --umbral 0.363
"""
from __future__ import annotations

import argparse
import csv
import math
import platform
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parents[1]          # .../Noox-id
sys.path.insert(0, str(RAIZ / 'noox-id-back'))
from face_recognition_service import DEFAULT_THRESHOLD, FaceError, FaceRecognitionService  # noqa: E402

EXTENSIONES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

# Paleta validada (categórica slots 1-2, CVD ΔE 24,7, contraste ≥ 3:1 sobre la superficie).
AZUL, NARANJA = '#2a78d6', '#eb6834'
TINTA, TINTA_2, REJILLA, SUPERFICIE = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'


# --------------------------------------------------------------------------- datos
@dataclass
class Foto:
    persona: str
    ruta: Path
    condicion: str
    vector: np.ndarray | None = None
    ms: float | None = None
    error: str | None = None


def condicion_de(ruta: Path) -> str:
    nombre = ruta.stem.lower()
    return nombre.split('_', 1)[0] if '_' in nombre else 'general'


def leer_imagen_bgr(ruta: Path) -> np.ndarray:
    """Lee la imagen respetando la orientación EXIF (fotos de celular) y la pasa a BGR."""
    with Image.open(ruta) as img:
        rgb = ImageOps.exif_transpose(img).convert('RGB')
    return np.ascontiguousarray(np.asarray(rgb)[:, :, ::-1])


def cargar_fotos(carpeta: Path) -> dict[str, list[Foto]]:
    personas: dict[str, list[Foto]] = {}
    for dir_persona in sorted(p for p in carpeta.iterdir() if p.is_dir()):
        fotos = [Foto(dir_persona.name, f, condicion_de(f))
                 for f in sorted(dir_persona.iterdir()) if f.suffix.lower() in EXTENSIONES]
        if fotos:
            personas[dir_persona.name] = fotos
    return personas


def extraer_vectores(servicio: FaceRecognitionService, personas: dict[str, list[Foto]]) -> None:
    total = sum(len(v) for v in personas.values())
    hechas = 0
    for fotos in personas.values():
        for foto in fotos:
            try:
                img = leer_imagen_bgr(foto.ruta)
                t0 = time.perf_counter()
                foto.vector = servicio.extract_face_encoding(img)
                foto.ms = (time.perf_counter() - t0) * 1000
            except FaceError as e:
                foto.error = str(e)
            except Exception as e:  # imagen corrupta, formato raro, etc.
                foto.error = f'No se pudo procesar: {e}'
            hechas += 1
            print(f'\r  Procesando fotos: {hechas}/{total}', end='', flush=True)
    print()


def elegir_registro(fotos: list[Foto]) -> Foto | None:
    validas = [f for f in fotos if f.vector is not None]
    preferidas = [f for f in validas if f.ruta.stem.lower().startswith('registro')]
    return (preferidas or validas or [None])[0]


def coseno(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # los vectores ya vienen normalizados L2


# ---------------------------------------------------------------------- métricas
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza de Wilson al 95 % para una proporción k/n."""
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def tasas(genuinos: np.ndarray, impostores: np.ndarray, umbral: float) -> tuple[float, float]:
    far = float(np.mean(impostores >= umbral)) if impostores.size else float('nan')
    frr = float(np.mean(genuinos < umbral)) if genuinos.size else float('nan')
    return far, frr


def calcular_eer(genuinos: np.ndarray, impostores: np.ndarray) -> tuple[float, float]:
    """Devuelve (EER, umbral) barriendo todos los valores observados."""
    candidatos = np.unique(np.concatenate([genuinos, impostores, [-1.0, 1.0001]]))
    mejor = (float('inf'), float('nan'), float('nan'))
    for u in candidatos:
        far, frr = tasas(genuinos, impostores, u)
        if abs(far - frr) < mejor[0]:
            mejor = (abs(far - frr), (far + frr) / 2, float(u))
    return mejor[1], mejor[2]


# --------------------------------------------------------- identificación 1:N con margen
def identificar(galeria: dict[str, np.ndarray], sondas: list[tuple[str, Foto]], tau: float, margen: float):
    """Política 1:N: se acepta solo si la mejor coincidencia es >= tau Y supera a la segunda mejor por >= margen.

    - Sondas de personas enroladas (galería completa): acierto, identificación errónea o rechazo.
    - Sondas "desconocidas": se simula quitando a esa persona de la galería (leave-one-out);
      cualquier aceptación es una falsa aceptación.
    Devuelve (resumen, detalle) donde detalle son las filas por sonda.
    """
    r = dict(n_enr=0, acierto=0, erronea=0, rechazo=0, rech_puntaje=0, rech_margen=0, n_desc=0, fa=0)
    detalle = []

    def decidir(gal: dict[str, np.ndarray], v: np.ndarray):
        if not gal:
            return None
        puntajes = sorted(((coseno(v, g), p) for p, g in gal.items()), reverse=True)
        s1, id1 = puntajes[0]
        s2 = puntajes[1][0] if len(puntajes) > 1 else -1.0
        return id1, s1, s2, (s1 >= tau and (s1 - s2) >= margen)

    for persona, foto in sondas:
        if foto.vector is None:
            continue
        if persona in galeria:
            d = decidir(galeria, foto.vector)
            r['n_enr'] += 1
            id1, s1, s2, ok = d
            if ok and id1 == persona:
                r['acierto'] += 1; res = 'acierto'
            elif ok:
                r['erronea'] += 1; res = 'identificacion_erronea'
            else:
                r['rechazo'] += 1; res = 'rechazo'
                if s1 < tau:
                    r['rech_puntaje'] += 1
                else:
                    r['rech_margen'] += 1
            detalle.append(('enrolado', persona, foto.ruta.name, id1, s1, s2, s1 - s2, ok, res))
        resto = {p: g for p, g in galeria.items() if p != persona}
        d = decidir(resto, foto.vector) if len(resto) >= 2 else None
        if d:
            id1, s1, s2, ok = d
            r['n_desc'] += 1
            r['fa'] += int(ok)
            detalle.append(('desconocido', persona, foto.ruta.name, id1, s1, s2, s1 - s2, ok,
                            'falsa_aceptacion' if ok else 'rechazo_correcto'))
    return r, detalle


# ----------------------------------------------------------------------- gráficos
def coma(x: float, decimales: int = 2) -> str:
    return f'{x:.{decimales}f}'.replace('.', ',')


def estilo_ejes(ax) -> None:
    import matplotlib.ticker as mticker
    ax.set_facecolor(SUPERFICIE)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    for lado in ('left', 'bottom'):
        ax.spines[lado].set_color(TINTA_2)
        ax.spines[lado].set_linewidth(0.8)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.grid(axis='y', color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: coma(v, 1)))


def guardar(fig, salida: Path, nombre: str) -> None:
    for ext in ('png', 'svg'):
        fig.savefig(salida / f'{nombre}.{ext}', dpi=300, bbox_inches='tight', facecolor=SUPERFICIE)


def figura_histograma(genuinos, impostores, umbral, salida: Path) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    fig, ax = plt.subplots(figsize=(6.5, 3.6), facecolor=SUPERFICIE)
    estilo_ejes(ax)
    todos = np.concatenate([genuinos, impostores])
    lo = math.floor(float(todos.min()) * 20) / 20
    hi = min(1.0, math.ceil(float(todos.max()) * 20) / 20 + 0.05)
    bins = np.arange(lo, hi + 1e-9, 0.025)
    series = [(impostores, NARANJA, '//', f'Impostores (n = {impostores.size})'),
              (genuinos, AZUL, None, f'Genuinos (n = {genuinos.size})')]
    for datos, color, trama, etiqueta in series:
        if not datos.size:
            continue
        cuenta, bordes = np.histogram(datos, bins=bins, weights=np.full(datos.size, 100 / datos.size))
        # Recorta al tramo con datos para que no quede una línea plana sobre el eje.
        con_datos = np.nonzero(cuenta)[0]
        i0, i1 = int(con_datos[0]), int(con_datos[-1]) + 1
        ax.stairs(cuenta[i0:i1], bordes[i0:i1 + 1], fill=True, color=color, alpha=0.30, hatch=trama,
                  edgecolor=color, linewidth=0)
        ax.stairs(cuenta[i0:i1], bordes[i0:i1 + 1], baseline=0, color=color, linewidth=2, label=etiqueta)
        # Etiqueta directa sobre el pico de cada distribución (identidad sin depender del color).
        i = int(np.argmax(cuenta))
        ax.annotate(etiqueta.split(' (')[0], ((bordes[i] + bordes[i + 1]) / 2, cuenta[i]),
                    xytext=(0, 6), textcoords='offset points', ha='center', fontsize=9, color=TINTA)
    ax.axvline(umbral, color=TINTA_2, linestyle=(0, (4, 3)), linewidth=1.5)
    ax.annotate(f'Umbral τ = {coma(umbral, 3)}', (umbral, 1), xycoords=('data', 'axes fraction'),
                xytext=(4, -2), textcoords='offset points', va='top', fontsize=9, color=TINTA_2)
    ax.set_xlabel('Similitud coseno (SFace)', color=TINTA, fontsize=10)
    ax.set_ylabel('Comparaciones (%)', color=TINTA, fontsize=10)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=6, integer=True))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.0f}'))
    ax.set_ylim(0, ax.get_ylim()[1] * 1.12)
    ax.legend(frameon=False, fontsize=9, loc='upper left', labelcolor=TINTA)
    guardar(fig, salida, 'figura_histograma')
    plt.close(fig)


def figura_far_frr(genuinos, impostores, umbral, eer, umbral_eer, salida: Path) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    # Desde la menor similitud observada: así FAR parte de 100 % y FRR llega a 100 %.
    inicio = min(0.0, math.floor(float(np.concatenate([genuinos, impostores]).min()) * 10) / 10)
    xs = np.linspace(inicio, 1.0, 501)
    far = np.array([tasas(genuinos, impostores, u)[0] for u in xs]) * 100
    frr = np.array([tasas(genuinos, impostores, u)[1] for u in xs]) * 100
    fig, ax = plt.subplots(figsize=(6.5, 3.6), facecolor=SUPERFICIE)
    estilo_ejes(ax)
    ax.plot(xs, far, color=AZUL, linewidth=2, label='FAR (impostores aceptados)')
    ax.plot(xs, frr, color=NARANJA, linewidth=2, linestyle=(0, (6, 3)), label='FRR (genuinos rechazados)')
    # Etiquetas directas en el extremo de cada curva.
    ax.annotate('FAR', (xs[0], far[0]), xytext=(4, 2), textcoords='offset points', fontsize=9, color=TINTA)
    ax.annotate('FRR', (xs[-1], frr[-1]), xytext=(-4, 2), textcoords='offset points', ha='right',
                fontsize=9, color=TINTA)
    if not math.isnan(eer) and inicio <= umbral_eer <= 1:
        # El valor va en la leyenda: una etiqueta junto al punto choca con las curvas según los datos.
        ax.plot([umbral_eer], [eer * 100], marker='o', markersize=8, linestyle='none', color=TINTA,
                markeredgecolor=SUPERFICIE, markeredgewidth=2, zorder=5,
                label=f'EER ≈ {coma(eer * 100, 1)} % (umbral ≈ {coma(umbral_eer, 3)})')
    ax.axvline(umbral, color=TINTA_2, linestyle=(0, (4, 3)), linewidth=1.5)
    ax.annotate(f'τ = {coma(umbral, 3)}', (umbral, 1), xycoords=('data', 'axes fraction'),
                xytext=(4, -2), textcoords='offset points', va='top', fontsize=9, color=TINTA_2)
    ax.set_xlabel('Umbral de similitud coseno', color=TINTA, fontsize=10)
    ax.set_ylabel('Tasa de error (%)', color=TINTA, fontsize=10)
    ax.set_ylim(-2, 102)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.0f}'))
    ax.legend(frameon=False, fontsize=9, loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=2,
              labelcolor=TINTA)
    guardar(fig, salida, 'figura_far_frr')
    plt.close(fig)


# -------------------------------------------------------------------------- main
def main() -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Evalúa FAR/FRR del reconocimiento facial de NooxID.')
    ap.add_argument('--fotos', type=Path, default=RAIZ / 'evaluacion' / 'datos' / 'fotos')
    ap.add_argument('--salida', type=Path, default=RAIZ / 'evaluacion' / 'resultados')
    ap.add_argument('--umbral', type=float, default=DEFAULT_THRESHOLD,
                    help=f'Umbral coseno a evaluar (por defecto {DEFAULT_THRESHOLD}, el del backend)')
    ap.add_argument('--protocolo', choices=['nooxid', 'todos'], default='nooxid')
    ap.add_argument('--umbral-id', type=float, default=0.50,
                    help='Identificación 1:N: similitud mínima de la mejor coincidencia (por defecto 0,50)')
    ap.add_argument('--margen', type=float, default=0.15,
                    help='Identificación 1:N: ventaja mínima sobre la segunda mejor coincidencia (por defecto 0,15)')
    ap.add_argument('--det-score', type=float, default=None,
                    help='Umbral de puntuación de YuNet (por defecto el del backend, 0,6; en producción 0,50)')
    args = ap.parse_args()

    if not args.fotos.is_dir():
        print(f'No existe la carpeta de fotos: {args.fotos}\nRevisa la estructura en el encabezado del script.')
        return 1
    personas = cargar_fotos(args.fotos)
    if len(personas) < 2:
        print('Se necesitan al menos 2 personas (subcarpetas) con fotos para medir impostores.')
        return 1
    args.salida.mkdir(parents=True, exist_ok=True)

    print(f'Personas: {len(personas)} | Fotos: {sum(len(v) for v in personas.values())}')
    servicio = FaceRecognitionService(tolerance=args.umbral)
    if args.det_score is not None:
        servicio._detector.setScoreThreshold(float(args.det_score))
    extraer_vectores(servicio, personas)

    todas = [f for fotos in personas.values() for f in fotos]
    fallidas = [f for f in todas if f.error]

    # --- pares de comparación
    filas = []  # (tipo, persona_ref, foto_ref, persona_prueba, foto_prueba, condicion, coseno)
    genuinos_fallidos = 0
    if args.protocolo == 'nooxid':
        registros = {p: elegir_registro(f) for p, f in personas.items()}
        sin_registro = [p for p, r in registros.items() if r is None]
        for p_ref, reg in registros.items():
            if reg is None:
                continue
            for p_prueba, fotos in personas.items():
                for foto in fotos:
                    if foto is reg:
                        continue
                    if foto.vector is None:
                        genuinos_fallidos += (p_prueba == p_ref)
                        continue
                    tipo = 'genuino' if p_prueba == p_ref else 'impostor'
                    filas.append((tipo, p_ref, reg.ruta.name, p_prueba, foto.ruta.name, foto.condicion,
                                  coseno(reg.vector, foto.vector)))
    else:
        sin_registro = [p for p, f in personas.items() if all(x.vector is None for x in f)]
        validas = [f for f in todas if f.vector is not None]
        for a, b in combinations(validas, 2):
            tipo = 'genuino' if a.persona == b.persona else 'impostor'
            filas.append((tipo, a.persona, a.ruta.name, b.persona, b.ruta.name, b.condicion,
                          coseno(a.vector, b.vector)))

    gen = np.array([r[6] for r in filas if r[0] == 'genuino'])
    imp = np.array([r[6] for r in filas if r[0] == 'impostor'])
    if not gen.size or not imp.size:
        print('No hay suficientes comparaciones genuinas e impostoras (¿cada persona tiene al menos 2 fotos válidas?).')
        for x in fallidas:
            print(f'  - {x.persona}/{x.ruta.name}: {x.error}')
        return 1

    far, frr = tasas(gen, imp, args.umbral)
    k_far, k_frr = int(np.sum(imp >= args.umbral)), int(np.sum(gen < args.umbral))
    ic_far, ic_frr = wilson(k_far, imp.size), wilson(k_frr, gen.size)
    eer, umbral_eer = calcular_eer(gen, imp)
    n_gen_total = gen.size + genuinos_fallidos
    frr_sistema = (k_frr + genuinos_fallidos) / n_gen_total if n_gen_total else float('nan')
    ms = [f.ms for f in todas if f.ms is not None]
    ms_ord = sorted(ms)
    p95 = ms_ord[min(len(ms_ord) - 1, math.ceil(0.95 * len(ms_ord)) - 1)] if ms_ord else float('nan')

    # --- CSV
    with open(args.salida / 'similitudes.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['tipo', 'persona_referencia', 'foto_referencia', 'persona_prueba', 'foto_prueba',
                    'condicion', 'coseno', f'aceptado_tau_{args.umbral}'])
        for r in filas:
            w.writerow([*r[:6], f'{r[6]:.6f}', 'si' if r[6] >= args.umbral else 'no'])
    with open(args.salida / 'fallos_captura.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['persona', 'foto', 'motivo'])
        for x in fallidas:
            w.writerow([x.persona, x.ruta.name, x.error])
    with open(args.salida / 'latencias.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['persona', 'foto', 'ms_extraccion'])
        for x in todas:
            if x.ms is not None:
                w.writerow([x.persona, x.ruta.name, f'{x.ms:.2f}'])

    # --- por condición (solo genuinos)
    por_cond = defaultdict(list)
    for r in filas:
        if r[0] == 'genuino':
            por_cond[r[5]].append(r[6] >= args.umbral)
    motivos = defaultdict(int)
    for x in fallidas:
        motivos[x.error] += 1

    # --- figuras
    import matplotlib
    matplotlib.use('Agg')
    figura_histograma(gen, imp, args.umbral, args.salida)
    figura_far_frr(gen, imp, args.umbral, eer, umbral_eer, args.salida)

    # --- resumen
    pct = lambda v: f'{coma(v * 100, 2)} %'
    ic = lambda t: f'[{coma(t[0] * 100, 1)} %; {coma(t[1] * 100, 1)} %]'
    lineas = [
        '# Resultados de la evaluación del reconocimiento facial',
        '',
        f'- Fecha: {datetime.now():%d/%m/%Y %H:%M}',
        f'- Protocolo: **{args.protocolo}** '
        + ('(foto de registro vs. intentos, como el login real)' if args.protocolo == 'nooxid' else '(todos los pares)'),
        f'- Modelos: YuNet `face_detection_yunet_2023mar.onnx` + SFace `face_recognition_sface_2021dec.onnx`',
        f'- Equipo: {platform.processor() or platform.machine()} · {platform.system()} {platform.release()} · '
        f'Python {platform.python_version()}',
        '',
        '## Muestra',
        '',
        '| Dato | Valor |',
        '|---|---|',
        f'| Personas | {len(personas)} |',
        f'| Fotos totales | {len(todas)} |',
        f'| Fotos rechazadas por el control de captura (FTA) | {len(fallidas)} ({pct(len(fallidas) / len(todas))}) |',
        f'| Personas sin foto de registro válida | {len(sin_registro)}{" (" + ", ".join(sin_registro) + ")" if sin_registro else ""} |',
        f'| Comparaciones genuinas | {gen.size} |',
        f'| Comparaciones impostoras | {imp.size} |',
        '',
        f'## Tasas de error con τ = {coma(args.umbral, 3)}',
        '',
        '| Métrica | Valor | IC 95 % (Wilson) |',
        '|---|---|---|',
        f'| FAR (impostores aceptados) | {pct(far)} ({k_far}/{imp.size}) | {ic(ic_far)} |',
        f'| FRR (genuinos rechazados en la comparación) | {pct(frr)} ({k_frr}/{gen.size}) | {ic(ic_frr)} |',
        f'| FRR del sistema (incluye fallos de captura genuinos) | {pct(frr_sistema)} '
        f'({k_frr + genuinos_fallidos}/{n_gen_total}) | — |',
        f'| EER aproximado | {pct(eer)} | umbral ≈ {coma(umbral_eer, 3)} |',
        '',
        '## Distribución de similitudes',
        '',
        '| | Media | Desv. est. | Mínimo | Máximo |',
        '|---|---|---|---|---|',
        f'| Genuinos | {coma(float(gen.mean()), 3)} | {coma(float(gen.std(ddof=1)) if gen.size > 1 else 0.0, 3)} | '
        f'{coma(float(gen.min()), 3)} | {coma(float(gen.max()), 3)} |',
        f'| Impostores | {coma(float(imp.mean()), 3)} | {coma(float(imp.std(ddof=1)) if imp.size > 1 else 0.0, 3)} | '
        f'{coma(float(imp.min()), 3)} | {coma(float(imp.max()), 3)} |',
        '',
        '## Latencia de extracción por foto (detección + alineación + embedding)',
        '',
        f'Media {coma(statistics.mean(ms), 1)} ms · mediana {coma(statistics.median(ms), 1)} ms · '
        f'p95 {coma(p95, 1)} ms (n = {len(ms)}).' if ms else 'Sin datos.',
        '',
    ]
    if len(por_cond) > 1 or 'general' not in por_cond:
        lineas += ['## Aceptación de intentos genuinos por condición', '',
                   '| Condición | Aceptados | Tasa |', '|---|---|---|']
        for cond, vals in sorted(por_cond.items()):
            lineas.append(f'| {cond} | {sum(vals)}/{len(vals)} | {pct(sum(vals) / len(vals))} |')
        lineas.append('')
    if motivos:
        lineas += ['## Motivos de rechazo en la captura', '', '| Motivo | Fotos |', '|---|---|']
        for m, n in sorted(motivos.items(), key=lambda kv: -kv[1]):
            lineas.append(f'| {m} | {n} |')
        lineas.append('')
    # --- identificación 1:N con margen (política de producción)
    registros_ok = {p: elegir_registro(f) for p, f in personas.items()}
    galeria = {p: r.vector for p, r in registros_ok.items() if r is not None}
    sondas = [(p, f) for p, fotos in personas.items() for f in fotos if f is not registros_ok[p]]
    if len(galeria) >= 3:
        res_id, detalle = identificar(galeria, sondas, args.umbral_id, args.margen)
        with open(args.salida / 'identificacion.csv', 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(['tipo_sonda', 'persona_real', 'foto', 'mejor_id', 'mejor_coseno', 'segundo_coseno',
                        'margen', 'aceptado', 'resultado'])
            for d in detalle:
                w.writerow([d[0], d[1], d[2], d[3], f'{d[4]:.6f}', f'{d[5]:.6f}', f'{d[6]:.6f}',
                            'si' if d[7] else 'no', d[8]])
        n_e, n_d = res_id['n_enr'], res_id['n_desc']
        fila = lambda k, n: f'{pct(k / n)} ({k}/{n}) · IC 95 % {ic(wilson(k, n))}' if n else '—'
        lineas += [
            '## Identificación 1:N con margen (política de producción)',
            '',
            f'Regla: se acepta solo si la mejor coincidencia de la galería es ≥ {coma(args.umbral_id, 2)} '
            f'**y** supera a la segunda mejor por ≥ {coma(args.margen, 2)}. Galería: {len(galeria)} personas '
            '(su foto de registro). Las personas "desconocidas" se simulan quitando a la persona de la galería '
            '(leave-one-out).',
            '',
            '| Resultado | Valor |',
            '|---|---|',
            f'| Identificación correcta (enrolados) | {fila(res_id["acierto"], n_e)} |',
            f'| Identificación errónea (aceptado como otra persona) | {fila(res_id["erronea"], n_e)} |',
            f'| Rechazo de enrolados (falso rechazo) | {fila(res_id["rechazo"], n_e)} |',
            f'| — de ellos, por similitud baja / por margen insuficiente | {res_id["rech_puntaje"]} / {res_id["rech_margen"]} |',
            f'| Falsa aceptación de desconocidos | {fila(res_id["fa"], n_d)} |',
            '',
            '### Sensibilidad al umbral y al margen',
            '',
            '| τ | Margen | Correcta | Errónea | Falso rechazo | Falsa aceptación (desconocidos) |',
            '|---|---|---|---|---|---|',
        ]
        for tau in sorted({round(DEFAULT_THRESHOLD, 3), 0.40, 0.50, 0.60, round(args.umbral_id, 3)}):
            for mar in sorted({0.0, 0.05, 0.10, 0.15, 0.20, round(args.margen, 3)}):
                rr, _ = identificar(galeria, sondas, tau, mar)
                marca = '**' if (abs(tau - args.umbral_id) < 1e-9 and abs(mar - args.margen) < 1e-9) else ''
                p_ = lambda k, n: pct(k / n) if n else '—'
                lineas.append(f'| {marca}{coma(tau, 3)}{marca} | {marca}{coma(mar, 2)}{marca} | '
                              f'{p_(rr["acierto"], rr["n_enr"])} | {p_(rr["erronea"], rr["n_enr"])} | '
                              f'{p_(rr["rechazo"], rr["n_enr"])} | {p_(rr["fa"], rr["n_desc"])} |')
        lineas += ['', f'Con una galería de solo {len(galeria)} personas, el margen casi no se pone a prueba: '
                       'repite el análisis con la galería real cuando esté disponible.', '']
    else:
        lineas += ['## Identificación 1:N con margen', '',
                   'Se necesitan al menos 3 personas con foto de registro válida para evaluarla.', '']

    lineas += [
        '## Figuras generadas',
        '',
        '- `figura_histograma.png`: distribución de similitudes genuinas vs. impostoras con el umbral.',
        '- `figura_far_frr.png`: FAR y FRR en función del umbral, con el punto EER.',
        '',
        '> Nota para el artículo: con muestras pequeñas, reporta siempre el intervalo de confianza. '
        'Un FAR de 0 % con pocas comparaciones no significa que el sistema nunca acepte impostores.',
    ]
    (args.salida / 'resumen.md').write_text('\n'.join(lineas) + '\n', encoding='utf-8')

    print(f'\nFAR = {pct(far)} · FRR = {pct(frr)} · EER ≈ {pct(eer)} (umbral {coma(umbral_eer, 3)})')
    print(f'Fallos de captura: {len(fallidas)} de {len(todas)}')
    print(f'Resultados en: {args.salida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
