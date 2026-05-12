import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play, Save, CheckCircle } from 'lucide-react';
import { api } from '../api';
import ModelSelector from '../components/ModelSelector';

export default function ProjectDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [project, setProject] = useState(null);

    const [requirements, setRequirements] = useState('');
    const [pmGuidelines, setPmGuidelines] = useState('');
    const [architectGuidelines, setArchitectGuidelines] = useState('');
    const [systemsGuidelines, setSystemsGuidelines] = useState('');
    const [aiGuidelines, setAiGuidelines] = useState('');
    const [uxGuidelines, setUxGuidelines] = useState('');
    const [securityStandards, setSecurityStandards] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState(false);
    const [isDeploying, setIsDeploying] = useState(false);

    useEffect(() => {
        fetchProjectDetails();
    }, [id]);

    const fetchProjectDetails = async () => {
        try {
            const res = await api.get(`/api/v1/projects/${id}`);
            setProject(res.data);
            if (res.data.requirements && res.data.requirements.length > 0) {
                setRequirements(res.data.requirements[res.data.requirements.length - 1].content);
            }
            if (res.data.knowledge_base) {
                setPmGuidelines(res.data.knowledge_base.pm_guidelines || '');
                setArchitectGuidelines(res.data.knowledge_base.architect_guidelines || '');
                setSystemsGuidelines(res.data.knowledge_base.systems_guidelines || '');
                setAiGuidelines(res.data.knowledge_base.ai_guidelines || '');
                setUxGuidelines(res.data.knowledge_base.ux_guidelines || '');
                setSecurityStandards(res.data.knowledge_base.security_standards || '');
            }
        } catch (error) {
            console.error("Error fetching project", error);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await api.put(`/api/v1/projects/${id}/knowledge_base/`, {
                pm_guidelines: pmGuidelines,
                architect_guidelines: architectGuidelines,
                systems_guidelines: systemsGuidelines,
                ai_guidelines: aiGuidelines,
                ux_guidelines: uxGuidelines,
                security_standards: securityStandards
            });

            if (requirements.trim()) {
                await api.post(`/api/v1/projects/${id}/requirements/`, {
                    content: requirements
                });
            }

            setSaveSuccess(true);
            setTimeout(() => setSaveSuccess(false), 3000);
        } catch (error) {
            console.error("Error saving configurations", error);
        } finally {
            setIsSaving(false);
        }
    };

    const handleDeploy = async () => {
        await handleSave();
        setIsDeploying(true);
        try {
            const res = await api.post(`/api/v1/projects/${id}/runs`);
            navigate(`/project/${id}/live/${res.data.id}`);
        } catch (error) {
            console.error("Error running team", error);
            alert(error.response?.data?.detail || "Failed to start the AI team.");
            setIsDeploying(false);
        }
    };

    const handleToggleDiscovery = async (enabled) => {
        // Optimistic update for snappy UX; revert if the PUT fails
        const prev = project;
        setProject(p => p ? { ...p, discovery_enabled: enabled } : p);
        try {
            await api.put(`/api/v1/projects/${id}`, { discovery_enabled: enabled });
        } catch (error) {
            console.error("Failed to toggle discovery", error);
            setProject(prev);
            alert("Couldn't update the discovery setting. Please try again.");
        }
    };

    const handleModelChange = async (newModel) => {
        const prev = project;
        setProject(p => p ? { ...p, llm_model: newModel } : p);
        try {
            await api.put(`/api/v1/projects/${id}`, { llm_model: newModel });
        } catch (error) {
            console.error("Failed to update model", error);
            setProject(prev);
            alert("Couldn't update the model. Please try again.");
        }
    };

    if (!project) return <div>Loading...</div>;

    return (
        <div className="animate-fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '2rem' }}>Configure: {project.title}</h1>
                    <p>Provide the product requirements and update the agent handbooks before deploying the team.</p>
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button className="btn btn-secondary" onClick={handleSave} disabled={isSaving}>
                        {saveSuccess ? <CheckCircle size={18} color="var(--success)" /> : <Save size={18} />}
                        {isSaving ? 'Saving...' : saveSuccess ? 'Saved' : 'Save Config'}
                    </button>
                    <button className="btn btn-primary" onClick={handleDeploy} disabled={isDeploying}>
                        <Play size={18} />
                        {isDeploying ? 'Starting Run...' : 'Start Run'}
                    </button>
                </div>
            </div>

            <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
                    <input
                        type="checkbox"
                        checked={project.discovery_enabled !== false}
                        onChange={(e) => handleToggleDiscovery(e.target.checked)}
                        style={{ marginTop: '0.25rem', cursor: 'pointer' }}
                    />
                    <span>
                        <span style={{ fontWeight: 500 }}>Run market discovery before requirements</span>
                        <span style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                            Adds a Market Researcher agent that produces ICP, market sizing (TAM/SAM/SOM), competitive landscape, and an opportunity tree before the PM decomposes requirements. Adds ~2–3 minutes per run.
                        </span>
                    </span>
                </label>
                <div>
                    <ModelSelector
                        value={project.llm_model || null}
                        onChange={handleModelChange}
                        label="LLM model"
                    />
                </div>
            </div>

            {/* Run History */}
            {project.crew_runs && project.crew_runs.length > 0 && (
                <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: 'var(--accent-primary)' }}>Run History</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {project.crew_runs.map(run => (
                            <div
                                key={run.id}
                                onClick={() => navigate(`/project/${id}/live/${run.id}`)}
                                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', borderRadius: 'var(--radius-sm)', background: 'var(--bg-tertiary)', cursor: 'pointer' }}
                            >
                                <span style={{ fontSize: '0.85rem' }}>Run #{run.id}</span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                        {run.started_at ? new Date(run.started_at).toLocaleString() : 'Queued'}
                                    </span>
                                    <span className={`badge badge-${run.status}`}>{run.status}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                {/* Requirements Section */}
                <div className="glass-panel" style={{ padding: '2rem' }}>
                    <h2 style={{ fontSize: '1.4rem', color: 'var(--accent-primary)', marginBottom: '1.5rem' }}>Product Requirements</h2>
                    <div className="form-group">
                        <label className="form-label">What are we building?</label>
                        <p style={{ fontSize: '0.85rem', marginTop: '-0.3rem' }}>The Lead Product Manager will break this down into atomic features.</p>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '400px' }}
                            placeholder="E.g. We need an application that allows users to search for..."
                            value={requirements}
                            onChange={(e) => setRequirements(e.target.value)}
                        />
                    </div>
                </div>

                {/* Knowledge Base Section */}
                <div className="glass-panel" style={{ padding: '2rem' }}>
                    <h2 style={{ fontSize: '1.4rem', color: '#9066cc', marginBottom: '1.5rem' }}>Agent Handbooks</h2>

                    <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                        <label className="form-label">Product Manager Guidelines</label>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '100px' }}
                            placeholder="Rules for mapping features and preventing scope creep..."
                            value={pmGuidelines}
                            onChange={(e) => setPmGuidelines(e.target.value)}
                        />
                    </div>

                    <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                        <label className="form-label">Lead Architect Guidelines</label>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '100px' }}
                            placeholder="Preferred tech stacks, system design patterns..."
                            value={architectGuidelines}
                            onChange={(e) => setArchitectGuidelines(e.target.value)}
                        />
                    </div>

                    <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                        <label className="form-label">Systems Engineer Guidelines</label>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '100px' }}
                            placeholder="Database preferences, CI/CD pipelines, DevOps constraints..."
                            value={systemsGuidelines}
                            onChange={(e) => setSystemsGuidelines(e.target.value)}
                        />
                    </div>

                    <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                        <label className="form-label">AI Specialist Guidelines</label>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '100px' }}
                            placeholder="Preferred LLMs, prompt engineering tactics, RAG strategies..."
                            value={aiGuidelines}
                            onChange={(e) => setAiGuidelines(e.target.value)}
                        />
                    </div>

                    <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                        <label className="form-label">UX/UI Guidelines</label>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '100px' }}
                            placeholder="Must use Material Design, mobile-first styling..."
                            value={uxGuidelines}
                            onChange={(e) => setUxGuidelines(e.target.value)}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Security Standards (CISO)</label>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '100px' }}
                            placeholder="Zero-Trust architecture, PII anonymization..."
                            value={securityStandards}
                            onChange={(e) => setSecurityStandards(e.target.value)}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
