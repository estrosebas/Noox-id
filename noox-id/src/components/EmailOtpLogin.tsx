import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px',
  marginBottom: '15px',
  border: '1px solid #d1d5db',
  borderRadius: '8px',
  fontSize: '16px'
};

/** Entrar sin contraseña con un código de 6 dígitos enviado al correo (alternativa al rostro). */
const EmailOtpLogin: React.FC = () => {
  const { requestEmailOtp, loginWithEmailOtp, isLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);

  const enviar = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setSending(true);
    const ok = await requestEmailOtp(email);
    setSending(false);
    if (ok) {
      setSent(true);
      setCode('');
    }
  };

  const entrar = async (e: React.FormEvent) => {
    e.preventDefault();
    await loginWithEmailOtp(email, code);
  };

  if (!sent) {
    return (
      <form onSubmit={enviar} style={{ width: '100%' }}>
        <input
          type="email"
          placeholder="Correo electrónico"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={inputStyle}
          required
        />
        <motion.button
          type="submit"
          disabled={sending || !email}
          className="btn btn-primary"
          style={{ width: '100%', marginBottom: '15px' }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {sending ? 'Enviando...' : '✉️ Enviarme un código'}
        </motion.button>
        <p style={{ color: '#6b7280', fontSize: '13px', textAlign: 'center' }}>
          Te enviaremos un código de 6 dígitos. No necesitas contraseña.
        </p>
      </form>
    );
  }

  return (
    <form onSubmit={entrar} style={{ width: '100%' }}>
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '12px' }}>
        Si <strong>{email}</strong> está registrado, enviamos un código. Revisa tu bandeja (y el spam).
      </p>
      <input
        inputMode="numeric"
        autoComplete="one-time-code"
        placeholder="000000"
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
        style={{ ...inputStyle, fontSize: '22px', letterSpacing: '8px', textAlign: 'center' }}
        autoFocus
      />
      <motion.button
        type="submit"
        disabled={isLoading || code.length !== 6}
        className="btn btn-primary"
        style={{ width: '100%', marginBottom: '10px' }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        {isLoading ? 'Verificando...' : 'Entrar'}
      </motion.button>
      <div style={{ display: 'flex', gap: '10px' }}>
        <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => enviar()} disabled={sending}>
          {sending ? 'Enviando...' : 'Reenviar código'}
        </button>
        <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setSent(false)}>
          Cambiar correo
        </button>
      </div>
    </form>
  );
};

export default EmailOtpLogin;
