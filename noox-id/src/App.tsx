import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LandingPage from './components/LandingPage';
import AuthPage from './components/AuthPage';
import Dashboard from './components/Dashboard';
import './styles/globals.css';

type AppState = 'landing' | 'auth' | 'dashboard';

function AppContent() {
  const [currentPage, setCurrentPage] = useState<AppState>('landing');
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  // Log para debugging
  console.log('App state:', { isAuthenticated, user: !!user, currentPage, isLoading });

  // Mostrar loading mientras se verifica la autenticación
  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        backgroundColor: '#0a0a0a'
      }}>
        <motion.div
          className="sidebar-logo"
          style={{ fontSize: '3rem' }}
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        >
          N
        </motion.div>
      </div>
    );
  }

  // Si el usuario está autenticado, mostrar dashboard
  if (isAuthenticated && user) {
    return (
      <motion.div
        key="dashboard"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Dashboard user={user} onLogout={logout} />
      </motion.div>
    );
  }

  const pageVariants = {
    initial: { opacity: 0, y: 20 },
    in: { opacity: 1, y: 0 },
    out: { opacity: 0, y: -20 }
  };

  const pageTransition: { type: 'tween'; ease: 'anticipate'; duration: number } = {
    type: 'tween',
    ease: 'anticipate',
    duration: 0.5
  };

  return (
    <AnimatePresence mode="wait">
      {currentPage === 'landing' && (
        <motion.div
          key="landing"
          initial="initial"
          animate="in"
          exit="out"
          variants={pageVariants}
          transition={pageTransition}
        >
          <LandingPage onTryNow={() => setCurrentPage('auth')} />
        </motion.div>
      )}
      
      {currentPage === 'auth' && (
        <motion.div
          key="auth"
          initial="initial"
          animate="in"
          exit="out"
          variants={pageVariants}
          transition={pageTransition}
        >
          <AuthPage onBack={() => setCurrentPage('landing')} />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;