import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Eye, EyeOff, Camera, X, RefreshCw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import EmailOtpLogin from './EmailOtpLogin';
import VerifyEmailStep from './VerifyEmailStep';
import GoogleSignInButton from './GoogleSignInButton';

interface AuthPageProps {
  onBack: () => void;
}

const AuthPage: React.FC<AuthPageProps> = ({ onBack }) => {
  const [mode, setMode] = useState<'login' | 'register' | 'face' | 'otp'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [showFaceCapture, setShowFaceCapture] = useState(false);
  const [cameraState, setCameraState] = useState<'off' | 'starting' | 'ready' | 'error'>('off');
  const [, setCapturedImage] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    firstname: '',
    lastname: '',
    confirmPassword: ''
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const { login, register, loginWithGoogle, loginWithFace, isLoading, error, pendingVerification } = useAuth();

  // Limpiar cámara al desmontar el componente
  useEffect(() => {
    return () => {
      console.log('🧹 Limpiando cámara al desmontar componente');
      stopCamera();
    };
  }, []);

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

  const handleFaceLogin = async () => {
    if (!formData.email) {
      alert('Por favor ingresa tu email primero');
      return;
    }
    
    console.log('🎥 Iniciando captura facial...');
    // Mostrar el modal de captura facial
    setShowFaceCapture(true);
    // Iniciar cámara inmediatamente después de abrir el modal
    setTimeout(async () => {
      await startCamera();
    }, 200);
  };

  // Remover el useEffect problemático que estaba causando el conflicto

  const startCamera = async () => {
    try {
      console.log('📹 Iniciando cámara...');
      console.log('📺 Elemento video disponible:', !!videoRef.current);
      setCameraState('starting');
      setCameraError(null);
      
      // Verificar si el navegador soporta getUserMedia
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Tu navegador no soporta acceso a la cámara');
      }
      
      console.log('🔍 Solicitando acceso a la cámara...');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        } 
      });
      
      console.log('✅ Stream de cámara obtenido:', stream);
      console.log('📺 Tracks activos:', stream.getVideoTracks().length);
      
      // Como el elemento video siempre existe, no necesitamos verificar si existe
      console.log('📺 Asignando stream al elemento video...');
      videoRef.current!.srcObject = stream;
      
      // Función que se ejecuta cuando el video está listo
      const handleVideoReady = () => {
        console.log('🎬 Video ready! Cambiando estado a ready');
        console.log('📏 Dimensiones del video:', videoRef.current?.videoWidth, 'x', videoRef.current?.videoHeight);
        setCameraState('ready');
      };
      
      // Múltiples eventos para detectar cuando está listo
      videoRef.current!.addEventListener('loadedmetadata', handleVideoReady);
      videoRef.current!.addEventListener('canplay', handleVideoReady);
      videoRef.current!.addEventListener('playing', handleVideoReady);
      
      // Error handler
      videoRef.current!.addEventListener('error', (e) => {
        console.error('❌ Error en el elemento video:', e);
        setCameraError('Error al cargar el video');
        setCameraState('error');
      });
      
      try {
        console.log('▶️ Intentando reproducir video...');
        const playPromise = videoRef.current!.play();
        if (playPromise !== undefined) {
          await playPromise;
          console.log('✅ Video en reproducción');
        }
        
        // Fallback más agresivo con verificaciones
        setTimeout(() => {
          if (videoRef.current) {
            console.log('⏰ Verificando estado después de 500ms...');
            console.log('📏 Dimensiones actuales:', videoRef.current.videoWidth, 'x', videoRef.current.videoHeight);
            console.log('🎮 Estado actual:', cameraState);
            console.log('📺 ReadyState:', videoRef.current.readyState);
            
            if (videoRef.current.readyState >= 3) { // HAVE_FUTURE_DATA
              console.log('🔄 Forzando estado ready por readyState');
              setCameraState('ready');
            } else if (videoRef.current.videoWidth > 0 && videoRef.current.videoHeight > 0) {
              console.log('🔄 Forzando estado ready por dimensiones');
              setCameraState('ready');
            }
          }
        }, 500);
        
        // Segundo fallback aún más tarde
        setTimeout(() => {
          if (videoRef.current && cameraState === 'starting') {
            console.log('🔄 Segundo fallback - forzando ready sin condiciones');
            setCameraState('ready');
          }
        }, 2000);
        
      } catch (playError) {
        console.error('❌ Error al reproducir video:', playError);
        // Intentar reproducir de nuevo tras un breve delay
        setTimeout(async () => {
          if (videoRef.current) {
            console.log('🔁 Reintentando reproducción...');
            try {
              await videoRef.current.play();
              console.log('✅ Reproducción exitosa en segundo intento');
            } catch (retryError) {
              console.error('❌ Error en segundo intento:', retryError);
            }
          }
        }, 500);
      }
    } catch (error) {
      console.error('💥 Error general en startCamera:', error);
      setCameraState('error');
      setCameraError(
        error instanceof Error 
          ? `Error al acceder a la cámara: ${error.message}` 
          : 'No se pudo acceder a la cámara. Verifica los permisos.'
      );
    }
  };

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current || cameraState !== 'ready') return;

    try {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      const context = canvas.getContext('2d');

      if (!context) {
        throw new Error('No se pudo obtener el contexto del canvas');
      }

      // Configurar canvas con las dimensiones del video
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      
      // Dibujar el frame actual del video
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Convertir a base64
      const base64String = canvas.toDataURL('image/jpeg', 0.8);
      setCapturedImage(base64String);

      // Detener la cámara
      stopCamera();

      // Proceder con el login facial
      if (formData.email) {
        const success = await loginWithFace(formData.email, base64String);
        console.log('Face login result:', success);
        
        if (success) {
          // Cerrar modal en caso de éxito
          setShowFaceCapture(false);
          setCapturedImage(null);
        }
      }
    } catch (error) {
      console.error('Error capturing photo:', error);
      setCameraError('Error al capturar la imagen');
    }
  };

  const stopCamera = () => {
    console.log('🛑 Deteniendo cámara...');
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      console.log('📹 Deteniendo tracks de video:', stream.getTracks().length);
      stream.getTracks().forEach(track => {
        console.log('⏹️ Deteniendo track:', track.kind);
        track.stop();
      });
      videoRef.current.srcObject = null;
      
      // Limpiar event listeners usando removeEventListener
      videoRef.current.removeEventListener('loadedmetadata', () => {});
      videoRef.current.removeEventListener('canplay', () => {});
      videoRef.current.removeEventListener('playing', () => {});
      videoRef.current.removeEventListener('error', () => {});
    }
    setCameraState('off');
    setCameraError(null);
    console.log('✅ Cámara detenida');
  };

  const closeFaceCapture = () => {
    stopCamera();
    setShowFaceCapture(false);
    setCapturedImage(null);
    setCameraError(null);
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
              Posiciona tu rostro en el centro de la cámara y haz clic en "Capturar"
            </p>
            
            {/* Debug info */}
            <div style={{ marginBottom: '10px', textAlign: 'center', fontSize: '12px', color: '#9ca3af' }}>
              Estado: {cameraState} | Email: {formData.email}
              <br />
              Video ref: {videoRef.current ? 'OK' : 'NULL'} | 
              Stream: {videoRef.current?.srcObject ? 'OK' : 'NULL'}
              <br />
              Dimensiones: {videoRef.current?.videoWidth || 0}x{videoRef.current?.videoHeight || 0}
            </div>

            <div style={{ 
              width: '100%', 
              height: '300px', 
              backgroundColor: '#374151', 
              borderRadius: '12px',
              border: '2px dashed #4b5563',
              marginBottom: '20px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              {/* Video siempre presente en el DOM */}
              <video
                ref={videoRef}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  backgroundColor: '#000',
                  visibility: cameraState === 'ready' ? 'visible' : 'hidden'
                }}
                autoPlay
                muted
                playsInline
              />
              <canvas ref={canvasRef} style={{ display: 'none' }} />

              {/* Botón de capturar siempre presente pero solo visible cuando ready */}
              {cameraState === 'ready' && (
                <motion.button
                  onClick={capturePhoto}
                  disabled={isLoading}
                  style={{ 
                    position: 'absolute', 
                    bottom: '16px', 
                    left: '50%', 
                    transform: 'translateX(-50%)',
                    padding: '12px 24px',
                    backgroundColor: '#4285f4',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '16px',
                    fontWeight: '600',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    zIndex: 10
                  }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Camera size={20} />
                  {isLoading ? 'Analizando...' : 'Capturar Foto'}
                </motion.button>
              )}

              {/* Overlay para estado "starting" */}
              {cameraState === 'starting' && (
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  backgroundColor: '#374151',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 5
                }}>
                  <div style={{ textAlign: 'center', color: '#9ca3af' }}>
                    <motion.div
                      style={{ 
                        width: '48px', 
                        height: '48px', 
                        border: '4px solid #374151', 
                        borderTop: '4px solid #4285f4', 
                        borderRadius: '50%',
                        margin: '0 auto 16px'
                      }}
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                    <p>Iniciando cámara...</p>
                  </div>
                </div>
              )}

              {/* Overlay para estado "error" */}
              {cameraState === 'error' && (
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  backgroundColor: '#374151',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 5
                }}>
                  <div style={{ textAlign: 'center', color: '#ef4444' }}>
                    <X size={48} style={{ marginBottom: '16px' }} />
                    <p>Error al acceder a la cámara</p>
                    {cameraError && (
                      <p style={{ fontSize: '12px', marginTop: '8px' }}>{cameraError}</p>
                    )}
                    <motion.button
                      onClick={startCamera}
                      style={{
                        marginTop: '12px',
                        padding: '8px 16px',
                        backgroundColor: '#6b7280',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        margin: '12px auto'
                      }}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <RefreshCw size={16} />
                      Reintentar
                    </motion.button>
                  </div>
                </div>
              )}

              {/* Overlay para estado inicial "off" */}
              {cameraState === 'off' && (
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  backgroundColor: '#374151',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 5
                }}>
                  <div style={{ textAlign: 'center', color: '#9ca3af' }}>
                    <Camera size={48} style={{ marginBottom: '16px' }} />
                    <p>Preparando cámara...</p>
                  </div>
                </div>
              )}
            </div>

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
