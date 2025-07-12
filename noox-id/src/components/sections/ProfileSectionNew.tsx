import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Shield, Clock, Smartphone, RefreshCw, Upload } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { UserService } from '../../services/userService';
import { AppService } from '../../services/appService';
import type { User as UserType, App } from '../../services/api';

interface ProfileSectionProps {
  user: UserType;
}

const ProfileSection: React.FC<ProfileSectionProps> = ({ user }) => {
  const [apps, setApps] = useState<App[]>([]);
  const [isLoadingApps, setIsLoadingApps] = useState(true);
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
  const [profileData, setProfileData] = useState({
    firstname: user.firstname || '',
    lastname: user.lastname || '',
    email: user.email || ''
  });
  
  const { refreshProfile } = useAuth();

  useEffect(() => {
    loadUserApps();
  }, []);

  const loadUserApps = async () => {
    try {
      setIsLoadingApps(true);
      const response = await AppService.getUserApps();
      if (response.success && response.data) {
        setApps(response.data.apps || []);
      }
    } catch (error) {
      console.error('Error loading apps:', error);
    } finally {
      setIsLoadingApps(false);
    }
  };

  const handleUpdateProfile = async () => {
    try {
      setIsUpdatingProfile(true);
      const response = await UserService.updateProfile(profileData);
      if (response.success) {
        await refreshProfile();
        // Show success message
      }
    } catch (error) {
      console.error('Error updating profile:', error);
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Convert to base64
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64String = reader.result as string;
        const response = await UserService.uploadFaceImage(base64String);
        if (response.success) {
          await refreshProfile();
          // Show success message
        }
      } catch (error) {
        console.error('Error uploading image:', error);
      }
    };
    reader.readAsDataURL(file);
  };

  const stats = [
    { label: 'Aplicaciones vinculadas', value: apps.length.toString(), icon: Smartphone, isLoading: isLoadingApps },
    { label: 'Último acceso', value: user.updated_at ? new Date(user.updated_at).toLocaleDateString() : 'N/A', icon: Clock },
    { label: 'ID de Usuario', value: user.id?.toString() || 'N/A', icon: User },
    { label: 'Estado de verificación', value: user.verified ? 'Verificado' : 'Pendiente', icon: Shield }
  ];

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div>
      <div className="header">
        <h1 className="header-title">Perfil de Usuario</h1>
        <div className="user-info">
          <div className="user-avatar" style={{ position: 'relative' }}>
            {user.firstname ? user.firstname.charAt(0).toUpperCase() : 'U'}
            <input
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              style={{ display: 'none' }}
              id="avatar-upload"
            />
            <label
              htmlFor="avatar-upload"
              style={{
                position: 'absolute',
                bottom: '-5px',
                right: '-5px',
                width: '20px',
                height: '20px',
                backgroundColor: '#4285f4',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                border: '2px solid #1a1a1a'
              }}
            >
              <Upload size={10} color="white" />
            </label>
          </div>
          <div>
            <div style={{ fontWeight: '500' }}>
              {user.firstname} {user.lastname}
            </div>
            <div style={{ fontSize: '14px', color: '#9aa0a6' }}>
              {user.email}
            </div>
            <div style={{ fontSize: '12px', color: '#6b7280' }}>
              ID: {user.id}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px', marginBottom: '40px' }}>
        {stats.map((stat, index) => (
          <motion.div
            key={index}
            className="card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            whileHover={{ scale: 1.02 }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ 
                width: '48px', 
                height: '48px', 
                background: 'linear-gradient(135deg, #4285f4, #34a853)',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white'
              }}>
                {stat.isLoading ? (
                  <RefreshCw size={24} className="animate-spin" />
                ) : (
                  <stat.icon size={24} />
                )}
              </div>
              <div>
                <div style={{ fontSize: '24px', fontWeight: '600', color: '#ffffff' }}>
                  {stat.isLoading ? '...' : stat.value}
                </div>
                <div style={{ fontSize: '14px', color: '#9aa0a6' }}>
                  {stat.label}
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Profile Update Form */}
      <motion.div
        className="card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        style={{ marginBottom: '20px' }}
      >
        <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#ffffff', marginBottom: '16px' }}>
          Información Personal
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', color: '#e0e0e0', fontSize: '14px' }}>
              Nombre
            </label>
            <input
              type="text"
              value={profileData.firstname}
              onChange={(e) => setProfileData(prev => ({ ...prev, firstname: e.target.value }))}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #374151',
                borderRadius: '8px',
                backgroundColor: '#1f2937',
                color: '#ffffff',
                fontSize: '16px'
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', color: '#e0e0e0', fontSize: '14px' }}>
              Apellido
            </label>
            <input
              type="text"
              value={profileData.lastname}
              onChange={(e) => setProfileData(prev => ({ ...prev, lastname: e.target.value }))}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #374151',
                borderRadius: '8px',
                backgroundColor: '#1f2937',
                color: '#ffffff',
                fontSize: '16px'
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', color: '#e0e0e0', fontSize: '14px' }}>
              Email
            </label>
            <input
              type="email"
              value={profileData.email}
              onChange={(e) => setProfileData(prev => ({ ...prev, email: e.target.value }))}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #374151',
                borderRadius: '8px',
                backgroundColor: '#1f2937',
                color: '#ffffff',
                fontSize: '16px'
              }}
            />
          </div>
        </div>
        <motion.button
          onClick={handleUpdateProfile}
          disabled={isUpdatingProfile}
          className="btn btn-primary"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          style={{ marginTop: '10px' }}
        >
          {isUpdatingProfile ? 'Actualizando...' : 'Actualizar Perfil'}
        </motion.button>
      </motion.div>

      {/* Account Status */}
      <motion.div
        className="card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
      >
        <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#ffffff', marginBottom: '16px' }}>
          Estado de la cuenta
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#e0e0e0' }}>Verificación por correo</span>
            <span style={{ 
              color: user.verified ? '#34a853' : '#ea4335', 
              fontWeight: '500' 
            }}>
              {user.verified ? '✓ Verificado' : '⚠ Pendiente'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#e0e0e0' }}>Imagen de perfil</span>
            <span style={{ 
              color: user.ProfilePickPath ? '#34a853' : '#ea4335', 
              fontWeight: '500' 
            }}>
              {user.ProfilePickPath ? '✓ Configurada' : '⚠ No configurada'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#e0e0e0' }}>Creación de cuenta</span>
            <span style={{ color: '#9aa0a6', fontSize: '14px' }}>
              {user.created_at ? formatDate(user.created_at) : 'N/A'}
            </span>
          </div>
          {user.updated_at && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#e0e0e0' }}>Última actualización</span>
              <span style={{ color: '#9aa0a6', fontSize: '14px' }}>
                {formatDate(user.updated_at)}
              </span>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default ProfileSection;
