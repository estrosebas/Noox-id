import face_recognition
import cv2
import numpy as np
import base64
from PIL import Image
from io import BytesIO

class FaceRecognitionService:
    def __init__(self, tolerance=0.6):
        self.tolerance = tolerance
    
    def image_to_base64(self, image_path):
        """Convierte una imagen a base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error convirtiendo imagen a base64: {str(e)}")
    
    def base64_to_image(self, base64_string):
        """Convierte base64 a imagen numpy"""
        try:
            print(f"🖼️ Convirtiendo base64 a imagen...")
            print(f"📏 Longitud original: {len(base64_string)}")
            
            # Limpiar el string base64 si tiene prefijo de data URL
            if base64_string.startswith('data:image'):
                print(f"🏷️ Detectado prefijo data URL, limpiando...")
                # Encontrar la coma que separa el header del data
                comma_index = base64_string.find(',')
                if comma_index != -1:
                    base64_string = base64_string[comma_index + 1:]
                    print(f"✂️ Longitud después de limpiar: {len(base64_string)}")
                else:
                    print(f"⚠️ No se encontró coma en data URL")
            
            # Decodificar base64
            image_data = base64.b64decode(base64_string)
            print(f"📦 Datos decodificados: {len(image_data)} bytes")
            
            image = Image.open(BytesIO(image_data))
            print(f"🖼️ Imagen abierta: {image.size}, modo: {image.mode}")
            
            # Convertir a RGB si es necesario (algunos formatos pueden ser RGBA)
            if image.mode != 'RGB':
                print(f"🎨 Convirtiendo de {image.mode} a RGB")
                image = image.convert('RGB')
                
            numpy_image = np.array(image)
            print(f"🔢 Imagen convertida a numpy: {numpy_image.shape}")
            
            return numpy_image
        except Exception as e:
            print(f"❌ Error en base64_to_image: {str(e)}")
            raise Exception(f"Error convirtiendo base64 a imagen: {str(e)}")
    
    def extract_face_encoding(self, image_data):
        """Extrae el encoding facial de una imagen"""
        try:
            # Si es base64, convertir a numpy array
            if isinstance(image_data, str):
                image = self.base64_to_image(image_data)
            else:
                image = image_data
            
            # Detectar rostros y extraer encodings
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                raise Exception("No se detectó ningún rostro en la imagen")
            
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if len(face_encodings) == 0:
                raise Exception("No se pudo extraer el encoding facial")
            
            # Retornar el primer encoding encontrado
            return face_encodings[0].tolist()  # Convertir a lista para serialización
            
        except Exception as e:
            raise Exception(f"Error extrayendo encoding facial: {str(e)}")
    
    def encoding_to_base64(self, encoding):
        """Convierte un encoding facial a base64 para almacenamiento"""
        try:
            encoding_array = np.array(encoding)
            encoding_bytes = encoding_array.tobytes()
            return base64.b64encode(encoding_bytes).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error convirtiendo encoding a base64: {str(e)}")
    
    def base64_to_encoding(self, base64_encoding):
        """Convierte base64 a encoding facial"""
        try:
            encoding_bytes = base64.b64decode(base64_encoding)
            encoding_array = np.frombuffer(encoding_bytes, dtype=np.float64)
            return encoding_array
        except Exception as e:
            raise Exception(f"Error convirtiendo base64 a encoding: {str(e)}")
    
    def compare_faces(self, known_encoding, unknown_encoding):
        """Compara dos encodings faciales"""
        try:
            # Convertir si son base64
            if isinstance(known_encoding, str):
                known_encoding = self.base64_to_encoding(known_encoding)
            if isinstance(unknown_encoding, str):
                unknown_encoding = self.base64_to_encoding(unknown_encoding)
            
            # Asegurar que son arrays numpy
            known_encoding = np.array(known_encoding)
            unknown_encoding = np.array(unknown_encoding)
            
            # Comparar rostros
            matches = face_recognition.compare_faces([known_encoding], unknown_encoding, tolerance=self.tolerance)
            distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
            
            return {
                'match': matches[0],
                'distance': float(distance),
                'confidence': max(0, 1 - distance)  # Convertir distancia a confianza
            }
            
        except Exception as e:
            raise Exception(f"Error comparando rostros: {str(e)}")
    
    def verify_user_face(self, user_base64_vector, input_image_base64):
        """Verifica si el rostro de entrada coincide con el del usuario"""
        try:
            # Extraer encoding de la imagen de entrada
            input_encoding = self.extract_face_encoding(input_image_base64)
            
            # Comparar con el vector almacenado del usuario
            comparison_result = self.compare_faces(user_base64_vector, input_encoding)
            
            return {
                'verified': comparison_result['match'],
                'distance': comparison_result['distance'],
                'confidence': comparison_result['confidence']
            }
            
        except Exception as e:
            raise Exception(f"Error verificando rostro de usuario: {str(e)}")
    
    def process_user_profile_image(self, image_base64):
        """Procesa la imagen de perfil del usuario y extrae el vector facial"""
        try:
            print(f"🔍 Procesando imagen de perfil...")
            print(f"📏 Longitud de imagen base64: {len(image_base64)}")
            
            # Verificar si tiene prefijo de data URL
            has_prefix = image_base64.startswith('data:image')
            print(f"🏷️ Tiene prefijo data URL: {has_prefix}")
            
            # Extraer encoding facial
            face_encoding = self.extract_face_encoding(image_base64)
            print(f"✅ Encoding facial extraído exitosamente")
            print(f"📊 Dimensiones del encoding: {len(face_encoding)}")
            
            # Convertir encoding a base64 para almacenamiento
            encoding_base64 = self.encoding_to_base64(face_encoding)
            print(f"💾 Encoding convertido a base64 para almacenamiento")
            
            return {
                'base64imageprofile': image_base64,
                'base64vector': encoding_base64,
                'success': True,
                'message': 'Imagen de perfil procesada correctamente'
            }
            
        except Exception as e:
            print(f"❌ Error procesando imagen: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
