import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import GoogleSignInButton from './GoogleSignInButton';

interface AuthPageProps {
  onBack: () => void;
}

const AuthPage: React.FC<AuthPageProps> = ({ onBack }) => {
  const [mode, setMode] = useState<'login' | 'register' | 'face'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    firstname: '',
    lastname: '',
    confirmPassword: ''
  });

  const { login, register, loginWithGoogle, loginWithFace, isLoading, error } = useAuth();

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'login') {
      await login(formData.email, formData.password);
    } else if (mode === 'register') {
      if (formData.password !== formData.confirmPassword) {
        return; // Handle password mismatch
      }
      await register({
        firstname: formData.firstname,
        lastname: formData.lastname,
        email: formData.email,
        password: formData.password
      });
    }
  };

  const handleFaceLogin = async () => {
    // This would typically capture from camera
    // For demo purposes, we'll use a placeholder
    if (formData.email) {
      await loginWithFace(formData.email, 'mock_face_data');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="auth-container">
      <motion.div
        className="auth-card"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <button 
          onClick={onBack}
          className="btn btn-secondary"
          style={{ position: 'absolute', top: '20px', left: '20px' }}
        >
          <ArrowLeft size={20} />
        </button>
        
        <motion.div
          className="sidebar-logo"
          style={{ margin: '0 auto 20px' }}
          initial={{ rotate: 0 }}
          animate={{ rotate: 360 }}
          transition={{ duration: 1, delay: 0.2 }}
        >
          N
        </motion.div>
        
        <h2 className="auth-title">
          {mode === 'login' ? 'Iniciar Sesión' : mode === 'register' ? 'Registrarse' : 'Login Facial'}
        </h2>
        <p className="auth-subtitle">
          {mode === 'login' ? 'Ingresa a tu cuenta' : mode === 'register' ? 'Crea tu nueva cuenta' : 'Usa tu rostro para ingresar'}
        </p>

        {error && (
          <motion.div
            className="error-message"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: '10px',
              marginBottom: '20px',
              backgroundColor: '#fee2e2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              color: '#dc2626',
              fontSize: '14px'
            }}
          >
            {error}
          </motion.div>
        )}

        <div style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <button
              onClick={() => setMode('login')}
              className={`btn ${mode === 'login' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ flex: 1 }}
            >
              Login
            </button>
            <button
              onClick={() => setMode('register')}
              className={`btn ${mode === 'register' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ flex: 1 }}
            >
              Registro
            </button>
            <button
              onClick={() => setMode('face')}
              className={`btn ${mode === 'face' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ flex: 1 }}
            >
              Facial
            </button>
          </div>
        </div>

        {mode !== 'face' && (
          <form onSubmit={handleEmailLogin} style={{ width: '100%' }}>
            {mode === 'register' && (
              <>
                <input
                  type="text"
                  name="firstname"
                  placeholder="Nombre"
                  value={formData.firstname}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '12px',
                    marginBottom: '15px',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    fontSize: '16px'
                  }}
                  required
                />
                <input
                  type="text"
                  name="lastname"
                  placeholder="Apellido"
                  value={formData.lastname}
                  onChange={handleInputChange}
                  style={{
                    width: '100%',
                    padding: '12px',
                    marginBottom: '15px',
                    border: '1px solid #d1d5db',
                    borderRadius: '8px',
                    fontSize: '16px'
                  }}
                  required
                />
              </>
            )}
            
            <input
              type="email"
              name="email"
              placeholder="Correo electrónico"
              value={formData.email}
              onChange={handleInputChange}
              style={{
                width: '100%',
                padding: '12px',
                marginBottom: '15px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                fontSize: '16px'
              }}
              required
            />
            
            <div style={{ position: 'relative', marginBottom: '15px' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                placeholder="Contraseña"
                value={formData.password}
                onChange={handleInputChange}
                style={{
                  width: '100%',
                  padding: '12px',
                  paddingRight: '45px',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  fontSize: '16px'
                }}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#6b7280'
                }}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            
            {mode === 'register' && (
              <input
                type={showPassword ? 'text' : 'password'}
                name="confirmPassword"
                placeholder="Confirmar contraseña"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                style={{
                  width: '100%',
                  padding: '12px',
                  marginBottom: '15px',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  fontSize: '16px'
                }}
                required
              />
            )}
            
            <motion.button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary"
              style={{ width: '100%', marginBottom: '15px' }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {isLoading ? 'Procesando...' : mode === 'login' ? 'Iniciar Sesión' : 'Registrarse'}
            </motion.button>
          </form>
        )}

        {mode === 'face' && (
          <div style={{ width: '100%' }}>
            <input
              type="email"
              name="email"
              placeholder="Correo electrónico (para identificarte)"
              value={formData.email}
              onChange={handleInputChange}
              style={{
                width: '100%',
                padding: '12px',
                marginBottom: '15px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                fontSize: '16px'
              }}
              required
            />
            <motion.button
              onClick={handleFaceLogin}
              disabled={isLoading || !formData.email}
              className="btn btn-primary"
              style={{ width: '100%', marginBottom: '15px' }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {isLoading ? 'Analizando...' : '📷 Usar Reconocimiento Facial'}
            </motion.button>
          </div>
        )}
        
        <div style={{ margin: '20px 0', textAlign: 'center', color: '#6b7280' }}>
          o
        </div>
        
        <GoogleSignInButton onCredential={loginWithGoogle} />
      </motion.div>
    </div>
  );
};

export default AuthPage;
