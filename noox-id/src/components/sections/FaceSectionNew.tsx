import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Camera, Upload, RefreshCw, Check, X, Eye, Settings } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { UserService } from '../../services/userService';
import { FaceService } from '../../services/faceService';

const FaceSection: React.FC = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [tolerance, setTolerance] = useState(0.6);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const { user, refreshProfile } = useAuth();

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadResult(null);

    try {
      // Convert to base64
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const base64String = reader.result as string;
          setPreviewImage(base64String);
          
          const response = await UserService.uploadFaceImage(base64String);
          setUploadResult(response);
          
          if (response.success) {
            await refreshProfile();
          }
        } catch (error) {
          console.error('Error uploading face image:', error);
          setUploadResult({ success: false, message: 'Error al subir la imagen' });
        } finally {
          setIsUploading(false);
        }
      };
      reader.readAsDataURL(file);
    } catch (error) {
      console.error('Error processing file:', error);
      setIsUploading(false);
    }
  };

  const startCamera = async () => {
    try {
      setIsCapturing(true);
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch (error) {
      console.error('Error accessing camera:', error);
      setIsCapturing(false);
    }
  };

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;
    const context = canvas.getContext('2d');

    if (!context) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);

    // Convert to base64
    const base64String = canvas.toDataURL('image/jpeg');
    setPreviewImage(base64String);

    // Stop camera
    const stream = video.srcObject as MediaStream;
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    setIsCapturing(false);

    // Upload the captured image
    setIsUploading(true);
    try {
      const response = await UserService.uploadFaceImage(base64String);
      setUploadResult(response);
      
      if (response.success) {
        await refreshProfile();
      }
    } catch (error) {
      console.error('Error uploading captured image:', error);
      setUploadResult({ success: false, message: 'Error al subir la imagen capturada' });
    } finally {
      setIsUploading(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current) {
      const stream = videoRef.current.srcObject as MediaStream;
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    }
    setIsCapturing(false);
  };

  const handleVerifyFace = async () => {
    if (!previewImage) return;

    setIsVerifying(true);
    setVerificationResult(null);

    try {
      const response = await UserService.verifyFace(previewImage);
      setVerificationResult(response);
    } catch (error) {
      console.error('Error verifying face:', error);
      setVerificationResult({ success: false, message: 'Error al verificar el rostro' });
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
            onClick={isCapturing ? stopCamera : startCamera}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Camera size={20} />
            {isCapturing ? 'Detener Cámara' : 'Usar Cámara'}
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
          Configuración de Tolerancia
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <label style={{ color: '#e0e0e0', fontSize: '14px', minWidth: '100px' }}>
            Tolerancia: {tolerance.toFixed(2)}
          </label>
          <input
            type="range"
            min="0.3"
            max="1.0"
            step="0.05"
            value={tolerance}
            onChange={(e) => handleToleranceChange(parseFloat(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ color: '#9aa0a6', fontSize: '12px', minWidth: '150px' }}>
            {tolerance < 0.5 ? 'Muy estricto' : tolerance < 0.7 ? 'Equilibrado' : 'Permisivo'}
          </span>
        </div>
        <p style={{ color: '#9aa0a6', fontSize: '12px', marginTop: '8px' }}>
          Una tolerancia menor significa verificaciones más estrictas. Recomendado: 0.6
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
          
          <div style={{ 
            width: '100%', 
            height: '300px', 
            backgroundColor: '#1f2937', 
            borderRadius: '12px',
            border: '2px dashed #374151',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '16px',
            overflow: 'hidden',
            position: 'relative'
          }}>
            {isCapturing ? (
              <>
                <video
                  ref={videoRef}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  autoPlay
                  muted
                />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
                <motion.button
                  onClick={capturePhoto}
                  className="btn btn-primary"
                  style={{ 
                    position: 'absolute', 
                    bottom: '16px', 
                    left: '50%', 
                    transform: 'translateX(-50%)' 
                  }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Camera size={20} />
                  Capturar
                </motion.button>
              </>
            ) : previewImage ? (
              <img
                src={previewImage}
                alt="Preview"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            ) : (
              <div style={{ textAlign: 'center', color: '#9aa0a6' }}>
                <Camera size={48} style={{ marginBottom: '16px' }} />
                <p>Usa la cámara o sube una imagen</p>
              </div>
            )}
          </div>

          {previewImage && !isCapturing && (
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
                {isVerifying ? 'Verificando...' : 'Verificar Rostro'}
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
                  Verificación de Rostro
                </span>
              </div>
              {verificationResult.data && (
                <div style={{ color: '#d1d5db', fontSize: '14px' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                    {JSON.stringify(verificationResult.data, null, 2)}
                  </pre>
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
