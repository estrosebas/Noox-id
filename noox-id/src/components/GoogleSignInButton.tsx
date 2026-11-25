import React, { useEffect, useRef } from 'react';

// Botón oficial de «Sign in with Google» (Google Identity Services). Entrega un ID token firmado por
// Google, que el backend verifica: el correo nunca se toma de lo que diga el navegador.
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
const SCRIPT_SRC = 'https://accounts.google.com/gsi/client';

interface GsiApi {
  accounts: {
    id: {
      initialize: (config: { client_id: string; callback: (r: { credential: string }) => void }) => void;
      renderButton: (el: HTMLElement, options: Record<string, unknown>) => void;
    };
  };
}

const gsi = () => (window as unknown as { google?: GsiApi }).google;

const cargarScript = (): Promise<void> =>
  new Promise((resolve, reject) => {
    if (gsi()) return resolve();
    let script = document.querySelector<HTMLScriptElement>(`script[src="${SCRIPT_SRC}"]`);
    if (!script) {
      script = document.createElement('script');
      script.src = SCRIPT_SRC;
      script.async = true;
      document.head.appendChild(script);
    }
    script.addEventListener('load', () => resolve());
    script.addEventListener('error', () => reject(new Error('No se pudo cargar Google')));
  });

interface Props {
  onCredential: (idToken: string) => void | Promise<unknown>;
}

const GoogleSignInButton: React.FC<Props> = ({ onCredential }) => {
  const contenedor = useRef<HTMLDivElement>(null);
  const alRecibir = useRef(onCredential);
  alRecibir.current = onCredential;

  useEffect(() => {
    if (!CLIENT_ID) return;
    let activo = true;
    cargarScript()
      .then(() => {
        const api = gsi();
        if (!activo || !api || !contenedor.current) return;
        api.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: (respuesta) => alRecibir.current(respuesta.credential)
        });
        api.accounts.id.renderButton(contenedor.current, {
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          width: 300
        });
      })
      .catch(() => undefined);
    return () => {
      activo = false;
    };
  }, []);

  if (!CLIENT_ID) {
    return (
      <p style={{ color: '#6b7280', fontSize: '13px', textAlign: 'center' }}>
        El acceso con Google no está configurado (falta VITE_GOOGLE_CLIENT_ID).
      </p>
    );
  }

  return <div ref={contenedor} style={{ display: 'flex', justifyContent: 'center' }} />;
};

export default GoogleSignInButton;
