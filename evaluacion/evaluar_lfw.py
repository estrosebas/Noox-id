"""Evalúa el reconocimiento facial de NooxID (YuNet + SFace) con LFW, un conjunto público de rostros.

Usa el MISMO servicio que el backend (noox-id-back/face_recognition_service.py), con sus controles de calidad, así que
los números corresponden al sistema tal como está implementado. No se necesitan voluntarios ni datos personales.

Qué mide:
  1. Verificación 1:1 con los 6 000 pares del protocolo estándar de LFW (3 000 del mismo sujeto y 3 000 de sujetos distintos):
     FAR, FRR y EER con intervalos de Wilson al 95 %, en el umbral de NooxID (0,363) y en el de la política 1:N (0,50),
     y la exactitud con el protocolo de 10 pliegues (umbral elegido en 9 pliegues y probado en el restante).
  2. Identificación 1:N: galería con una foto por persona (las que tienen ≥ 2 fotos), sondas = sus otras fotos, y como
     «desconocidos» las personas con una sola foto. Regla de aceptación: mejor coincidencia ≥ umbral y ventaja ≥ margen.
  3. Latencia por imagen del canal detección + alineación + extracción.

Datos (fuera del repositorio):
    <carpeta>/lfw/<Persona>/<Persona>_0001.jpg      (lfw.tgz descomprimido)
    <carpeta>/pairs.txt

Uso:
    python evaluacion/evaluar_lfw.py --datos RUTA_A_LA_CARPETA
Salida: evaluacion/resultados_lfw/ (metricas.json, resumen.md, pares.csv, figuras PNG/SVG) y un caché de vectores en la carpeta de datos.
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from evaluar_reconocimiento import calcular_eer, leer_imagen_bgr, tasas, wilson  # noqa: E402

RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / 'noox-id-back'))
from face_recognition_service import DEFAULT_THRESHOLD, FaceError, FaceRecognitionService  # noqa: E402

AZUL, NARANJA, TINTA, TINTA_2, REJILLA = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3df'
UMBRAL_1N, MARGEN_1N = 0.50, 0.15


# --------------------------------------------------------------------------- datos
def ruta_foto(base: Path, nombre: str, n: int) -> Path:
    return base / 'lfw' / nombre / f'{nombre}_{n:04d}.jpg'


def leer_pares(archivo: Path):
    """Devuelve [(pliegue, es_mismo, (nombre,n), (nombre,n))] del protocolo de 10 pliegues de LFW."""
    lineas = archivo.read_text(encoding='utf-8').split('\n')
    pliegues, por_pliegue = map(int, lineas[0].split())
    pares, i = [], 1
    for p in range(pliegues):
        for _ in range(por_pliegue):
            nombre, a, b = lineas[i].split(); i += 1
            pares.append((p, True, (nombre, int(a)), (nombre, int(b))))
        for _ in range(por_pliegue):
            n1, a, n2, b = lineas[i].split(); i += 1
            pares.append((p, False, (n1, int(a)), (n2, int(b))))
    return pares


def todas_las_fotos(base: Path) -> list[tuple[str, int]]:
    fotos = []
    for d in sorted((base / 'lfw').iterdir()):
        if d.is_dir():
            for f in sorted(d.glob('*.jpg')):
                fotos.append((d.name, int(f.stem.rsplit('_', 1)[1])))
    return fotos


def vectores(servicio, base: Path, fotos, cache: Path):
    """Vector de 128 dim por foto (None si el servicio la rechaza) y tiempo en ms. Se guarda en caché."""
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        return list(z['claves']), z['vec'], z['ms'], list(z['err'])
    claves = [f'{n}|{k}' for n, k in fotos]
    vec = np.full((len(fotos), 128), np.nan, dtype=np.float32)
    ms = np.full(len(fotos), np.nan)
    err = [''] * len(fotos)
    t_ini = time.time()
    for i, (n, k) in enumerate(fotos):
        try:
            img = leer_imagen_bgr(ruta_foto(base, n, k))
            t0 = time.perf_counter()
            v = servicio.extract_face_encoding(img)
            ms[i] = (time.perf_counter() - t0) * 1000
            vec[i] = v
        except FaceError as e:
            err[i] = str(e)
        except Exception as e:  # noqa: BLE001
            err[i] = f'error: {e}'
        if i % 250 == 0:
            print(f'\r  {i}/{len(fotos)} fotos ({time.time() - t_ini:.0f} s)', end='', flush=True)
    print()
    np.savez(cache, claves=np.array(claves), vec=vec, ms=ms, err=np.array(err))
    return claves, vec, ms, err


# ------------------------------------------------------------------------- 1:1
def evaluar_1a1(pares, idx, vec):
    gen, imp, pliegue_gen, pliegue_imp, excluidos = [], [], [], [], 0
    filas = []
    for p, mismo, a, b in pares:
        ia, ib = idx[f'{a[0]}|{a[1]}'], idx[f'{b[0]}|{b[1]}']
        if np.isnan(vec[ia, 0]) or np.isnan(vec[ib, 0]):
            excluidos += 1
            filas.append((p, int(mismo), a, b, ''))
            continue
        s = float(np.dot(vec[ia], vec[ib]))
        (gen if mismo else imp).append(s)
        (pliegue_gen if mismo else pliegue_imp).append(p)
        filas.append((p, int(mismo), a, b, f'{s:.5f}'))
    return np.array(gen), np.array(imp), np.array(pliegue_gen), np.array(pliegue_imp), excluidos, filas


def fila_umbral(gen, imp, umbral):
    far, frr = tasas(gen, imp, umbral)
    kf, kr = int(round(far * imp.size)), int(round(frr * gen.size))
    return {'umbral': umbral, 'far': far, 'far_ic': wilson(kf, imp.size), 'far_k': kf, 'far_n': int(imp.size),
            'frr': frr, 'frr_ic': wilson(kr, gen.size), 'frr_k': kr, 'frr_n': int(gen.size),
            'exactitud': 1 - (kf + kr) / (imp.size + gen.size)}


def diez_pliegues(gen, imp, pg, pi):
    """Protocolo de LFW: el umbral se elige en 9 pliegues y se prueba en el décimo."""
    accs, umbrales = [], []
    for k in range(10):
        entr_g, entr_i = gen[pg != k], imp[pi != k]
        cand = np.unique(np.concatenate([entr_g, entr_i]))
        mejor = max(cand, key=lambda u: (np.sum(entr_g >= u) + np.sum(entr_i < u)))
        prue_g, prue_i = gen[pg == k], imp[pi == k]
        accs.append((np.sum(prue_g >= mejor) + np.sum(prue_i < mejor)) / (prue_g.size + prue_i.size))
        umbrales.append(float(mejor))
    return float(np.mean(accs)), float(np.std(accs)), float(np.mean(umbrales))


# ------------------------------------------------------------------------- 1:N
def evaluar_1an(fotos, vec):
    por_persona: dict[str, list[int]] = {}
    for i, (n, _) in enumerate(fotos):
        if not np.isnan(vec[i, 0]):
            por_persona.setdefault(n, []).append(i)
    galeria_i, sondas_i, sondas_dueno, desconocidas_i = [], [], [], []
    nombres_galeria = []
    for n, lst in por_persona.items():
        if len(lst) >= 2:
            galeria_i.append(lst[0]); nombres_galeria.append(n)
            for j in lst[1:]:
                sondas_i.append(j); sondas_dueno.append(len(galeria_i) - 1)
        else:
            desconocidas_i.append(lst[0])
    G = vec[galeria_i]
    sondas_dueno = np.array(sondas_dueno)

    def top2(P):
        S = P @ G.T
        orden = np.argsort(-S, axis=1)[:, :2]
        s1 = S[np.arange(len(P)), orden[:, 0]]
        s2 = S[np.arange(len(P)), orden[:, 1]]
        return orden[:, 0], s1, s2

    e_arg, e_s1, e_s2 = top2(vec[sondas_i])
    d_arg, d_s1, d_s2 = top2(vec[desconocidas_i])
    filas = []
    for tau in (0.363, 0.50, 0.60):
        for margen in (0.0, 0.05, 0.10, 0.15, 0.20):
            acepta_e = (e_s1 >= tau) & ((e_s1 - e_s2) >= margen)
            acierto = acepta_e & (e_arg == sondas_dueno)
            erronea = acepta_e & (e_arg != sondas_dueno)
            rech_puntaje = ~acepta_e & (e_s1 < tau)
            rech_margen = ~acepta_e & (e_s1 >= tau)
            acepta_d = (d_s1 >= tau) & ((d_s1 - d_s2) >= margen)
            n_e, n_d = len(sondas_i), len(desconocidas_i)
            filas.append({'umbral': tau, 'margen': margen,
                          'acierto': acierto.mean(), 'erronea': erronea.mean(),
                          'rechazo_puntaje': rech_puntaje.mean(), 'rechazo_margen': rech_margen.mean(),
                          'fa_desconocidos': acepta_d.mean(),
                          'fa_desconocidos_ic': wilson(int(acepta_d.sum()), n_d), 'erronea_ic': wilson(int(erronea.sum()), n_e)})
    return {'galeria': len(galeria_i), 'sondas': len(sondas_i), 'desconocidas': len(desconocidas_i), 'filas': filas}


# ------------------------------------------------------------------------ figuras
def figuras(gen, imp, salida: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.edgecolor': TINTA_2, 'axes.labelcolor': TINTA,
                         'xtick.color': TINTA_2, 'ytick.color': TINTA_2})
    coma = lambda v, _p: f'{v:.2f}'.replace('.', ',')

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    bins = np.linspace(-0.2, 1.0, 61)
    ax.hist(imp, bins=bins, color=NARANJA, alpha=.85, hatch='///', edgecolor='white', label=f'Distintos (n = {imp.size})')
    ax.hist(gen, bins=bins, color=AZUL, alpha=.85, edgecolor='white', label=f'Mismo sujeto (n = {gen.size})')
    ax.set_ylim(0, ax.get_ylim()[1] * 1.28)          # espacio arriba para rótulos y leyenda
    for u, ls, ha, dx in ((0.363, '-', 'right', -.012), (0.50, '--', 'left', .012)):
        ax.axvline(u, color=TINTA, ls=ls, lw=1.2)
        ax.text(u + dx, ax.get_ylim()[1] * .93, f'τ = {str(u).replace(".", ",")}', fontsize=8.5, color=TINTA, ha=ha)
    ax.set_xlabel('Similitud coseno'); ax.set_ylabel('Pares')
    ax.xaxis.set_major_formatter(plt.FuncFormatter(coma)); ax.legend(frameon=False, fontsize=8.5, loc='upper left')
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(salida / 'figura_histograma.png', dpi=300); fig.savefig(salida / 'figura_histograma.svg'); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    u = np.linspace(0.0, 0.8, 321)
    far = [np.mean(imp >= x) * 100 for x in u]; frr = [np.mean(gen < x) * 100 for x in u]
    ax.plot(u, far, color=NARANJA, lw=2, ls='--', label='FAR (falsa aceptación)')
    ax.plot(u, frr, color=AZUL, lw=2, label='FRR (falso rechazo)')
    eer, ue = calcular_eer(gen, imp)
    ax.plot([ue], [eer * 100], 'o', color=TINTA, ms=5); ax.annotate(f'EER = {eer*100:.2f}'.replace('.', ',') + f' %\nτ = {ue:.3f}'.replace('.', ','),
        (ue, eer * 100), (ue + .06, 20), fontsize=8.5, arrowprops=dict(arrowstyle='-', color=TINTA_2))
    for x in (0.363, 0.50): ax.axvline(x, color=TINTA, lw=.8, ls=':')
    ax.set_xlabel('Umbral τ'); ax.set_ylabel('Tasa (%)'); ax.set_ylim(0, 100)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(coma)); ax.legend(frameon=False, fontsize=8.5)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(salida / 'figura_far_frr.png', dpi=300); fig.savefig(salida / 'figura_far_frr.svg'); plt.close(fig)


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='Evalúa NooxID con LFW')
    ap.add_argument('--datos', required=True, help='carpeta con lfw/ y pairs.txt')
    ap.add_argument('--salida', default=str(RAIZ / 'evaluacion' / 'resultados_lfw'))
    a = ap.parse_args()
    base, salida = Path(a.datos), Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)

    servicio = FaceRecognitionService()
    fotos = todas_las_fotos(base)
    print(f'LFW: {len(fotos)} fotos')
    claves, vec, ms, err = vectores(servicio, base, fotos, base / 'vectores_nooxid.npz')
    idx = {c: i for i, c in enumerate(claves)}
    ok = ~np.isnan(vec[:, 0])
    rechazos: dict[str, int] = {}
    for e in err:
        if e:
            rechazos[e.split(':')[0][:70]] = rechazos.get(e.split(':')[0][:70], 0) + 1

    pares = leer_pares(base / 'pairs.txt')
    gen, imp, pg, pi, excluidos, filas_pares = evaluar_1a1(pares, idx, vec)
    eer, u_eer = calcular_eer(gen, imp)
    acc, acc_sd, u_medio = diez_pliegues(gen, imp, pg, pi)
    res_1a1 = [fila_umbral(gen, imp, DEFAULT_THRESHOLD), fila_umbral(gen, imp, UMBRAL_1N), fila_umbral(gen, imp, u_eer)]
    res_1an = evaluar_1an(fotos, vec)
    tiempos = ms[~np.isnan(ms)]

    # el sistema también «falla» cuando rechaza la foto: FAR/FRR del sistema consideran esos pares
    metricas = {
        'generado': datetime.now().isoformat(timespec='seconds'),
        'equipo': {'sistema': platform.platform(), 'cpu': platform.processor(), 'python': platform.python_version()},
        'dataset': {'fotos': len(fotos), 'fotos_validas': int(ok.sum()), 'fotos_rechazadas': int((~ok).sum()),
                    'motivos_rechazo': rechazos, 'pares': len(pares), 'pares_excluidos': int(excluidos),
                    'genuinos': int(gen.size), 'impostores': int(imp.size)},
        'verificacion': {'filas': res_1a1, 'eer': eer, 'umbral_eer': u_eer,
                         'exactitud_10_pliegues': acc, 'exactitud_sd': acc_sd, 'umbral_medio_pliegues': u_medio,
                         'media_genuinos': float(gen.mean()), 'media_impostores': float(imp.mean()),
                         'sd_genuinos': float(gen.std()), 'sd_impostores': float(imp.std())},
        'identificacion': res_1an,
        'latencia_ms': {'n': int(tiempos.size), 'media': float(tiempos.mean()), 'mediana': float(np.median(tiempos)),
                        'p95': float(np.percentile(tiempos, 95)), 'p99': float(np.percentile(tiempos, 99)),
                        'max': float(tiempos.max())},
        'umbral_nooxid': DEFAULT_THRESHOLD, 'umbral_1n': UMBRAL_1N, 'margen_1n': MARGEN_1N,
    }
    (salida / 'metricas.json').write_text(json.dumps(metricas, indent=2, ensure_ascii=False, default=float), encoding='utf-8')
    with open(salida / 'pares.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['pliegue', 'mismo_sujeto', 'foto_a', 'foto_b', 'similitud'])
        for p, m, a_, b_, s in filas_pares: w.writerow([p, m, f'{a_[0]}_{a_[1]:04d}', f'{b_[0]}_{b_[1]:04d}', s])
    figuras(gen, imp, salida)

    r = metricas['verificacion']['filas']
    print(f"\nPares válidos: {gen.size} genuinos + {imp.size} impostores (excluidos {excluidos}); fotos rechazadas: {int((~ok).sum())}")
    for fila in r:
        print(f"  τ={fila['umbral']:.3f}  FAR={fila['far']*100:.2f}% {tuple(round(x*100,2) for x in fila['far_ic'])}  FRR={fila['frr']*100:.2f}% {tuple(round(x*100,2) for x in fila['frr_ic'])}")
    print(f"  EER={eer*100:.2f}% en τ={u_eer:.3f} | exactitud 10 pliegues = {acc*100:.2f} ± {acc_sd*100:.2f} %")
    print(f"  1:N galería={res_1an['galeria']} sondas={res_1an['sondas']} desconocidas={res_1an['desconocidas']}")
    print(f"  latencia ms: {metricas['latencia_ms']}")


if __name__ == '__main__':
    main()
