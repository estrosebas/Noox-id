import React, { useEffect } from 'react';
import { Camera, RefreshCw } from 'lucide-react';
import { useFaceCapture } from '../hooks/useFaceCapture';

interface FaceCameraProps {
  /** Se llama una vez con la foto (data URL JPEG) cuando la captura es válida. */
  onCapture: (photo: string) => void;
  /** El padre está procesando la foto (login, subida…). */
  busy?: boolean;
  busyLabel?: string;
}

const COLORS: Record<string, string> = {
  listo: '#22c55e', buscando: '#9ca3af', varias: '#ef4444',
  cerca: '#f59e0b', lejos: '#f59e0b', descentrado: '#f59e0b',
};

/** Visor de cámara con óvalo guía, autocaptura y revisión de encuadre (MediaPipe). */
const FaceCamera: React.FC<FaceCameraProps> = ({ onCapture, busy = false, busyLabel = 'Analizando…' }) => {
  const cam = useFaceCapture();
  const { start, photo } = cam;

  useEffect(() => { void start(); }, [start]);
  useEffect(() => { if (photo) onCapture(photo); }, [photo]); // eslint-disable-line react-hooks/exhaustive-deps

  const color = COLORS[cam.guide.estado] ?? '#9ca3af';
  const box: React.CSSProperties = {
    position: 'relative', width: '100%', maxWidth: 360, aspectRatio: '1 / 1', margin: '0 auto 12px',
    borderRadius: 12, overflow: 'hidden', backgroundColor: '#111827',
  };
  const center: React.CSSProperties = {
    position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', color: '#d1d5db', textAlign: 'center', padding: 16,
  };
  const button: React.CSSProperties = {
    padding: '10px 18px', backgroundColor: '#4285f4', color: '#fff', border: 'none',
    borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600,
    display: 'inline-flex', alignItems: 'center', gap: 8,
  };

  return (
    <div>
      <div style={box}>
        {photo ? (
          <>
            <img src={photo} alt="Foto capturada" style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }} />
            {busy && <div style={{ ...center, background: 'rgba(0,0,0,.55)' }}>{busyLabel}</div>}
          </>
        ) : (
          <>
            <video ref={cam.videoRef} autoPlay muted playsInline
              style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }} />
            {cam.status === 'ready' && (
              <svg viewBox="0 0 100 100" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                <defs>
                  <mask id="face-oval-mask">
                    <rect width="100" height="100" fill="#fff" />
                    <ellipse cx="50" cy="50" rx="30" ry="38" fill="#000" />
                  </mask>
                </defs>
                <rect width="100" height="100" fill="rgba(0,0,0,.45)" mask="url(#face-oval-mask)" />
                <ellipse cx="50" cy="50" rx="30" ry="38" fill="none" stroke={color} strokeWidth="1.2"
                  strokeDasharray={cam.progress > 0 ? undefined : '3 2'} />
              </svg>
            )}
            {cam.status === 'starting' && <div style={{ ...center, background: '#1f2937' }}>Iniciando cámara…</div>}
            {cam.status === 'error' && (
              <div style={{ ...center, background: '#1f2937', color: '#fca5a5' }}>
                <p style={{ marginBottom: 12 }}>{cam.error}</p>
                <button style={button} onClick={() => void start()}><RefreshCw size={16} />Reintentar</button>
              </div>
            )}
          </>
        )}
      </div>

      {!photo && cam.status === 'ready' && (
        <div style={{ textAlign: 'center' }}>
          <p style={{ color, fontSize: 14, margin: '0 0 8px', minHeight: 20 }}>
            {cam.detectorFailed
              ? 'No se pudo iniciar la detección automática. Toma la foto manualmente.'
              : cam.detectorReady ? cam.guide.mensaje : 'Cargando detector facial…'}
          </p>
          <div style={{ height: 6, borderRadius: 3, background: '#374151', maxWidth: 360, margin: '0 auto 12px', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${Math.round(cam.progress * 100)}%`, background: color, transition: 'width .15s' }} />
          </div>
          {cam.detectorFailed && (
            <button style={button} onClick={cam.captureManual}><Camera size={16} />Capturar foto</button>
          )}
        </div>
      )}

      {photo && !busy && (
        <div style={{ textAlign: 'center' }}>
          <button style={{ ...button, backgroundColor: '#6b7280' }} onClick={() => void cam.retake()}>
            <RefreshCw size={16} />Tomar otra
          </button>
        </div>
      )}
    </div>
  );
};

export default FaceCamera;
