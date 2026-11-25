import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { AuthService } from '../services/authService';
import { UserService } from '../services/userService';
import type { User } from '../services/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  loginWithGoogle: (idToken: string) => Promise<boolean>;
  loginWithFace: (email: string, faceImage: string) => Promise<boolean>;
  requestEmailOtp: (email: string) => Promise<boolean>;
  loginWithEmailOtp: (email: string, code: string) => Promise<boolean>;
  register: (userData: {
    firstname: string;
    lastname: string;
    email: string;
    password: string;
    base64imageprofile?: string;
  }) => Promise<boolean>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Verificar si hay un token guardado al cargar la app
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('noox_token');
      console.log('🔐 Checking auth on app load...');
      console.log('🔑 Token exists:', !!token);
      
      if (token) {
        try {
          console.log('📡 Verifying token with backend...');
          const isValid = await AuthService.verifyToken();
          console.log('✅ Token verification result:', isValid);
          
          if (isValid.success) {
            // Token válido, obtener perfil del usuario
            console.log('👤 Token valid, loading user profile...');
            await refreshProfile();
          } else {
            // Token inválido, limpiar storage
            console.log('❌ Token invalid, clearing storage...');
            localStorage.removeItem('noox_token');
          }
        } catch (error) {
          console.error('💥 Error checking auth:', error);
          console.log('🧹 Clearing token due to error...');
          localStorage.removeItem('noox_token');
        }
      } else {
        console.log('ℹ️ No token found, user not authenticated');
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await AuthService.login({ email, password });
      console.log('Login service response:', response);
      if (response.success && response.token && response.user) {
        localStorage.setItem('noox_token', String(response.token));
        setUser(response.user);
        console.log('User set in context:', response.user);
        setIsLoading(false);
        return true;
      } else {
        setError(response.message || 'Error en el login');
        setIsLoading(false);
        return false;
      }
    } catch (error: any) {
      setError(error.message || 'Error de conexión');
      setIsLoading(false);
      return false;
    }
  };

  const loginWithGoogle = async (idToken: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await AuthService.googleAuth(idToken);
      if (response.success && response.token && response.user) {
        localStorage.setItem('noox_token', String(response.token));
        setUser(response.user);
        setIsLoading(false);
        return true;
      } else {
        setError(response.message || 'Error en el login con Google');
        setIsLoading(false);
        return false;
      }
    } catch (error: any) {
      setError(error.message || 'Error de conexión');
      setIsLoading(false);
      return false;
    }
  };

  const loginWithFace = async (email: string, faceImage: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await AuthService.faceLogin({ email, face_image: faceImage });
      if (response.success && response.token && response.user) {
        localStorage.setItem('noox_token', String(response.token));
        setUser(response.user);
        setIsLoading(false);
        return true;
      } else {
        setError(response.message || 'No se pudo autenticar con reconocimiento facial');
        setIsLoading(false);
        return false;
      }
    } catch (error: any) {
      setError(error.message || 'Error de conexión');
      setIsLoading(false);
      return false;
    }
  };

  const requestEmailOtp = async (email: string): Promise<boolean> => {
    setError(null);
    try {
      const response = await AuthService.requestEmailOtp(email);
      return !!response.success;
    } catch (error: any) {
      setError(error.message || 'No se pudo enviar el código');
      return false;
    }
  };

  const loginWithEmailOtp = async (email: string, code: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await AuthService.emailOtpLogin(email, code);
      if (response.success && response.token && response.user) {
        localStorage.setItem('noox_token', String(response.token));
        setUser(response.user);
        setIsLoading(false);
        return true;
      } else {
        setError(response.message || 'Código incorrecto o vencido');
        setIsLoading(false);
        return false;
      }
    } catch (error: any) {
      setError(error.message || 'Error de conexión');
      setIsLoading(false);
      return false;
    }
  };

  const register = async (userData: {
    firstname: string;
    lastname: string;
    email: string;
    password: string;
    base64imageprofile?: string;
  }): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await AuthService.register(userData);
      if (response.success) {
        // Registro exitoso, ahora hacer login automáticamente
        const loginResponse = await AuthService.login({ 
          email: userData.email, 
          password: userData.password 
        });
        
        if (loginResponse.success && loginResponse.token && loginResponse.user) {
          localStorage.setItem('noox_token', String(loginResponse.token));
          setUser(loginResponse.user);
          setIsLoading(false);
          return true;
        } else {
          setError('Usuario registrado pero error en login automático');
          setIsLoading(false);
          return false;
        }
      } else {
        setError(response.message || 'Error en el registro');
        setIsLoading(false);
        return false;
      }
    } catch (error: any) {
      setError(error.message || 'Error de conexión');
      setIsLoading(false);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('noox_token');
    setUser(null);
    setError(null);
  };

  const refreshProfile = async () => {
    try {
      const response = await UserService.getCurrentProfile();
      if (response.success && response.data) {
        setUser(response.data);
      }
    } catch (error) {
      console.error('Error refreshing profile:', error);
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    loginWithGoogle,
    loginWithFace,
    requestEmailOtp,
    loginWithEmailOtp,
    register,
    logout,
    refreshProfile,
    error
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
