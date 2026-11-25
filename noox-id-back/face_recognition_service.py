"""Reconocimiento facial con YuNet (detección) + SFace (embeddings) vía OpenCV.

Mantiene la API pública del servicio anterior (dlib/face_recognition) para que las
rutas no cambien. Diferencias importantes:

- Embedding SFace: 128 floats float32 (512 bytes), normalizado L2.
- Similitud: coseno. `distance = 1 - coseno`; `match` si coseno >= `threshold`.
- Los vectores antiguos de dlib (128 float64 = 1024 bytes) NO son compatibles y se
  rechazan con un mensaje claro: el usuario debe registrar de nuevo su rostro.
"""
import base64
import os
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

MODEL_DIR = Path(os.environ.get('FACE_MODEL_DIR', Path(__file__).parent / 'models' / 'sface_yunet'))
DETECTOR_FILE = MODEL_DIR / 'face_detection_yunet_2023mar.onnx'
RECOGNIZER_FILE = MODEL_DIR / 'face_recognition_sface_2021dec.onnx'

EMBEDDING_DIM = 128
EMBEDDING_BYTES = EMBEDDING_DIM * 4  # float32
MAX_SIDE = 1280  # se reduce el lado mayor para acotar el costo de detección

# Umbral coseno recomendado por OpenCV para SFace en verificación 1:1.
DEFAULT_THRESHOLD = float(os.environ.get('FACE_RECOGNITION_THRESHOLD', '0.363'))


class FaceError(Exception):
    """Error de validación facial con mensaje apto para mostrar al usuario."""


class FaceRecognitionService:
    def __init__(self, tolerance=DEFAULT_THRESHOLD):
        # `tolerance` conserva el nombre por compatibilidad con /api/face/tolerance,
        # pero ahora es el umbral mínimo de similitud coseno (0-1).
        self.tolerance = tolerance
        for path in (DETECTOR_FILE, RECOGNIZER_FILE):
            if not path.is_file():
                raise FileNotFoundError(f'Falta el modelo facial: {path}')
        cv2.setNumThreads(int(os.environ.get('FACE_CPU_THREADS', '2')))
        self._detector = cv2.FaceDetectorYN.create(
            str(DETECTOR_FILE), '', (320, 320), score_threshold=0.6)
        self._recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_FILE), '')

    # ------------------------------------------------------------------ imágenes
    def image_to_base64(self, image_path):
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def base64_to_image(self, base64_string):
        """Devuelve una imagen BGR (numpy) lista para OpenCV."""
        try:
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',', 1)[1]
            image = Image.open(BytesIO(base64.b64decode(base64_string))).convert('RGB')
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            raise FaceError('No se pudo leer la imagen enviada') from e

    # ----------------------------------------------------------------- detección
    def _detect(self, image_bgr):
        h, w = image_bgr.shape[:2]
        scale = min(1.0, MAX_SIDE / max(h, w))
        if scale < 1.0:
            image_bgr = cv2.resize(image_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        self._detector.setInputSize((image_bgr.shape[1], image_bgr.shape[0]))
        _, rows = self._detector.detect(image_bgr)
        return image_bgr, ([] if rows is None else list(rows))

    @staticmethod
    def _check_quality(image, row):
        """Controles básicos de calidad: encuadre, tamaño, nitidez y luz."""
        h, w = image.shape[:2]
        x, y, bw, bh = (float(v) for v in row[:4])
        if x < 0 or y < 0 or x + bw > w or y + bh > h:
            raise FaceError('Tu rostro está cortado. Aléjate un poco y vuelve a intentarlo')
        if min(bw, bh) < 60 or bh / h < 0.20:
            raise FaceError('Tu rostro se ve muy pequeño. Acércate a la cámara')
        crop = image[int(y):int(y + bh), int(x):int(x + bw)]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if cv2.Laplacian(gray, cv2.CV_64F).var() < 20.0:
            raise FaceError('La fotografía está borrosa. Mantente quieto y vuelve a tomarla')
        if not 20 <= float(gray.mean()) <= 235:
            raise FaceError('Mala iluminación. Mejora la luz sobre tu rostro')

    # --------------------------------------------------------------- embeddings
    def extract_face_encoding(self, image_data):
        """Extrae el embedding SFace (np.float32, 128, normalizado L2)."""
        image = self.base64_to_image(image_data) if isinstance(image_data, str) else image_data
        image, rows = self._detect(image)
        if not rows:
            raise FaceError('No se detectó ningún rostro en la imagen')
        if len(rows) > 1:
            raise FaceError('Debe aparecer una sola persona en la fotografía')
        self._check_quality(image, rows[0])
        aligned = self._recognizer.alignCrop(image, rows[0])
        vector = np.asarray(self._recognizer.feature(aligned), dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if vector.shape != (EMBEDDING_DIM,) or not np.isfinite(vector).all() or norm <= 0:
            raise FaceError('No se pudo extraer el vector facial')
        return vector / norm

    def encoding_to_base64(self, encoding):
        return base64.b64encode(np.asarray(encoding, dtype=np.float32).tobytes()).decode('utf-8')

    def base64_to_encoding(self, base64_encoding):
        raw = base64.b64decode(base64_encoding)
        if len(raw) != EMBEDDING_BYTES:
            # 1024 bytes = vector antiguo de dlib (float64): incompatible con SFace.
            raise FaceError('Tu registro facial es de una versión anterior. Registra tu rostro de nuevo')
        return np.frombuffer(raw, dtype=np.float32)

    # --------------------------------------------------------------- comparación
    def compare_faces(self, known_encoding, unknown_encoding):
        if isinstance(known_encoding, str):
            known_encoding = self.base64_to_encoding(known_encoding)
        if isinstance(unknown_encoding, str):
            unknown_encoding = self.base64_to_encoding(unknown_encoding)
        a = np.asarray(known_encoding, dtype=np.float32).reshape(-1)
        b = np.asarray(unknown_encoding, dtype=np.float32).reshape(-1)
        a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
        cosine = float(np.dot(a, b))
        return {
            'match': cosine >= self.tolerance,
            'distance': 1.0 - cosine,
            'confidence': max(0.0, min(1.0, cosine)),
        }

    def verify_user_face(self, user_base64_vector, input_image_base64):
        result = self.compare_faces(user_base64_vector, self.extract_face_encoding(input_image_base64))
        return {'verified': bool(result['match']), 'distance': result['distance'],
                'confidence': result['confidence']}

    def process_user_profile_image(self, image_base64):
        """Valida la foto y devuelve el vector facial para guardarlo."""
        try:
            encoding = self.extract_face_encoding(image_base64)
            return {
                'base64imageprofile': image_base64,
                'base64vector': self.encoding_to_base64(encoding),
                'success': True,
                'message': 'Imagen de perfil procesada correctamente',
            }
        except FaceError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            return {'success': False, 'message': f'Error procesando la imagen: {e}'}
