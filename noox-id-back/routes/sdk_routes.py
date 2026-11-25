"""SDK de captura facial que NooxID sirve a las apps cliente (públicos, solo lectura).

    GET /sdk/noox-face.js                      el componente de cámara
    GET /sdk/vendor/vision_bundle.mjs          MediaPipe Tasks Vision (Apache-2.0)
    GET /sdk/mediapipe/...                     WASM de MediaPipe y modelo BlazeFace

Así la app que integra NooxID no instala MediaPipe ni el modelo: los "jala" directo de NooxID. Los archivos de
MediaPipe se buscan en MEDIAPIPE_DIR, en static/sdk/mediapipe (imagen Docker) o en noox-id/public/mediapipe (monorepo).
"""
import os
from pathlib import Path

from flask import Blueprint, abort, make_response, send_from_directory

sdk_bp = Blueprint('sdk', __name__)

BACK = Path(__file__).resolve().parent.parent
SDK_DIR = BACK / 'static' / 'sdk'


def _mediapipe_dir():
    candidatos = [os.environ.get('MEDIAPIPE_DIR'), SDK_DIR / 'mediapipe', BACK.parent / 'noox-id' / 'public' / 'mediapipe']
    for c in candidatos:
        if c and Path(c).is_dir():
            return Path(c)
    return None


# Windows no conoce .mjs/.wasm: sin el tipo correcto el navegador rechaza el módulo o el WASM
TIPOS = {'.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm',
         '.tflite': 'application/octet-stream', '.map': 'application/json'}


def _servir(directorio, ruta):
    if directorio is None:
        abort(404)
    resp = make_response(send_from_directory(directorio, ruta, conditional=True))
    tipo = TIPOS.get(Path(ruta).suffix.lower())
    if tipo:
        resp.headers['Content-Type'] = tipo
    # recursos públicos: cualquier app puede cargarlos desde su propio origen
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


@sdk_bp.route('/sdk/mediapipe/<path:ruta>', methods=['GET'])
def mediapipe(ruta):
    return _servir(_mediapipe_dir(), ruta)


@sdk_bp.route('/sdk/<path:ruta>', methods=['GET'])
def sdk(ruta):
    return _servir(SDK_DIR, ruta)
