import { API_CONFIG, getAuthHeaders, handleApiResponse } from './api';
import type { ApiResponse, Token } from './api';

export class TokenService {
  
  // Crear token de acceso
  static async createToken(tokenData: {
    profilePick?: boolean;
    email?: boolean;
    days_to_expire?: number;
  }): Promise<ApiResponse<Token>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOKENS}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(tokenData)
    });
    
    return handleApiResponse(response);
  }

  // Obtener tokens del usuario actual
  static async getUserTokens(page = 1, perPage = 10): Promise<ApiResponse<{ tokens: Token[]; total: number; pages: number }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOKENS}?page=${page}&per_page=${perPage}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Obtener token por ID
  static async getTokenById(id: number): Promise<ApiResponse<Token>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOKENS}/${id}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Actualizar token
  static async updateToken(id: number, tokenData: {
    profilePick?: boolean;
    email?: boolean;
    expires_at?: string;
  }): Promise<ApiResponse<Token>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOKENS}/${id}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(tokenData)
    });
    
    return handleApiResponse(response);
  }

  // Eliminar token
  static async deleteToken(id: number): Promise<ApiResponse> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOKENS}/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }

  // Validar token
  static async validateToken(id: number): Promise<ApiResponse<{ valid: boolean; token: Token }>> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOKEN_VALIDATE(id.toString())}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    return handleApiResponse(response);
  }
}
