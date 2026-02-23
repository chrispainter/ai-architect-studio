import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, CheckCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api } from '../api';

export default function LiveTeamView() {
    const { id } = useParams();
    const [project, setProject] = useState(null);
    const [outputs, setOutputs] = useState([]);
    const [isPolling, setIsPolling] = useState(true);

    useEffect(() => {
        fetchProjectData();
        const interval = setInterval(() => {
            if (isPolling) {
                fetchProjectData();
            }
        }, 5000); // Poll every 5 seconds

        return () => clearInterval(interval);
    }, [id, isPolling]);

    const fetchProjectData = async () => {
        try {
            const projRes = await api.get(`/projects/${id}`);
            const outRes = await api.get(`/projects/${id}/outputs/`);

            setProject(projRes.data);
            setOutputs(outRes.data);

            if (projRes.data.status === 'completed' || projRes.data.status.startsWith('error')) {
                setIsPolling(false);
            }
        } catch (error) {
            console.error("Error fetching live data", error);
        }
    };

    if (!project) return <div>Loading...</div>;

    return (
        <div className="animate-fade-in">
            <div style={{ marginBottom: '2rem' }}>
                <Link to="/" style={{ color: 'var(--text-secondary)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <ArrowLeft size={16} /> Back to Dashboard
                </Link>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 style={{ fontSize: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            Team Output: {project.title}
                        </h1>
                    </div>
                    <div className={`badge badge-${project.status.toLowerCase()}`} style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}>
                        {project.status === 'running' && <RefreshCw size={14} className="spin" style={{ marginRight: '0.5rem', display: 'inline' }} />}
                        {project.status === 'completed' && <CheckCircle size={14} style={{ marginRight: '0.5rem', display: 'inline' }} />}
                        Status: {project.status.toUpperCase()}
                    </div>
                </div>
            </div>

            <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .spin { animation: spin 2s linear infinite; }
      `}</style>

            {outputs.length === 0 ? (
                <div className="glass-panel" style={{ padding: '4rem', textAlign: 'center' }}>
                    <RefreshCw size={48} className="spin" color="var(--accent-primary)" style={{ margin: '0 auto 1.5rem' }} />
                    <h3>The AI Team is hard at work...</h3>
                    <p>Agents are thinking and reading your knowledge base. The first output may take 1-3 minutes.</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    {outputs.map((output, idx) => (
                        <div key={idx} className="glass-panel" style={{ padding: '2rem', borderLeft: '4px solid var(--accent-primary)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
                                <h3 style={{ margin: 0, color: '#a4b1fa' }}>{output.agent_name}</h3>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    Task: {output.task_name}
                                </span>
                            </div>
                            <div className="markdown-body">
                                <ReactMarkdown>{output.output_content}</ReactMarkdown>
                            </div>
                        </div>
                    ))}

                    {project.status === 'running' && (
                        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                            <RefreshCw size={24} className="spin" style={{ margin: '0 auto 1rem' }} />
                            <p>Waiting for the next agent to finish...</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
