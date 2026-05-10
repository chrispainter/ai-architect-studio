import React, { useState, useMemo } from 'react';
import { Monitor, Smartphone, ExternalLink, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

/**
 * Renders the UX agent's Stitch-generated design output.
 *
 * Expects `output.output_content` to be a JSON string of shape:
 *   {
 *     stitch_project_id: string,
 *     screens: [{name, description, html_url, screenshot_url}],
 *     theme: {primary_color, accent_color, font_family, notes},
 *     design_rationale: string
 *   }
 *
 * Falls back to rendering as markdown if parsing fails — early Stitch runs
 * can be inconsistent and we don't want the page to blow up.
 */
export default function DesignPreview({ output }) {
    const parsed = useMemo(() => tryParseStitchPayload(output.output_content), [output.output_content]);
    const [activeScreenIdx, setActiveScreenIdx] = useState(0);
    const [viewport, setViewport] = useState('desktop');
    const [iframeFailed, setIframeFailed] = useState(false);

    if (!parsed) {
        return (
            <div>
                <ParseFallbackBanner />
                <div className="markdown-body">
                    <ReactMarkdown>{output.output_content}</ReactMarkdown>
                </div>
            </div>
        );
    }

    const screens = parsed.screens || [];
    const screen = screens[activeScreenIdx];
    const theme = parsed.theme || {};

    return (
        <div>
            {parsed.design_rationale && (
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem', lineHeight: 1.6 }}>
                    {parsed.design_rationale}
                </p>
            )}

            {screens.length > 1 && (
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                    {screens.map((s, idx) => (
                        <button
                            key={idx}
                            onClick={() => { setActiveScreenIdx(idx); setIframeFailed(false); }}
                            style={{
                                padding: '0.5rem 1rem',
                                borderRadius: 'var(--radius-sm)',
                                border: '1px solid var(--glass-border)',
                                background: idx === activeScreenIdx ? 'var(--accent-primary)' : 'transparent',
                                color: idx === activeScreenIdx ? '#fff' : 'var(--text-secondary)',
                                cursor: 'pointer',
                                fontSize: '0.85rem',
                            }}
                        >
                            {s.name || `Screen ${idx + 1}`}
                        </button>
                    ))}
                </div>
            )}

            {screen && (
                <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <div>
                            {screen.description && (
                                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                    {screen.description}
                                </span>
                            )}
                        </div>
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                            <ViewportButton active={viewport === 'mobile'} onClick={() => setViewport('mobile')} icon={<Smartphone size={14} />} label="Mobile" />
                            <ViewportButton active={viewport === 'desktop'} onClick={() => setViewport('desktop')} icon={<Monitor size={14} />} label="Desktop" />
                            {screen.html_url && (
                                <a
                                    href={screen.html_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                        padding: '0.4rem 0.75rem',
                                        borderRadius: 'var(--radius-sm)',
                                        border: '1px solid var(--glass-border)',
                                        color: 'var(--text-secondary)',
                                        fontSize: '0.8rem',
                                        textDecoration: 'none',
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: '0.4rem',
                                    }}
                                >
                                    <ExternalLink size={12} /> Open
                                </a>
                            )}
                        </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'center', background: 'rgba(0,0,0,0.25)', borderRadius: 'var(--radius-md)', padding: '1rem', minHeight: '400px' }}>
                        <ScreenViewer
                            key={`${activeScreenIdx}-${viewport}`}
                            screen={screen}
                            viewport={viewport}
                            iframeFailed={iframeFailed}
                            onIframeError={() => setIframeFailed(true)}
                        />
                    </div>
                </>
            )}

            {screens.length === 0 && (
                <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                    No screens were generated in this run.
                </p>
            )}

            {(theme.primary_color || theme.font_family) && (
                <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                    <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.9rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Design System
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center' }}>
                        {theme.primary_color && <ColorToken label="Primary" value={theme.primary_color} />}
                        {theme.accent_color && <ColorToken label="Accent" value={theme.accent_color} />}
                        {theme.font_family && (
                            <div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Font</div>
                                <div style={{ fontFamily: theme.font_family, fontSize: '0.95rem' }}>{theme.font_family}</div>
                            </div>
                        )}
                    </div>
                    {theme.notes && (
                        <p style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                            {theme.notes}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

function ScreenViewer({ screen, viewport, iframeFailed, onIframeError }) {
    const width = viewport === 'mobile' ? 375 : '100%';
    const maxWidth = viewport === 'mobile' ? 375 : 1280;
    const height = viewport === 'mobile' ? 667 : 720;

    if (iframeFailed && screen.screenshot_url) {
        return (
            <img
                src={screen.screenshot_url}
                alt={screen.name || 'Screen preview'}
                style={{ width, maxWidth: '100%', borderRadius: 'var(--radius-sm)', boxShadow: 'var(--shadow-sm)' }}
            />
        );
    }

    if (screen.html_url) {
        return (
            <iframe
                title={screen.name || 'Stitch screen preview'}
                src={screen.html_url}
                sandbox="allow-scripts allow-same-origin"
                onError={onIframeError}
                style={{
                    width,
                    maxWidth,
                    height,
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-sm)',
                    background: '#fff',
                }}
            />
        );
    }

    if (screen.screenshot_url) {
        return (
            <img
                src={screen.screenshot_url}
                alt={screen.name || 'Screen preview'}
                style={{ width, maxWidth: '100%', borderRadius: 'var(--radius-sm)' }}
            />
        );
    }

    return (
        <div style={{ color: 'var(--text-secondary)', padding: '2rem' }}>
            No preview asset available for this screen.
        </div>
    );
}

function ViewportButton({ active, onClick, icon, label }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: '0.4rem 0.75rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--glass-border)',
                background: active ? 'var(--accent-primary)' : 'transparent',
                color: active ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.8rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
            }}
        >
            {icon} {label}
        </button>
    );
}

function ColorToken({ label, value }) {
    return (
        <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>{label}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: 24, height: 24, borderRadius: 6, background: value, border: '1px solid var(--glass-border)' }} />
                <code style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{value}</code>
            </div>
        </div>
    );
}

function ParseFallbackBanner() {
    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            background: 'rgba(255, 200, 0, 0.08)',
            border: '1px solid rgba(255, 200, 0, 0.25)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
        }}>
            <AlertTriangle size={14} />
            Stitch returned a non-JSON response — showing raw output.
        </div>
    );
}

function tryParseStitchPayload(content) {
    if (!content || typeof content !== 'string') return null;
    let candidate = content.trim();
    const fenceMatch = candidate.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    if (fenceMatch) candidate = fenceMatch[1].trim();
    try {
        const obj = JSON.parse(candidate);
        if (obj && typeof obj === 'object' && (Array.isArray(obj.screens) || obj.stitch_project_id)) {
            return obj;
        }
    } catch {
        // fall through
    }
    return null;
}
