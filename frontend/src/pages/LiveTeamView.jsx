import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api } from '../api';
import DesignPreview from '../components/DesignPreview';

// In dev, Vite proxy forwards /ws to backend. In prod, nginx does the same.
// So we connect relative to the current host.
const WS_URL = import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/^http/, 'ws')
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

export default function LiveTeamView() {
    const { id, runId } = useParams();
    const [project, setProject] = useState(null);
    const [outputs, setOutputs] = useState([]);
    const [runStatus, setRunStatus] = useState(null);
    const [error, setError] = useState(null);
    const wsRef = useRef(null);
    const reconnectTimer = useRef(null);

    // Initial data fetch
    useEffect(() => {
        fetchProjectData();
    }, [id, runId]);

    // WebSocket connection for real-time updates
    useEffect(() => {
        const targetRunId = runId || null;
        if (!targetRunId) return;

        function connect() {
            const ws = new WebSocket(`${WS_URL}/ws/runs/${targetRunId}`);
            wsRef.current = ws;

            ws.onopen = () => {
                // Send a ping to keep alive
                ws.send('ping');
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);

                    if (msg.type === 'agent_output') {
                        setOutputs(prev => [...prev, {
                            id: msg.output_id,
                            agent_name: msg.agent_name,
                            task_name: msg.task_name,
                            output_content: msg.output_content,
                            artifact_type: msg.artifact_type ?? null,
                        }]);
                    } else if (msg.type === 'status') {
                        setRunStatus(msg.status);
                        if (msg.status === 'error') {
                            setError(msg.error || 'An error occurred');
                        }
                        // Refresh project status
                        fetchProjectData();
                    }
                } catch (e) {
                    // ignore non-JSON messages
                }
            };

            ws.onclose = () => {
                // Reconnect if the run is still active
                if (runStatus === 'running' || runStatus === 'queued') {
                    reconnectTimer.current = setTimeout(connect, 3000);
                }
            };
        }

        connect();

        // Keep-alive ping every 30s
        const pingInterval = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send('ping');
            }
        }, 30000);

        return () => {
            clearInterval(pingInterval);
            clearTimeout(reconnectTimer.current);
            wsRef.current?.close();
        };
    }, [runId]);

    // Fallback polling for when WebSocket isn't available or run was started before page load
    useEffect(() => {
        if (runStatus === 'completed' || runStatus === 'error') return;

        const interval = setInterval(fetchProjectData, 8000);
        return () => clearInterval(interval);
    }, [id, runId, runStatus]);

    const fetchProjectData = async () => {
        try {
            const projRes = await api.get(`/api/v1/projects/${id}`);
            setProject(projRes.data);

            // Determine which run to show
            const targetRunId = runId
                ? parseInt(runId)
                : projRes.data.crew_runs?.[0]?.id;

            if (targetRunId) {
                const runRes = await api.get(`/api/v1/runs/${targetRunId}`);
                setRunStatus(runRes.data.status);
                if (runRes.data.agent_outputs?.length > 0) {
                    setOutputs(runRes.data.agent_outputs);
                }
                if (runRes.data.error_message) {
                    setError(runRes.data.error_message);
                }
            } else {
                // Legacy: fetch outputs directly
                const outRes = await api.get(`/api/v1/projects/${id}/outputs/`);
                setOutputs(outRes.data);
                setRunStatus(projRes.data.status);
                if (projRes.data.status === 'completed' || projRes.data.status.startsWith('error')) {
                    setRunStatus(projRes.data.status.startsWith('error') ? 'error' : projRes.data.status);
                }
            }
        } catch (err) {
            console.error("Error fetching live data", err);
        }
    };

    if (!project) return <div>Loading...</div>;

    const isActive = runStatus === 'running' || runStatus === 'queued';
    const isError = runStatus === 'error' || project.status?.startsWith('error');
    const isComplete = runStatus === 'completed';
    const displayStatus = runStatus || project.status;

    return (
        <div className="animate-fade-in">
            <div style={{ marginBottom: '2rem' }}>
                <Link to={`/project/${id}`} style={{ color: 'var(--text-secondary)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <ArrowLeft size={16} /> Back to Project
                </Link>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 style={{ fontSize: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            Team Output: {project.title}
                        </h1>
                        {runId && <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>Run #{runId}</p>}
                    </div>
                    <div className={`badge badge-${isError ? 'error' : isComplete ? 'completed' : isActive ? 'running' : 'draft'}`} style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}>
                        {isActive && <RefreshCw size={14} className="spin" style={{ marginRight: '0.5rem', display: 'inline' }} />}
                        {isComplete && <CheckCircle size={14} style={{ marginRight: '0.5rem', display: 'inline' }} />}
                        {isError && <AlertCircle size={14} style={{ marginRight: '0.5rem', display: 'inline' }} />}
                        Status: {(displayStatus || 'unknown').toUpperCase()}
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes spin { 100% { transform: rotate(360deg); } }
                .spin { animation: spin 2s linear infinite; }
            `}</style>

            {error && (
                <div style={{ background: 'rgba(255, 59, 48, 0.1)', border: '1px solid rgba(255, 59, 48, 0.3)', borderRadius: 'var(--radius-md)', padding: '1.5rem', marginBottom: '2rem' }}>
                    <h3 style={{ color: 'var(--error)', marginBottom: '0.5rem' }}>Error</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{error}</p>
                </div>
            )}

            {outputs.length === 0 && isActive ? (
                <div className="glass-panel" style={{ padding: '4rem', textAlign: 'center' }}>
                    <RefreshCw size={48} className="spin" color="var(--accent-primary)" style={{ margin: '0 auto 1.5rem' }} />
                    <h3>The AI Team is hard at work...</h3>
                    <p>Agents are thinking and reading your knowledge base. The first output may take 1-3 minutes.</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    {outputs.map((output, idx) => (
                        <div key={output.id || idx} className="glass-panel" style={{ padding: '2rem', borderLeft: '4px solid var(--accent-primary)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
                                <h3 style={{ margin: 0, color: '#a4b1fa' }}>{output.agent_name}</h3>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    Task: {output.task_name}
                                </span>
                            </div>
                            {output.artifact_type === 'stitch_design' ? (
                                <DesignPreview output={output} />
                            ) : (
                                <div className="markdown-body">
                                    <ReactMarkdown>{output.output_content}</ReactMarkdown>
                                </div>
                            )}
                        </div>
                    ))}

                    {isActive && (
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
