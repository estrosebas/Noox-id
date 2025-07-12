import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Smartphone, Edit, Trash2, Plus, RefreshCw, Key, Copy, Eye, EyeOff } from 'lucide-react';
import { AppService } from '../../services/appService';
import type { App } from '../../services/api';

const AppsSection: React.FC = () => {
  const [apps, setApps] = useState<App[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [visibleApiKeys, setVisibleApiKeys] = useState<Set<number>>(new Set());
  const [newAppName, setNewAppName] = useState('');
  const [editingApp, setEditingApp] = useState<App | null>(null);

  useEffect(() => {
    loadApps();
  }, []);

  const loadApps = async () => {
    try {
      setIsLoading(true);
      const response = await AppService.getUserApps();
      if (response.success && response.data) {
        setApps(response.data.apps || []);
      }
    } catch (error) {
      console.error('Error loading apps:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateApp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAppName.trim()) return;

    try {
      setIsCreating(true);
      const response = await AppService.createApp({ name_app: newAppName });
      if (response.success) {
        setNewAppName('');
        setShowCreateForm(false);
        await loadApps();
      }
    } catch (error) {
      console.error('Error creating app:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleUpdateApp = async (app: App, newName: string) => {
    try {
      const response = await AppService.updateApp(app.id, { name_app: newName });
      if (response.success) {
        setEditingApp(null);
        await loadApps();
      }
    } catch (error) {
      console.error('Error updating app:', error);
    }
  };

  const handleDeleteApp = async (appId: number) => {
    if (!confirm('¿Estás seguro de que quieres eliminar esta aplicación?')) return;

    try {
      const response = await AppService.deleteApp(appId);
      if (response.success) {
        await loadApps();
      }
    } catch (error) {
      console.error('Error deleting app:', error);
    }
  };

  const handleRegenerateApiKey = async (appId: number) => {
    if (!confirm('¿Estás seguro de que quieres regenerar la API key? La anterior dejará de funcionar.')) return;

    try {
      const response = await AppService.regenerateApiKey(appId);
      if (response.success) {
        await loadApps();
      }
    } catch (error) {
      console.error('Error regenerating API key:', error);
    }
  };

  const toggleApiKeyVisibility = (appId: number) => {
    const newVisibleKeys = new Set(visibleApiKeys);
    if (newVisibleKeys.has(appId)) {
      newVisibleKeys.delete(appId);
    } else {
      newVisibleKeys.add(appId);
    }
    setVisibleApiKeys(newVisibleKeys);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getAppInitials = (name: string) => {
    return name.split(' ').map(word => word.charAt(0)).join('').slice(0, 2).toUpperCase();
  };

  const getAppColor = (id: number) => {
    const colors = ['#4285f4', '#ea4335', '#34a853', '#fbbc05', '#9c27b0', '#ff9800', '#795548', '#607d8b'];
    return colors[id % colors.length];
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
        <RefreshCw size={32} className="animate-spin" color="#4285f4" />
        <span style={{ marginLeft: '10px', color: '#e0e0e0' }}>Cargando aplicaciones...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="header">
        <h1 className="header-title">Aplicaciones vinculadas</h1>
        <motion.button
          className="btn btn-primary"
          onClick={() => setShowCreateForm(true)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Plus size={20} />
          Crear Nueva App
        </motion.button>
      </div>

      {/* Create App Form */}
      <AnimatePresence>
        {showCreateForm && (
          <motion.div
            className="card"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ marginBottom: '20px' }}
          >
            <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#ffffff', marginBottom: '16px' }}>
              Crear Nueva Aplicación
            </h3>
            <form onSubmit={handleCreateApp}>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'end' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '5px', color: '#e0e0e0', fontSize: '14px' }}>
                    Nombre de la aplicación
                  </label>
                  <input
                    type="text"
                    value={newAppName}
                    onChange={(e) => setNewAppName(e.target.value)}
                    placeholder="Mi App Increíble"
                    style={{
                      width: '100%',
                      padding: '12px',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      backgroundColor: '#1f2937',
                      color: '#ffffff',
                      fontSize: '16px'
                    }}
                    required
                  />
                </div>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="btn btn-primary"
                >
                  {isCreating ? 'Creando...' : 'Crear'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false);
                    setNewAppName('');
                  }}
                  className="btn btn-secondary"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Apps Grid */}
      {apps.length === 0 ? (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ textAlign: 'center', padding: '40px' }}
        >
          <Smartphone size={48} color="#6b7280" style={{ margin: '0 auto 20px' }} />
          <h3 style={{ color: '#e0e0e0', marginBottom: '10px' }}>No hay aplicaciones</h3>
          <p style={{ color: '#9aa0a6', marginBottom: '20px' }}>
            Crea tu primera aplicación para comenzar a usar NooxID
          </p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="btn btn-primary"
          >
            Crear Primera App
          </button>
        </motion.div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '20px' }}>
          {apps.map((app, index) => (
            <motion.div
              key={app.id}
              className="card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ scale: 1.02 }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', marginBottom: '16px' }}>
                <div style={{
                  width: '48px',
                  height: '48px',
                  backgroundColor: getAppColor(app.id),
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: '18px',
                  fontWeight: '600'
                }}>
                  {getAppInitials(app.name_app)}
                </div>
                <div style={{ flex: 1 }}>
                  {editingApp?.id === app.id ? (
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <input
                        type="text"
                        defaultValue={app.name_app}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleUpdateApp(app, e.currentTarget.value);
                          } else if (e.key === 'Escape') {
                            setEditingApp(null);
                          }
                        }}
                        style={{
                          flex: 1,
                          padding: '8px',
                          border: '1px solid #374151',
                          borderRadius: '6px',
                          backgroundColor: '#1f2937',
                          color: '#ffffff',
                          fontSize: '14px'
                        }}
                        autoFocus
                      />
                      <button
                        onClick={() => setEditingApp(null)}
                        className="btn btn-secondary"
                        style={{ padding: '6px 8px', fontSize: '12px' }}
                      >
                        ✓
                      </button>
                    </div>
                  ) : (
                    <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#ffffff', margin: 0 }}>
                      {app.name_app}
                    </h3>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                    <span style={{
                      fontSize: '12px',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      backgroundColor: app.is_verified ? '#065f46' : '#7c2d12',
                      color: app.is_verified ? '#10b981' : '#f59e0b'
                    }}>
                      {app.is_verified ? '✓ Verificada' : '⚠ Pendiente'}
                    </span>
                    <span style={{ fontSize: '12px', color: '#9aa0a6' }}>
                      ID: {app.id}
                    </span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <motion.button
                    onClick={() => setEditingApp(app)}
                    className="btn btn-secondary"
                    style={{ padding: '6px' }}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Edit size={16} />
                  </motion.button>
                  <motion.button
                    onClick={() => handleDeleteApp(app.id)}
                    className="btn btn-danger"
                    style={{ padding: '6px' }}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Trash2 size={16} />
                  </motion.button>
                </div>
              </div>

              {/* API Key Section */}
              <div style={{ 
                padding: '12px', 
                backgroundColor: '#1f2937', 
                borderRadius: '8px', 
                marginBottom: '12px',
                border: '1px solid #374151'
              }}>
                <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '14px', fontWeight: '500', color: '#e0e0e0' }}>
                    API Key
                  </span>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button
                      onClick={() => toggleApiKeyVisibility(app.id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#9aa0a6',
                        padding: '4px'
                      }}
                      title={visibleApiKeys.has(app.id) ? 'Ocultar' : 'Mostrar'}
                    >
                      {visibleApiKeys.has(app.id) ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                    <button
                      onClick={() => copyToClipboard(app.api_key)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#9aa0a6',
                        padding: '4px'
                      }}
                      title="Copiar"
                    >
                      <Copy size={16} />
                    </button>
                    <button
                      onClick={() => handleRegenerateApiKey(app.id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#9aa0a6',
                        padding: '4px'
                      }}
                      title="Regenerar"
                    >
                      <Key size={16} />
                    </button>
                  </div>
                </div>
                <code style={{ 
                  fontSize: '12px', 
                  color: '#10b981',
                  fontFamily: 'monospace',
                  wordBreak: 'break-all',
                  display: 'block',
                  backgroundColor: '#111827',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #374151'
                }}>
                  {visibleApiKeys.has(app.id) 
                    ? app.api_key 
                    : '●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●'
                  }
                </code>
              </div>

              {/* Timestamps */}
              <div style={{ fontSize: '12px', color: '#9aa0a6' }}>
                <div style={{ marginBottom: '4px' }}>
                  <strong>Creada:</strong> {app.created_at ? formatDate(app.created_at) : 'N/A'}
                </div>
                {app.last_edit && (
                  <div>
                    <strong>Última edición:</strong> {formatDate(app.last_edit)}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AppsSection;
