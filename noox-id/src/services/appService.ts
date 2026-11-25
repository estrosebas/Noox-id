import { API_CONFIG, getAuthHeaders, handleApiResponse } from './api';
import type { ApiResponse, App } from './api';

export class AppService {
  
  // Crear nueva aplicación
  static async createApp(appData: {
    name_app: string;
    IconAppPath?: string;
    requires_totp?: boolean;
  }): Promise<ApiResponse<App>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APPS}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(appData)
    });
    
    return handleApiResponse(response);
  }

  // Obtener aplicaciones del usuario actual
  static async getUserApps(page = 1, perPage = 10): Promise<ApiResponse<{ apps: App[]; total: number; pages: number }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APPS}?page=${page}&per_page=${perPage}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Obtener aplicación por ID
  static async getAppById(id: number): Promise<ApiResponse<App>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APPS}/${id}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Actualizar aplicación
  static async updateApp(id: number, appData: {
    name_app?: string;
    is_verified?: boolean;
    IconAppPath?: string;
    requires_totp?: boolean;
  }): Promise<ApiResponse<App>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APPS}/${id}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(appData)
    });
    
    return handleApiResponse(response);
  }

  // Eliminar aplicación
  static async deleteApp(id: number): Promise<ApiResponse> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APPS}/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Regenerar API key
  static async regenerateApiKey(id: number): Promise<ApiResponse<App>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APP_REGENERATE_KEY(id.toString())}`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Agregar usuario a aplicación
  static async addUserToApp(appId: number, userData: {
    id_usuario: number;
    status?: 'enable' | 'disable';
    TokenToAcces?: number;
  }): Promise<ApiResponse> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APP_USERS(appId.toString())}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(userData)
    });
    
    return handleApiResponse(response);
  }

  // Obtener usuarios de una aplicación
  static async getAppUsers(appId: number, page = 1, perPage = 10): Promise<ApiResponse<{ app_users: any[]; total: number; pages: number }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APP_USERS(appId.toString())}?page=${page}&per_page=${perPage}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Actualizar estado de usuario en aplicación
  static async updateUserAppStatus(appId: number, userId: number, status: 'enable' | 'disable'): Promise<ApiResponse> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APP_USERS(appId.toString())}/${userId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ status })
    });
    
    return handleApiResponse(response);
  }

  // Remover usuario de aplicación
  static async removeUserFromApp(appId: number, userId: number): Promise<ApiResponse> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.APP_USERS(appId.toString())}/${userId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }
}
