import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Camera, Upload, RefreshCw, Check, X, Eye, Settings, StopCircle } from 'lucide-react';
import FaceCamera from '../FaceCamera';
import { useAuth } from '../../contexts/AuthContext';
import { FaceService, ImageUtils } from '../../services/faceService';

const FaceSection: React.FC = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  // Umbral mínimo de similitud coseno (SFace): más alto = más estricto.
  const [tolerance, setTolerance] = useState(0.363);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { user, refreshProfile, loginWithFace } = useAuth();

  // Cargar tolerancia al montar
  useEffect(() => {
    const loadTolerance = async () => {
      try {
        const response = await FaceService.getTolerance();
        if (response.success && response.data) {
          setTolerance(response.data.tolerance);
        }
      } catch (error) {
        console.error('Error loading tolerance:', error);
      }
    };
    loadTolerance();
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadResult(null);

    try {
      // Redimensionar y optimizar la imagen
      const optimizedBase64 = await ImageUtils.resizeImage(file, 800, 600, 0.8);
      setPreviewImage(optimizedBase64);
      
      // Usar el servicio de procesamiento de imagen de perfil
      const response = await FaceService.processProfileImage(optimizedBase64);
      setUploadResult(response);
      
      if (response.success) {
        await refreshProfile();
      }
    } catch (error) {
      console.error('Error uploading face image:', error);
      setUploadResult({ 
        success: false, 
        message: error instanceof Error ? error.message : 'Error al procesar la imagen' 
      });
    } finally {
      setIsUploading(false);
    }
  };

  // FaceCamera ya validó el encuadre en el navegador (MediaPipe);
  // el backend (YuNet + SFace) extrae y guarda el vector facial.
  const handleCameraCapture = async (photo: string) => {
    setShowCamera(false);
    setPreviewImage(photo);
    setUploadResult(null);
    setVerificationResult(null);
    setIsUploading(true);
    try {
      const response = await FaceService.processProfileImage(photo);
      setUploadResult(response);
      if (response.success) await refreshProfile();
    } catch (error) {
      setUploadResult({
        success: false,
        message: error instanceof Error ? error.message : 'Error al procesar la imagen'
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleVerifyFace = async () => {
    if (!previewImage) return;

    setIsVerifying(true);
    setVerificationResult(null);

    try {
      // Extraer email del JWT token
      const token = localStorage.getItem('noox_token');
      if (!token) {
        setVerificationResult({ 
          success: false, 
          message: 'No hay token de autenticación disponible' 
        });
        return;
      }

      // Decodificar JWT para obtener el email
      let userEmail = '';
      try {
        const tokenParts = token.split('.');
        if (tokenParts.length === 3) {
          const payload = JSON.parse(atob(tokenParts[1]));
          userEmail = payload.email;
          console.log('📧 Email extraído del JWT:', userEmail);
        } else {
          throw new Error('Token JWT malformado');
        }
      } catch (jwtError) {
        console.error('Error decodificando JWT:', jwtError);
        setVerificationResult({ 
          success: false, 
          message: 'Error al decodificar el token de autenticación' 
        });
        return;
      }

      if (!userEmail) {
        setVerificationResult({ 
          success: false, 
          message: 'No se pudo obtener el email del token' 
        });
        return;
      }

      // Usar el endpoint de login facial para verificar
      console.log('🔍 Verificando rostro con login facial...');
      const response = await loginWithFace(userEmail, previewImage);
      
      // Crear resultado de verificación basado en la respuesta del login facial
      if (response) {
        setVerificationResult({
          success: true,
          message: '✅ Rostro verificado exitosamente - Coincide con tu perfil',
          data: {
            email: userEmail,
            verified: true,
            method: 'facial_login_verification'
          }
        });
        console.log('✅ Verificación facial exitosa');
      } else {
        setVerificationResult({
          success: false,
          message: '❌ El rostro no coincide con tu perfil registrado',
          data: {
            email: userEmail,
            verified: false,
            method: 'facial_login_verification'
          }
        });
        console.log('❌ Verificación facial fallida');
      }

    } catch (error) {
      console.error('Error verifying face:', error);
      setVerificationResult({ 
        success: false, 
        message: error instanceof Error ? error.message : 'Error al verificar el rostro' 
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleToleranceChange = async (newTolerance: number) => {
    setTolerance(newTolerance);
    try {
      await FaceService.setTolerance(newTolerance);
    } catch (error) {
      console.error('Error setting tolerance:', error);
    }
  };

  return (
    <div>
      <div className="header">
        <h1 className="header-title">Reconocimiento Facial</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <motion.button
            className="btn btn-secondary"
            onClick={() => fileInputRef.current?.click()}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Upload size={20} />
            Subir Imagen
          </motion.button>
          <motion.button
            className="btn btn-primary"
            onClick={() => setShowCamera(v => !v)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {showCamera ? <StopCircle size={20} /> : <Camera size={20} />}
            {showCamera ? 'Detener Cámara' : 'Usar Cámara'}
          </motion.button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileUpload}
        style={{ display: 'none' }}
      />

      {/* Tolerance Control */}
      <motion.div
        className="card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ marginBottom: '20px' }}
      >
        <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#ffffff', marginBottom: '16px' }}>
          <Settings size={20} style={{ display: 'inline', marginRight: '8px' }} />
          Umbral de Similitud (SFace)
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <label style={{ color: '#e0e0e0', fontSize: '14px', minWidth: '100px' }}>
            Umbral: {tolerance.toFixed(2)}
          </label>
          <input
            type="range"
            min="0.2"
            max="0.8"
            step="0.01"
            value={tolerance}
            onChange={(e) => handleToleranceChange(parseFloat(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ color: '#9aa0a6', fontSize: '12px', minWidth: '150px' }}>
            {tolerance < 0.3 ? 'Permisivo' : tolerance < 0.45 ? 'Equilibrado' : 'Muy estricto'}
          </span>
        </div>
        <p style={{ color: '#9aa0a6', fontSize: '12px', marginTop: '8px' }}>
          Un umbral mayor exige mayor parecido (más estricto). Valor recomendado por OpenCV para SFace: 0.363
        </p>
      </motion.div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        
        {/* Camera/Upload Section */}
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#ffffff', marginBottom: '16px' }}>
            Captura de Imagen
          </h3>
          
          {showCamera ? (
            <FaceCamera onCapture={handleCameraCapture} busy={isUploading} />
          ) : (
            <div style={{
              width: '100%',
              height: '300px',
              backgroundColor: '#1f2937',
              borderRadius: '12px',
              border: '2px dashed #374151',
              marginBottom: '16px',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              color: '#9aa0a6'
            }}>
              {previewImage ? (
                <img src={previewImage} alt="Preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                <div>
                  <Camera size={48} style={{ marginBottom: '16px' }} />
                  <p>Usa la cámara o sube una imagen</p>
                </div>
              )}
            </div>
          )}

          {previewImage && !showCamera && (
            <div style={{ display: 'flex', gap: '10px' }}>
              <motion.button
                onClick={handleVerifyFace}
                disabled={isVerifying}
                className="btn btn-primary"
                style={{ flex: 1 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {isVerifying ? (
                  <RefreshCw size={16} className="animate-spin" />
                ) : (
                  <Eye size={16} />
                )}
                {isVerifying ? 'Verificando...' : 'Verificar con Login Facial'}
              </motion.button>
              <button
                onClick={() => {
                  setPreviewImage(null);
                  setUploadResult(null);
                  setVerificationResult(null);
                }}
                className="btn btn-secondary"
              >
                <X size={16} />
                Limpiar
              </button>
            </div>
          )}
        </motion.div>

        {/* Results Section */}
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#ffffff', marginBottom: '16px' }}>
            Resultados
          </h3>

          {/* Upload Result */}
          {uploadResult && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '16px',
                backgroundColor: uploadResult.success ? '#065f46' : '#7f1d1d',
                border: `1px solid ${uploadResult.success ? '#059669' : '#dc2626'}`
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                {uploadResult.success ? (
                  <Check size={16} color="#10b981" />
                ) : (
                  <X size={16} color="#ef4444" />
                )}
                <span style={{ color: '#ffffff', fontWeight: '500' }}>
                  {uploadResult.success ? 'Imagen subida exitosamente' : 'Error al subir imagen'}
                </span>
              </div>
              {uploadResult.message && (
                <p style={{ color: '#d1d5db', fontSize: '14px', margin: 0 }}>
                  {uploadResult.message}
                </p>
              )}
            </motion.div>
          )}

          {/* Verification Result */}
          {verificationResult && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '16px',
                backgroundColor: verificationResult.success ? '#065f46' : '#7f1d1d',
                border: `1px solid ${verificationResult.success ? '#059669' : '#dc2626'}`
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                {verificationResult.success ? (
                  <Check size={16} color="#10b981" />
                ) : (
                  <X size={16} color="#ef4444" />
                )}
                <span style={{ color: '#ffffff', fontWeight: '500' }}>
                  Verificación Facial (Login)
                </span>
              </div>
              {verificationResult.data && (
                <div style={{ color: '#d1d5db', fontSize: '14px' }}>
                  <div style={{ marginBottom: '8px' }}>
                    <strong>Email:</strong> {verificationResult.data.email || 'N/A'}
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <strong>Método:</strong> {verificationResult.data.method || 'N/A'}
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <strong>Estado:</strong> {verificationResult.data.verified ? '✅ Verificado' : '❌ No verificado'}
                  </div>
                  {/* Mostrar datos adicionales si existen */}
                  {Object.keys(verificationResult.data).length > 3 && (
                    <details style={{ marginTop: '8px' }}>
                      <summary style={{ cursor: 'pointer', color: '#9ca3af' }}>Ver detalles técnicos</summary>
                      <pre style={{ margin: '8px 0 0 0', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '12px' }}>
                        {JSON.stringify(verificationResult.data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </motion.div>
          )}

          {/* Current Status */}
          <div style={{ 
            padding: '12px',
            backgroundColor: '#1f2937',
            borderRadius: '8px',
            border: '1px solid #374151'
          }}>
            <h4 style={{ color: '#ffffff', fontSize: '16px', marginBottom: '12px' }}>Estado Actual</h4>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ color: '#e0e0e0' }}>Imagen de perfil facial</span>
              <span style={{ 
                color: user?.ProfilePickPath ? '#10b981' : '#f59e0b', 
                fontWeight: '500' 
              }}>
                {user?.ProfilePickPath ? '✓ Configurada' : '⚠ No configurada'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#e0e0e0' }}>Reconocimiento facial activo</span>
              <span style={{ 
                color: user?.ProfilePickPath ? '#10b981' : '#ef4444', 
                fontWeight: '500' 
              }}>
                {user?.ProfilePickPath ? '✓ Disponible' : '✗ No disponible'}
              </span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Loading Overlay */}
      {isUploading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
        >
          <div style={{
            backgroundColor: '#1f2937',
            padding: '20px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px'
          }}>
            <RefreshCw size={24} className="animate-spin" color="#4285f4" />
            <span style={{ color: '#ffffff' }}>Procesando imagen facial...</span>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default FaceSection;
