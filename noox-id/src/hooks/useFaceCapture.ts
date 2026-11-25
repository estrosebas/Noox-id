import { useCallback, useEffect, useRef, useState } from 'react';
import type { FaceDetector as MPFaceDetector } from '@mediapipe/tasks-vision';
import { createStability, evaluateCapture } from '../utils/faceQuality';
import type { Reading } from '../utils/faceQuality';

/**
 * Cámara frontal + MediaPipe (BlazeFace) para guiar el encuadre y autocapturar un
 * cuadrado JPEG cuando el rostro es único, está completo, nítido y estable.
 * MediaPipe solo guía al usuario: la identidad la decide el backend (YuNet + SFace).
 * Los archivos viven en /public/mediapipe (sin CDN).
 */
const SIDE = 720;

export type CameraStatus = 'idle' | 'starting' | 'ready' | 'error';

export function useFaceCapture() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState<CameraStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [detectorReady, setDetectorReady] = useState(false);
  const [detectorFailed, setDetectorFailed] = useState(false);
  const [guide, setGuide] = useState<Reading>({ estado: 'buscando', mensaje: 'Coloca tu rostro dentro del óvalo' });
  const [progress, setProgress] = useState(0);
  const [photo, setPhoto] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const detectorRef = useRef<MPFaceDetector | null>(null);
  const rafRef = useRef<number | null>(null);
  const generation = useRef(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const bestRef = useRef<HTMLCanvasElement | null>(null);
  const stability = useRef(createStability());
  const lastFrame = useRef(-1);
  const lastRun = useRef(0);

  const stop = useCallback(() => {
    generation.current += 1;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    detectorRef.current?.close();
    detectorRef.current = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    stability.current.reset();
    bestRef.current = null;
    setDetectorReady(false);
    setProgress(0);
    setStatus('idle');
  }, []);

  const cameraMessage = (e: unknown) => {
    const name = (e as { name?: string })?.name;
    if (name === 'NotAllowedError' || name === 'SecurityError')
      return 'No diste permiso para usar la cámara. Habilítala desde el candado de la barra de direcciones.';
    if (name === 'NotFoundError') return 'No encontramos ninguna cámara en este dispositivo.';
    if (name === 'NotReadableError') return 'Otra aplicación está usando la cámara. Ciérrala e inténtalo de nuevo.';
    return 'No pudimos abrir la cámara. Revisa los permisos e inténtalo de nuevo.';
  };

  const takeBest = useCallback((fallback: HTMLCanvasElement) => {
    const src = bestRef.current ?? fallback;
    setPhoto(src.toDataURL('image/jpeg', 0.92));
    // Se corta la cámara: la foto evaluada es exactamente la que se envía.
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    detectorRef.current?.close();
    detectorRef.current = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setStatus('idle');
    setProgress(0);
  }, []);

  const drawSquare = (video: HTMLVideoElement) => {
    const side = Math.min(video.videoWidth, video.videoHeight);
    const out = Math.min(SIDE, side); // nunca se amplía una cámara de baja resolución
    const canvas = (canvasRef.current ??= document.createElement('canvas'));
    if (canvas.width !== out) { canvas.width = out; canvas.height = out; }
    canvas.getContext('2d', { willReadFrequently: true })!.drawImage(
      video, (video.videoWidth - side) / 2, (video.videoHeight - side) / 2, side, side, 0, 0, out, out);
    return canvas;
  };

  const loop = useCallback((gen: number) => {
    const tick = () => {
      if (gen !== generation.current) return;
      const video = videoRef.current;
      const detector = detectorRef.current;
      if (!video || !detector) return;
      const now = performance.now();
      if (video.readyState < 2 || !video.videoWidth || now - lastRun.current < 120
          || video.currentTime === lastFrame.current) {
        rafRef.current = requestAnimationFrame(tick);
        return;
      }
      lastRun.current = now;
      lastFrame.current = video.currentTime;
      try {
        const canvas = drawSquare(video);
        const out = detector.detectForVideo(canvas, now);
        const img = canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height);
        const reading = evaluateCapture(out.detections as never, img);
        setGuide(reading);
        const s = stability.current.update(reading, now);
        setProgress(s.progreso);
        if (s.descartarCandidato) bestRef.current = null;
        if (s.mejora) {
          const best = (bestRef.current ??= document.createElement('canvas'));
          best.width = canvas.width; best.height = canvas.height;
          best.getContext('2d')!.drawImage(canvas, 0, 0);
        }
        if (s.lista) { takeBest(canvas); return; }
      } catch (e) {
        console.warn('[face] análisis no disponible', e);
        setDetectorFailed(true);
        setDetectorReady(false);
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [takeBest]);

  const loadDetector = useCallback(async (gen: number) => {
    try {
      const vision = await import('@mediapipe/tasks-vision');
      const files = await vision.FilesetResolver.forVisionTasks('/mediapipe/wasm');
      const options = (delegate: 'GPU' | 'CPU') => ({
        baseOptions: { modelAssetPath: '/mediapipe/blaze_face_short_range.tflite', delegate },
        runningMode: 'VIDEO' as const,
        minDetectionConfidence: 0.6,
      });
      let detector: MPFaceDetector;
      try {
        detector = await vision.FaceDetector.createFromOptions(files, options('GPU'));
      } catch {
        detector = await vision.FaceDetector.createFromOptions(files, options('CPU'));
      }
      if (gen !== generation.current) { detector.close(); return; }
      detectorRef.current = detector;
      setDetectorReady(true);
      loop(gen);
    } catch (e) {
      if (gen !== generation.current) return;
      console.warn('[face] MediaPipe no pudo iniciar', e);
      setDetectorFailed(true); // queda el disparador manual; el backend valida igual
    }
  }, [loop]);

  const start = useCallback(async (deviceId?: string) => {
    stop();
    const gen = generation.current;
    setStatus('starting');
    setError(null);
    setPhoto(null);
    setDetectorFailed(false);
    setGuide({ estado: 'buscando', mensaje: 'Coloca tu rostro dentro del óvalo' });
    lastFrame.current = -1;
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Este navegador no permite usar la cámara (requiere HTTPS o localhost).');
      setStatus('error');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { ...(deviceId ? { deviceId: { exact: deviceId } } : { facingMode: 'user' }),
          width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      if (gen !== generation.current) { stream.getTracks().forEach(t => t.stop()); return; }
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) { stream.getTracks().forEach(t => t.stop()); return; }
      video.srcObject = stream;
      await video.play().catch(() => undefined);
      if (gen !== generation.current) return;
      setStatus('ready');
      void loadDetector(gen);
    } catch (e) {
      if (gen !== generation.current) return;
      setError(cameraMessage(e));
      setStatus('error');
    }
  }, [stop, loadDetector]);

  /** Disparador manual: solo si MediaPipe no está disponible. */
  const captureManual = useCallback(() => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    takeBest(drawSquare(video));
  }, [takeBest]);

  const retake = useCallback(() => { setPhoto(null); return start(); }, [start]);

  useEffect(() => () => stop(), [stop]);

  return { videoRef, status, error, guide, progress, photo, detectorReady, detectorFailed,
    start, stop, retake, captureManual };
}
