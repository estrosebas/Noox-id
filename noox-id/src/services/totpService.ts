import { API_CONFIG, getAuthHeaders, handleApiResponse } from './api';

export interface TotpStatus {
  success: boolean;
  enabled: boolean;
  pending: boolean;
}

export interface TotpSetup {
  success: boolean;
  secret: string;
  otpauth_uri: string;
  /** Código QR como data URL (SVG), listo para un <img>. */
  qr: string;
  message?: string;
}

export class TotpService {
  static async getStatus(): Promise<TotpStatus> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOTP_STATUS}`, {
      headers: getAuthHeaders()
    });
    return (await handleApiResponse(response)) as unknown as TotpStatus;
  }

  // Genera un secreto nuevo (aún sin activar) y devuelve el QR para escanearlo
  static async setup(): Promise<TotpSetup> {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOTP_SETUP}`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    return (await handleApiResponse(response)) as unknown as TotpSetup;
  }

  // Activa el autenticador confirmando un código generado por la app
  static async enable(code: string) {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOTP_ENABLE}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ code })
    });
    return handleApiResponse(response);
  }

  // Desactiva el autenticador (exige un código vigente)
  static async disable(code: string) {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOTP_DISABLE}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ code })
    });
    return handleApiResponse(response);
  }
}
