import { API_CONFIG, getAuthHeaders, getApiKeyHeaders, handleApiResponse } from './api';
import type { ApiResponse, FaceComparison } from './api';

export class FaceService {
  
  // Comparar dos rostros (usando API key)
  static async compareFaces(
    face1: string,
    face2: string,
    apiKey: string,
    appId: string
  ): Promise<ApiResponse<{ comparison: FaceComparison; app_id: number }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FACE_COMPARE}`, {
      method: 'POST',
      headers: getApiKeyHeaders(apiKey, appId),
      body: JSON.stringify({ face1, face2 })
    });
    
    return handleApiResponse(response);
  }

  // Verificar usuario por rostro (usando API key)
  static async verifyUserFace(
    userEmail: string,
    faceImage: string,
    apiKey: string,
    appId: string
  ): Promise<ApiResponse<{ verification: FaceComparison; user_id: number; app_id: number }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FACE_VERIFY_USER}`, {
      method: 'POST',
      headers: getApiKeyHeaders(apiKey, appId),
      body: JSON.stringify({ user_email: userEmail, face_image: faceImage })
    });
    
    return handleApiResponse(response);
  }

  // Extraer encoding facial (usando API key)
  static async extractFaceEncoding(
    faceImage: string,
    apiKey: string,
    appId: string
  ): Promise<ApiResponse<{ encoding: string; app_id: number }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FACE_EXTRACT_ENCODING}`, {
      method: 'POST',
      headers: getApiKeyHeaders(apiKey, appId),
      body: JSON.stringify({ face_image: faceImage })
    });
    
    return handleApiResponse(response);
  }

  // Procesar imagen de perfil (usando JWT)
  static async processProfileImage(base64Image: string): Promise<ApiResponse> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FACE_PROCESS_PROFILE}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ base64imageprofile: base64Image })
    });
    
    return handleApiResponse(response);
  }

  // Comparar con usuario actual (usando JWT)
  static async compareWithCurrentUser(faceImage: string): Promise<ApiResponse<{ verification: FaceComparison }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}/api/face/compare-with-user`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ face_image: faceImage })
    });
    
    return handleApiResponse(response);
  }

  // Obtener tolerancia actual
  static async getTolerance(): Promise<ApiResponse<{ tolerance: number }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FACE_TOLERANCE}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Configurar tolerancia
  static async setTolerance(tolerance: number): Promise<ApiResponse<{ tolerance: number }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.FACE_TOLERANCE}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ tolerance })
    });
    
    return handleApiResponse(response);
  }
}

// Utilidades para manejo de imágenes
export class ImageUtils {
  
  // Convertir File a base64
  static fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        resolve(result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  // Convertir canvas a base64
  static canvasToBase64(canvas: HTMLCanvasElement, quality = 0.8): string {
    return canvas.toDataURL('image/jpeg', quality);
  }

  // Redimensionar imagen manteniendo proporción
  static resizeImage(
    file: File,
    maxWidth = 800,
    maxHeight = 600,
    quality = 0.8
  ): Promise<string> {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      const img = new Image();

      img.onload = () => {
        // Calcular nuevas dimensiones
        let { width, height } = img;
        
        if (width > height) {
          if (width > maxWidth) {
            height = (height * maxWidth) / width;
            width = maxWidth;
          }
        } else {
          if (height > maxHeight) {
            width = (width * maxHeight) / height;
            height = maxHeight;
          }
        }

        // Redimensionar
        canvas.width = width;
        canvas.height = height;
        ctx.drawImage(img, 0, 0, width, height);

        // Convertir a base64
        const base64 = canvas.toDataURL('image/jpeg', quality);
        resolve(base64);
      };

      // Cargar imagen
      const reader = new FileReader();
      reader.onload = (e) => {
        img.src = e.target?.result as string;
      };
      reader.readAsDataURL(file);
    });
  }

  // Capturar imagen desde webcam
  static async captureFromCamera(): Promise<string> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        } 
      });

      return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d')!;

        video.srcObject = stream;
        video.play();

        video.onloadedmetadata = () => {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          
          // Esperar un momento para que la cámara se estabilice
          setTimeout(() => {
            ctx.drawImage(video, 0, 0);
            const base64 = canvas.toDataURL('image/jpeg', 0.8);
            
            // Detener stream
            stream.getTracks().forEach(track => track.stop());
            
            resolve(base64);
          }, 1000);
        };

        video.onerror = () => {
          stream.getTracks().forEach(track => track.stop());
          reject(new Error('Error accessing camera'));
        };
      });
    } catch (error) {
      throw new Error('Camera not available: ' + error);
    }
  }

  // Validar que la imagen contiene un rostro (básico)
  static async validateFaceImage(base64Image: string): Promise<boolean> {
    // Aquí podrías implementar validación básica del lado cliente
    // Por ahora, solo verificamos que sea una imagen válida
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.src = base64Image;
    });
  }
}
