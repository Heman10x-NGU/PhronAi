import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Login } from './pages/Login';
import { AgentCanvas } from './pages/AgentCanvas';

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--phronai-dark)]">
        <div className="text-center animate-fade-in">
          <div className="text-4xl font-bold gradient-text mb-4">PHRONAI</div>
          <div className="text-[var(--phronai-text-muted)]">Initializing agent...</div>
          <div className="mt-4 w-12 h-12 border-4 border-[var(--phronai-primary)] border-t-transparent rounded-full animate-spin mx-auto"></div>
        </div>
      </div>
    );
  }

  return user ? <AgentCanvas /> : <Login />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
