import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { LayoutDashboard, Plus, Settings } from 'lucide-react';
import ProjectDashboard from './pages/ProjectDashboard';
import ProjectDetails from './pages/ProjectDetails';
import LiveTeamView from './pages/LiveTeamView';

function App() {
  return (
    <Router>
      <div className="app-container">
        {/* Sidebar Navigation */}
        <aside className="sidebar">
          <div style={{ marginBottom: '3rem' }}>
            <h2 style={{ fontSize: '1.4rem', background: 'var(--accent-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              IntakeEngine AI
            </h2>
            <p style={{ fontSize: '0.8rem', marginTop: '-0.5rem' }}>Architect Studio</p>
          </div>

          <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <Link to="/" className="btn btn-secondary" style={{ justifyContent: 'flex-start' }}>
              <LayoutDashboard size={18} />
              Dashboard
            </Link>
          </nav>
        </aside>

        {/* Main Workspace */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ProjectDashboard />} />
            <Route path="/project/:id" element={<ProjectDetails />} />
            <Route path="/project/:id/live" element={<LiveTeamView />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
