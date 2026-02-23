import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play, Save, CheckCircle } from 'lucide-react';
import { api } from '../api';

export default function ProjectDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [project, setProject] = useState(null);

    const [requirements, setRequirements] = useState('');
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
                    <h2 style={{ fontSize: '1.4rem', color: '#9066cc', marginBottom: '1.5rem' }}>Agent Knowledge Bases</h2>

                    <div className="form-group" style={{ marginBottom: '2rem' }}>
                        <label className="form-label">UX/UI Guidelines (Lead Designer Handbook)</label>
                        <p style={{ fontSize: '0.85rem', marginTop: '-0.3rem' }}>Mandatory aesthetic and usability rules.</p>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '150px' }}
                            placeholder="E.g. Must use Material Design, high contrast, mobile-first..."
                            value={uxGuidelines}
                            onChange={(e) => setUxGuidelines(e.target.value)}
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">Security Standards (CISO Handbook)</label>
                        <p style={{ fontSize: '0.85rem', marginTop: '-0.3rem' }}>Mandatory infrastructure and data privacy rules.</p>
                        <textarea
                            className="form-textarea"
                            style={{ minHeight: '150px' }}
                            placeholder="E.g. Zero-Trust architecture, PII anonymization required..."
                            value={securityStandards}
                            onChange={(e) => setSecurityStandards(e.target.value)}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
