"""Mide la latencia de punta a punta del endpoint /api/face/verify-user de NooxID.

Levanta la API en memoria (cliente de pruebas de Flask), con una base SQLite temporal y el servicio facial REAL (YuNet + SFace):
registra un usuario con una foto de LFW, crea una app con su API key y llama N veces a verify-user con otra foto de la misma
persona (genuino) y con una foto de otra persona (impostor). El tiempo incluye decodificar el JSON y la imagen, consultar la
base de datos, detectar, alinear, extraer el vector y comparar. No incluye la red.

Uso:
    python evaluacion/medir_latencia_api.py --datos RUTA_A_LA_CARPETA_CON_lfw [--n 100]
Salida: evaluacion/resultados_lfw/latencia_api.json
"""
import argparse
import base64
import contextlib
import io
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BACK = RAIZ / 'noox-id-back'


def data_url(ruta: Path) -> str:
    return 'data:image/jpeg;base64,' + base64.b64encode(ruta.read_bytes()).decode()


def resumen(ms):
    ms = sorted(ms)
    p = lambda q: ms[min(len(ms) - 1, int(round(q * (len(ms) - 1))))]
    return {'n': len(ms), 'media': statistics.mean(ms), 'mediana': statistics.median(ms), 'p95': p(0.95), 'max': ms[-1], 'min': ms[0]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--datos', required=True)
    ap.add_argument('--n', type=int, default=100)
    a = ap.parse_args()
    lfw = Path(a.datos) / 'lfw'
    registro = lfw / 'George_W_Bush' / 'George_W_Bush_0001.jpg'
    genuina = lfw / 'George_W_Bush' / 'George_W_Bush_0002.jpg'
    impostora = lfw / 'Colin_Powell' / 'Colin_Powell_0001.jpg'

    os.chdir(BACK)
    sys.path.insert(0, str(BACK))
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'lat.db').replace('\\', '/')
    os.environ['MAIL_CONSOLE'] = 'true'
    os.environ['ACCESS_NOTIFY'] = 'false'
    os.environ['SECRET_KEY'] = 'medicion-de-latencia'
    from app import create_app
    from models import User, db
    with contextlib.redirect_stdout(io.StringIO()):
        app = create_app()
    c = app.test_client()
    c.post('/api/auth/register', json={'firstname': 'L', 'lastname': 'P', 'email': 'lat@x.com', 'password': 'pw12345'})
    with app.app_context():
        u = User.query.filter_by(email='lat@x.com').first(); u.verified = True; db.session.commit()
    tok = c.post('/api/auth/login', json={'email': 'lat@x.com', 'password': 'pw12345'}).get_json()['token']
    H = {'Authorization': 'Bearer ' + tok}
    st = c.post('/api/users/upload-face', json={'base64imageprofile': data_url(registro)}, headers=H)
    assert st.status_code == 200, st.get_json()
    app_d = c.post('/api/apps/', json={'name_app': 'Medición'}, headers=H).get_json()['app']
    c.post(f"/api/apps/{app_d['id']}/users", json={'email': 'lat@x.com'}, headers={**H})
    AH = {'X-API-Key': app_d['api_key'], 'X-App-ID': str(app_d['id'])}

    def llamada(ruta):
        cuerpo = {'user_email': 'lat@x.com', 'face_image': data_url(ruta)}
        t0 = time.perf_counter()
        r = c.post('/api/face/verify-user', json=cuerpo, headers=AH)
        dt = (time.perf_counter() - t0) * 1000
        return dt, r.get_json()

    import routes.face_recognition_routes as FR
    for _ in range(3):
        llamada(genuina)                           # calentamiento
    res = {}
    for nombre, ruta in (('genuino', genuina), ('impostor', impostora)):
        tiempos, veredictos = [], []
        for _ in range(a.n):
            import throttle
            throttle.FACE.reset(f"vu:{app_d['id']}:lat@x.com")   # los intentos fallidos no deben bloquear la medición
            dt, d = llamada(ruta)
            tiempos.append(dt); veredictos.append(bool(d.get('authenticated')))
        res[nombre] = {**resumen(tiempos), 'aceptados': sum(veredictos)}
    res['equipo'] = {'sistema': platform.platform(), 'cpu': platform.processor(), 'python': platform.python_version()}
    res['nota'] = 'Tiempo de servidor en proceso (sin red): JSON + imagen + base de datos + YuNet + SFace.'
    salida = RAIZ / 'evaluacion' / 'resultados_lfw'
    salida.mkdir(exist_ok=True)
    (salida / 'latencia_api.json').write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding='utf-8')
    for k in ('genuino', 'impostor'):
        r = res[k]
        print(f"{k}: n={r['n']} media={r['media']:.1f} ms mediana={r['mediana']:.1f} p95={r['p95']:.1f} máx={r['max']:.1f} | aceptados {r['aceptados']}/{r['n']}")


if __name__ == '__main__':
    main()
