import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { LayoutDashboard, LogOut } from 'lucide-react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import ProjectDashboard from './pages/ProjectDashboard';
import ProjectDetails from './pages/ProjectDetails';
import LiveTeamView from './pages/LiveTeamView';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div style={{ marginBottom: '3rem' }}>
          <h2 style={{ fontSize: '1.4rem', background: 'var(--accent-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            AI Architect Studio
          </h2>
          <p style={{ fontSize: '0.8rem', marginTop: '-0.5rem' }}>Product Development Platform</p>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
          <Link to="/" className="btn btn-secondary" style={{ justifyContent: 'flex-start' }}>
            <LayoutDashboard size={18} />
            Dashboard
          </Link>
        </nav>

        {user && (
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              {user.full_name || user.email}
            </p>
            <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'flex-start', fontSize: '0.85rem' }} onClick={logout}>
              <LogOut size={16} />
              Sign Out
            </button>
          </div>
        )}
      </aside>

      {/* Main Workspace */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<ProjectDashboard />} />
          <Route path="/project/:id" element={<ProjectDetails />} />
          <Route path="/project/:id/live" element={<LiveTeamView />} />
          <Route path="/project/:id/live/:runId" element={<LiveTeamView />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
