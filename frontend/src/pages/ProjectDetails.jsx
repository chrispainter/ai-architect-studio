import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play, Save, CheckCircle } from 'lucide-react';
import { api } from '../api';

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
            const res = await api.get(`/projects/${id}`);
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
            // Save Knowledge Base
            await api.put(`/projects/${id}/knowledge_base/`, {
                pm_guidelines: pmGuidelines,
                architect_guidelines: architectGuidelines,
                systems_guidelines: systemsGuidelines,
                ai_guidelines: aiGuidelines,
                ux_guidelines: uxGuidelines,
                security_standards: securityStandards
            });

            // Save Requirement
            if (requirements.trim()) {
                await api.post(`/projects/${id}/requirements/`, {
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
            await api.post(`/projects/${id}/run`);
            navigate(`/project/${id}/live`);
        } catch (error) {
            console.error("Error running team", error);
            alert("Failed to start the AI team.");
            setIsDeploying(false);
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
                        {isDeploying ? 'Deploying...' : 'Deploy Team'}
                    </button>
                </div>
            </div>

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
