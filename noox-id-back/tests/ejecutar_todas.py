"""Ejecuta todas las pruebas automáticas de NooxID y resume el resultado.

    cd noox-id-back
    python tests/ejecutar_todas.py

Cada prueba corre en su propio proceso con una base SQLite temporal y un SMTP simulado (no toca tu base ni envía correos).
Cubre: registro y verificación del correo, código por correo, TOTP, inicio de sesión con Google, roles y permisos, límites de
intentos, API keys con hash, pertenencia usuario-aplicación, aviso de acceso y configuración del servidor.
"""
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PRUEBAS = sorted(AQUI.glob('prueba_*.py'))


def main() -> int:
    fallos = 0
    t0 = time.time()
    for p in PRUEBAS:
        t = time.time()
        r = subprocess.run([sys.executable, '-X', 'utf8', str(p)], capture_output=True, text=True, encoding='utf-8', errors='replace')
        ok = r.returncode == 0
        fallos += not ok
        print(f"{'OK   ' if ok else 'FALLA'}  {p.name:<34} {time.time() - t:5.1f} s")
        if not ok:
            print('\n'.join('      ' + l for l in (r.stdout + r.stderr).strip().splitlines()[-12:]))
    print(f'\n{len(PRUEBAS) - fallos}/{len(PRUEBAS)} pruebas correctas en {time.time() - t0:.0f} s')
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
