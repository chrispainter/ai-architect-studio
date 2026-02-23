import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, FolderGit2, ArrowRight } from 'lucide-react';
import { api } from '../api';

export default function ProjectDashboard() {
    const [projects, setProjects] = useState([]);
    const [isCreating, setIsCreating] = useState(false);
    const [newTitle, setNewTitle] = useState('');
    const [newDesc, setNewDesc] = useState('');
    const [newGithub, setNewGithub] = useState('');

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const res = await api.get('/projects/');
            setProjects(res.data);
        } catch (error) {
            console.error("Failed to fetch projects", error);
        }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!newTitle.trim()) return;
        try {
            await api.post('/projects/', { title: newTitle, description: newDesc, github_url: newGithub });
            setNewTitle('');
            setNewDesc('');
            setNewGithub('');
            setIsCreating(false);
            fetchProjects();
        } catch (error) {
            console.error("Failed to create project", error);
        }
    };

    return (
        <div className="animate-fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
                <div>
                    <h1>Active Products</h1>
                    <p>Manage your AI development team instances and ideation sessions.</p>
                </div>
                <button className="btn btn-primary" onClick={() => setIsCreating(true)}>
                    <Plus size={18} /> New Product
                </button>
            </div>

            {isCreating && (
                <div className="card" style={{ marginBottom: '2rem' }}>
                    <h3 className="card-title">Initialize New Product</h3>
                    <form onSubmit={handleCreate}>
                        <div className="form-group">
                            <label className="form-label">Product Name</label>
                            <input
                                type="text"
                                className="form-input"
                                placeholder="e.g. AI Amenities Map"
                                value={newTitle}
                                onChange={(e) => setNewTitle(e.target.value)}
                                autoFocus
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Brief Description</label>
                            <input
                                type="text"
                                className="form-input"
                                placeholder="A short tagline for the team"
                                value={newDesc}
                                onChange={(e) => setNewDesc(e.target.value)}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">GitHub Repository URL (Optional)</label>
                            <input
                                type="url"
                                className="form-input"
                                placeholder="https://github.com/username/repo"
                                value={newGithub}
                                onChange={(e) => setNewGithub(e.target.value)}
                            />
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>If provided, agents will analyze this codebase first. Otherwise, they will build an architecture from scratch.</p>
                        </div>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <button type="submit" className="btn btn-primary">Create Workspace</button>
                            <button type="button" className="btn btn-secondary" onClick={() => setIsCreating(false)}>Cancel</button>
                        </div>
                    </form>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
                {projects.length === 0 && !isCreating ? (
                    <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', gridColumn: '1 / -1' }}>
                        <FolderGit2 size={48} color="var(--text-secondary)" style={{ margin: '0 auto 1rem' }} />
                        <h3 style={{ marginBottom: '0.5rem' }}>No Products Yet</h3>
                        <p>Create your first product to spin up an AI architect team.</p>
                    </div>
                ) : (
                    projects.map(project => (
                        <div key={project.id} className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                                <h3 className="card-title" style={{ margin: 0 }}>{project.title}</h3>
                                <span className={`badge badge-${project.status.toLowerCase()}`}>
                                    {project.status}
                                </span>
                            </div>
                            <p style={{ flex: 1 }}>{project.description || 'No description provided.'}</p>

                            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem', marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
                                {project.status === 'running' || project.status === 'completed' ? (
                                    <Link to={`/project/${project.id}/live`} className="btn btn-secondary" style={{ width: '100%' }}>
                                        View Team Output <ArrowRight size={16} />
                                    </Link>
                                ) : (
                                    <Link to={`/project/${project.id}`} className="btn btn-secondary" style={{ width: '100%' }}>
                                        Configure Team <ArrowRight size={16} />
                                    </Link>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
