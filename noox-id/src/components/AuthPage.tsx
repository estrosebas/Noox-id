import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Eye, EyeOff, X } from 'lucide-react';
import FaceCamera from './FaceCamera';
import EmailOtpLogin from './EmailOtpLogin';
import VerifyEmailStep from './VerifyEmailStep';
import GoogleSignInButton from './GoogleSignInButton';
import { useAuth } from '../contexts/AuthContext';

interface AuthPageProps {
  onBack: () => void;
}

const AuthPage: React.FC<AuthPageProps> = ({ onBack }) => {
  const [mode, setMode] = useState<'login' | 'register' | 'face' | 'otp'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [showFaceCapture, setShowFaceCapture] = useState(false);
  const [faceError, setFaceError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    firstname: '',
    lastname: '',
    confirmPassword: ''
  });


  const { login, register, loginWithGoogle, loginWithFace, isLoading, error, pendingVerification } = useAuth();


  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'login') {
      const success = await login(formData.email, formData.password);
      console.log('Login result:', success);
    } else if (mode === 'register') {
      if (formData.password !== formData.confirmPassword) {
        return; // Handle password mismatch
      }
      const success = await register({
        firstname: formData.firstname,
        lastname: formData.lastname,
        email: formData.email,
        password: formData.password
      });
      console.log('Register result:', success);
    }
  };

  const handleFaceLogin = () => {
    if (!formData.email) {
      alert('Por favor ingresa tu email primero');
      return;
    }
    setFaceError(null);
    setShowFaceCapture(true);
  };

  // FaceCamera entrega la foto ya validada en el navegador (MediaPipe);
  // el backend (YuNet + SFace) hace la verificación definitiva.
  const handleFaceCaptured = async (photo: string) => {
    setFaceError(null);
    const success = await loginWithFace(formData.email, photo);
    if (success) setShowFaceCapture(false);
    else setFaceError('No pudimos verificar tu rostro. Toma otra foto e inténtalo de nuevo.');
  };

  const closeFaceCapture = () => {
    setShowFaceCapture(false);
    setFaceError(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Cuenta recién registrada (o sin verificar): primero se verifica el correo con el código
  if (pendingVerification) return <VerifyEmailStep />;

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
          {mode === 'login' ? 'Iniciar Sesión' : mode === 'register' ? 'Registrarse' : mode === 'otp' ? 'Código por correo' : 'Login Facial'}
        </h2>
        <p className="auth-subtitle">
          {mode === 'login' ? 'Ingresa a tu cuenta' : mode === 'register' ? 'Crea tu nueva cuenta' : mode === 'otp' ? 'Entra sin contraseña con un código' : 'Usa tu rostro para ingresar'}
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
            <button
              onClick={() => setMode('otp')}
              className={`btn ${mode === 'otp' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ flex: 1 }}
            >
              Código
            </button>
          </div>
        </div>

        {mode !== 'face' && mode !== 'otp' && (
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

        {mode === 'otp' && <EmailOtpLogin />}

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

      {/* Modal de Captura Facial */}
      {showFaceCapture && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            style={{
              backgroundColor: '#1f2937',
              borderRadius: '16px',
              padding: '24px',
              width: '90%',
              maxWidth: '500px',
              maxHeight: '90vh',
              overflow: 'auto',
              position: 'relative'
            }}
          >
            <button
              onClick={closeFaceCapture}
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'none',
                border: 'none',
                color: '#9ca3af',
                cursor: 'pointer',
                padding: '4px'
              }}
            >
              <X size={24} />
            </button>

            <h3 style={{ color: '#ffffff', marginBottom: '20px', textAlign: 'center' }}>
              Reconocimiento Facial
            </h3>
            <p style={{ color: '#d1d5db', marginBottom: '20px', textAlign: 'center', fontSize: '14px' }}>
              Coloca tu rostro dentro del óvalo y mantente quieto: la foto se toma sola
            </p>

            <FaceCamera onCapture={handleFaceCaptured} busy={isLoading} busyLabel="Verificando rostro…" />
            {(faceError || error) && (
              <p style={{ color: '#fca5a5', fontSize: '13px', textAlign: 'center', marginBottom: '12px' }}>
                {error || faceError}
              </p>
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={closeFaceCapture}
                style={{
                  padding: '12px 24px',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                Cancelar
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
};

export default AuthPage;
