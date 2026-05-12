import React, { useState, useEffect } from 'react';
import { api } from '../api';

/**
 * Dropdown for picking the LLM model used by the crew.
 *
 * Server-driven option list (GET /api/v1/models). When `value` is null/empty
 * the selector shows "Default" — which means the server's configured default
 * applies at run time. Users only override when they want a specific model.
 *
 * Cached at module level so navigating between Dashboard and Details doesn't
 * re-fetch every time.
 */
let cachedModels = null;
let cachedDefault = null;

export default function ModelSelector({ value, onChange, label = "LLM model", helpText }) {
    const [models, setModels] = useState(cachedModels || []);
    const [defaultModel, setDefaultModel] = useState(cachedDefault || '');

    useEffect(() => {
        if (cachedModels) return;
        api.get('/api/v1/models')
            .then(res => {
                cachedModels = res.data.models || [];
                cachedDefault = res.data.default || '';
                setModels(cachedModels);
                setDefaultModel(cachedDefault);
            })
            .catch(err => console.error("Failed to load model list", err));
    }, []);

    const current = value || '';
    const activeOption = models.find(m => m.value === current);

    return (
        <div>
            {label && (
                <label className="form-label" style={{ display: 'block', marginBottom: '0.4rem' }}>
                    {label}
                </label>
            )}
            <select
                className="form-input"
                value={current}
                onChange={(e) => onChange(e.target.value || null)}
                style={{ width: '100%', cursor: 'pointer' }}
            >
                <option value="">
                    Default{defaultModel ? ` (${defaultModel})` : ''}
                </option>
                {models.map(m => (
                    <option key={m.value} value={m.value}>
                        {m.label}{m.tier === 'experimental' ? ' — experimental' : ''}{m.tier === 'fast' ? ' — fast/cheap' : ''}
                    </option>
                ))}
            </select>
            {(activeOption?.description || helpText) && (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.4rem', lineHeight: 1.5 }}>
                    {activeOption?.description || helpText}
                </p>
            )}
        </div>
    );
}
