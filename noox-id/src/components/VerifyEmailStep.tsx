import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';

/** Paso posterior al registro: el usuario escribe el código de 6 dígitos que llegó a su correo. */
const VerifyEmailStep: React.FC = () => {
  const { pendingVerification, loginWithEmailOtp, resendVerificationCode, cancelVerification, isLoading, error } =
    useAuth();
  const [code, setCode] = useState('');
  const [sending, setSending] = useState(false);
  const [resent, setResent] = useState(false);

  if (!pendingVerification) return null;

  const verificar = async (e: React.FormEvent) => {
    e.preventDefault();
    await loginWithEmailOtp(pendingVerification.email, code);
  };

  const reenviar = async () => {
    setSending(true);
    setResent(await resendVerificationCode());
    setSending(false);
  };

  return (
    <div className="auth-container">
      <motion.div
        className="auth-card"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4 }}
      >
        <div className="sidebar-logo" style={{ margin: '0 auto 20px' }}>N</div>
        <h2 className="auth-title">Verifica tu correo</h2>
        <p className="auth-subtitle">
          {pendingVerification.sent || resent
            ? <>Enviamos un código de 6 dígitos a <strong>{pendingVerification.email}</strong>.</>
            : <>Tu correo <strong>{pendingVerification.email}</strong> aún no está verificado. Pide un código.</>}
        </p>

        {error && (
          <div style={{ padding: '10px', marginBottom: '16px', backgroundColor: '#fee2e2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', fontSize: '14px' }}>
            {error}
          </div>
        )}

        <form onSubmit={verificar} style={{ width: '100%' }}>
          <input
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            style={{ width: '100%', padding: '12px', marginBottom: '15px', border: '1px solid #d1d5db', borderRadius: '8px', fontSize: '22px', letterSpacing: '8px', textAlign: 'center' }}
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
            {isLoading ? 'Verificando...' : 'Verificar y entrar'}
          </motion.button>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={reenviar} disabled={sending}>
              {sending ? 'Enviando...' : pendingVerification.sent || resent ? 'Reenviar código' : 'Enviar código'}
            </button>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={cancelVerification}>
              Volver
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

export default VerifyEmailStep;
