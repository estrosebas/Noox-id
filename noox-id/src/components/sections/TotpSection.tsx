import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldOff, RefreshCw, Copy } from 'lucide-react';
import { TotpService } from '../../services/totpService';
import type { TotpSetup } from '../../services/totpService';

type Fase = 'cargando' | 'inactivo' | 'configurando' | 'activo';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px',
  border: '1px solid #374151',
  borderRadius: '8px',
  backgroundColor: '#1f2937',
  color: '#ffffff',
  fontSize: '22px',
  letterSpacing: '8px',
  textAlign: 'center'
};

const TotpSection: React.FC = () => {
  const [fase, setFase] = useState<Fase>('cargando');
  const [setup, setSetup] = useState<TotpSetup | null>(null);
  const [codigo, setCodigo] = useState('');
  const [error, setError] = useState('');
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    cargarEstado();
  }, []);

  const cargarEstado = async () => {
    try {
      const estado = await TotpService.getStatus();
      setFase(estado.enabled ? 'activo' : 'inactivo');
    } catch {
      setError('No se pudo consultar el estado del autenticador');
      setFase('inactivo');
    }
  };

  const mensaje = (e: unknown) => (e instanceof Error ? e.message : 'Ocurrió un error');

  const iniciar = async () => {
    setError('');
    setOcupado(true);
    try {
      setSetup(await TotpService.setup());
      setCodigo('');
      setFase('configurando');
    } catch (e) {
      setError(mensaje(e));
    } finally {
      setOcupado(false);
    }
  };

  const activar = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setError('');
    setOcupado(true);
    try {
      await TotpService.enable(codigo);
      setSetup(null);
      setCodigo('');
      setFase('activo');
    } catch (e) {
      setError(mensaje(e));
    } finally {
      setOcupado(false);
    }
  };

  const desactivar = async (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!confirm('Las apps que exigen TOTP no te dejarán entrar hasta que lo vuelvas a configurar. ¿Desactivar?')) return;
    setError('');
    setOcupado(true);
    try {
      await TotpService.disable(codigo);
      setCodigo('');
      setFase('inactivo');
    } catch (e) {
      setError(mensaje(e));
    } finally {
      setOcupado(false);
    }
  };

  const soloDigitos = (v: string) => v.replace(/\D/g, '').slice(0, 6);

  if (fase === 'cargando') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
        <RefreshCw size={32} className="animate-spin" color="#4285f4" />
        <span style={{ marginLeft: '10px', color: '#e0e0e0' }}>Cargando...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="header">
        <h1 className="header-title">Autenticador (TOTP)</h1>
      </div>

      <motion.div
        className="card"
        style={{ maxWidth: '560px', margin: '0 auto' }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{
            width: '64px',
            height: '64px',
            background: fase === 'activo' ? 'linear-gradient(135deg, #34a853, #4285f4)' : '#374151',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
            color: 'white'
          }}>
            {fase === 'activo' ? <ShieldCheck size={32} /> : <ShieldOff size={32} />}
          </div>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: '#ffffff', marginBottom: '8px' }}>
            {fase === 'activo' ? 'Autenticador activo' : 'Segundo factor de seguridad'}
          </h3>
          <p style={{ color: '#9aa0a6', fontSize: '15px', lineHeight: 1.5 }}>
            Algunas aplicaciones piden, después de tu rostro, un código de 6 dígitos que cambia cada 30 segundos
            (Google Authenticator, Microsoft Authenticator, Authy, 1Password…).
          </p>
        </div>

        {error && (
          <div style={{ padding: '10px 12px', borderRadius: '8px', backgroundColor: '#7f1d1d', color: '#fecaca', fontSize: '14px', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {fase === 'inactivo' && (
          <button className="btn btn-primary" style={{ width: '100%' }} onClick={iniciar} disabled={ocupado}>
            {ocupado ? 'Preparando...' : 'Configurar autenticador'}
          </button>
        )}

        {fase === 'configurando' && setup && (
          <form onSubmit={activar}>
            <p style={{ color: '#e0e0e0', fontSize: '14px', marginBottom: '12px' }}>
              1. Escanea este código QR con tu app autenticadora.
            </p>
            <div style={{ textAlign: 'center', marginBottom: '16px' }}>
              <img
                src={setup.qr}
                alt="Código QR para el autenticador"
                style={{ width: '200px', height: '200px', background: '#fff', padding: '8px', borderRadius: '8px' }}
              />
            </div>
            <p style={{ color: '#9aa0a6', fontSize: '13px', marginBottom: '6px' }}>
              ¿No puedes escanearlo? Ingresa esta clave a mano:
            </p>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '20px' }}>
              <code style={{
                flex: 1,
                fontSize: '13px',
                color: '#10b981',
                backgroundColor: '#111827',
                padding: '8px',
                borderRadius: '6px',
                border: '1px solid #374151',
                wordBreak: 'break-all'
              }}>
                {setup.secret}
              </code>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '8px' }}
                onClick={() => navigator.clipboard.writeText(setup.secret)}
                title="Copiar"
              >
                <Copy size={16} />
              </button>
            </div>
            <p style={{ color: '#e0e0e0', fontSize: '14px', marginBottom: '8px' }}>
              2. Escribe el código de 6 dígitos que muestra la app para confirmar.
            </p>
            <input
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              value={codigo}
              onChange={(e) => setCodigo(soloDigitos(e.target.value))}
              style={inputStyle}
              autoFocus
            />
            <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
              <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={ocupado || codigo.length !== 6}>
                {ocupado ? 'Verificando...' : 'Activar'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => { setFase('inactivo'); setSetup(null); setCodigo(''); setError(''); }}
              >
                Cancelar
              </button>
            </div>
          </form>
        )}

        {fase === 'activo' && (
          <form onSubmit={desactivar}>
            <p style={{ color: '#9aa0a6', fontSize: '14px', marginBottom: '8px' }}>
              Para desactivarlo, escribe un código vigente de tu app:
            </p>
            <input
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              value={codigo}
              onChange={(e) => setCodigo(soloDigitos(e.target.value))}
              style={inputStyle}
            />
            <button
              type="submit"
              className="btn btn-danger"
              style={{ width: '100%', marginTop: '16px' }}
              disabled={ocupado || codigo.length !== 6}
            >
              {ocupado ? 'Verificando...' : 'Desactivar autenticador'}
            </button>
          </form>
        )}
      </motion.div>
    </div>
  );
};

export default TotpSection;
