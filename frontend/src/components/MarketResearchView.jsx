import React, { useState, useMemo } from 'react';
import { ChevronRight, ChevronDown, ExternalLink, AlertTriangle, Users, TrendingUp, Swords, GitBranch, Lightbulb, Link as LinkIcon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

/**
 * Renders the Market Discovery Researcher's structured discovery brief.
 *
 * Expects `output.output_content` to be a JSON string of the shape produced by
 * the market_research_task in backend/crew_runner.py — ICP/JTBD, market sizing
 * (TAM/SAM/SOM), competitive landscape, an opportunity tree, key insights for
 * architecture, and citations.
 *
 * Falls back to markdown render if JSON parsing fails so the user always sees
 * something (LLM occasionally wraps JSON in fences or adds prose).
 */
export default function MarketResearchView({ output }) {
    const parsed = useMemo(() => tryParseResearchPayload(output.output_content), [output.output_content]);

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

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {parsed.key_insights_for_architecture?.length > 0 && (
                <Section icon={<Lightbulb size={16} />} title="Key insights for the team">
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: 1.7 }}>
                        {parsed.key_insights_for_architecture.map((insight, i) => (
                            <li key={i} style={{ marginBottom: '0.5rem' }}>{insight}</li>
                        ))}
                    </ul>
                </Section>
            )}

            {parsed.icp && (
                <Section icon={<Users size={16} />} title="Ideal customer profile">
                    {parsed.icp.primary_persona && (
                        <Field label="Primary persona">
                            <p style={{ margin: 0, lineHeight: 1.6 }}>{parsed.icp.primary_persona}</p>
                        </Field>
                    )}
                    {parsed.icp.alternative_personas?.length > 0 && (
                        <Field label="Alternative personas">
                            <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: 1.6 }}>
                                {parsed.icp.alternative_personas.map((p, i) => (
                                    <li key={i} style={{ marginBottom: '0.5rem' }}>{p}</li>
                                ))}
                            </ul>
                        </Field>
                    )}
                    {parsed.icp.jobs_to_be_done?.length > 0 && (
                        <Field label="Jobs-to-be-done">
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {parsed.icp.jobs_to_be_done.map((j, i) => (
                                    <div key={i} style={{ background: 'rgba(0,0,0,0.2)', padding: '0.85rem 1rem', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--accent-primary)' }}>
                                        <div style={{ fontWeight: 600, marginBottom: '0.4rem' }}>{j.job}</div>
                                        {j.current_alternative && (
                                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                                                <span style={{ opacity: 0.7 }}>Today they: </span>{j.current_alternative}
                                            </div>
                                        )}
                                        {j.trigger && (
                                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                                <span style={{ opacity: 0.7 }}>Switches when: </span>{j.trigger}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </Field>
                    )}
                </Section>
            )}

            {parsed.market_sizing && hasAnyValue(parsed.market_sizing) && (
                <Section icon={<TrendingUp size={16} />} title="Market sizing">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                        {['tam', 'sam', 'som', 'growth_rate'].map(key => parsed.market_sizing[key] && (
                            <SizingCard key={key} label={prettyLabel(key)} value={parsed.market_sizing[key]} />
                        ))}
                    </div>
                    {parsed.market_sizing.notes && (
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                            {parsed.market_sizing.notes}
                        </div>
                    )}
                </Section>
            )}

            {parsed.competitive_landscape?.length > 0 && (
                <Section icon={<Swords size={16} />} title="Competitive landscape">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                        {parsed.competitive_landscape.map((c, i) => (
                            <CompetitorCard key={i} competitor={c} />
                        ))}
                    </div>
                </Section>
            )}

            {parsed.opportunity_tree && (
                <Section icon={<GitBranch size={16} />} title="Opportunity tree">
                    {parsed.opportunity_tree.outcome && (
                        <div style={{ padding: '0.85rem 1rem', background: 'linear-gradient(90deg, rgba(94,106,210,0.15), rgba(94,106,210,0.05))', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', borderLeft: '3px solid var(--accent-primary)' }}>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Outcome</div>
                            <div style={{ fontWeight: 500 }}>{parsed.opportunity_tree.outcome}</div>
                        </div>
                    )}
                    {parsed.opportunity_tree.opportunities?.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {parsed.opportunity_tree.opportunities.map((opp, i) => (
                                <OpportunityRow key={i} opportunity={opp} defaultOpen={i === 0} />
                            ))}
                        </div>
                    )}
                </Section>
            )}

            {parsed.citations?.length > 0 && (
                <Section icon={<LinkIcon size={16} />} title="Sources">
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', listStyle: 'none' }}>
                        {parsed.citations.map((url, i) => (
                            <li key={i} style={{ marginBottom: '0.35rem', fontSize: '0.85rem' }}>
                                <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-primary)', textDecoration: 'none', wordBreak: 'break-all' }}>
                                    {url}
                                </a>
                            </li>
                        ))}
                    </ul>
                </Section>
            )}
        </div>
    );
}

function Section({ icon, title, children }) {
    return (
        <div>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', marginBottom: '0.85rem' }}>
                {icon} {title}
            </h3>
            {children}
        </div>
    );
}

function Field({ label, children }) {
    return (
        <div style={{ marginBottom: '1.1rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>{label}</div>
            {children}
        </div>
    );
}

function SizingCard({ label, value }) {
    return (
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.35rem' }}>{label}</div>
            <div style={{ fontSize: '0.9rem', lineHeight: 1.4 }}>{value}</div>
        </div>
    );
}

function CompetitorCard({ competitor }) {
    return (
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.85rem 1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.5rem' }}>
                <div style={{ fontWeight: 600 }}>{competitor.name}</div>
                {competitor.url && (
                    <a href={competitor.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-primary)', fontSize: '0.75rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                        <ExternalLink size={11} />
                    </a>
                )}
            </div>
            {competitor.positioning && (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', lineHeight: 1.45 }}>
                    {competitor.positioning}
                </div>
            )}
            {competitor.weakness && (
                <div style={{ fontSize: '0.85rem', lineHeight: 1.45 }}>
                    <span style={{ color: 'var(--text-secondary)', opacity: 0.7 }}>Weakness: </span>{competitor.weakness}
                </div>
            )}
        </div>
    );
}

function OpportunityRow({ opportunity, defaultOpen }) {
    const [open, setOpen] = useState(!!defaultOpen);
    return (
        <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)', overflow: 'hidden' }}>
            <button
                onClick={() => setOpen(o => !o)}
                style={{
                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                    width: '100%', padding: '0.75rem 1rem', textAlign: 'left',
                    background: 'transparent', border: 'none', cursor: 'pointer',
                    color: 'inherit', font: 'inherit',
                }}
            >
                {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                <span style={{ fontWeight: 500 }}>{opportunity.name}</span>
            </button>
            {open && (
                <div style={{ padding: '0 1rem 1rem 2.5rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    {opportunity.evidence && (
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: 1.5 }}>
                            <span style={{ opacity: 0.7, fontStyle: 'normal' }}>Evidence: </span>{opportunity.evidence}
                        </div>
                    )}
                    {opportunity.sub_opportunities?.length > 0 && (
                        <div>
                            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>Sub-opportunities</div>
                            <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: 1.6 }}>
                                {opportunity.sub_opportunities.map((s, i) => <li key={i}>{s}</li>)}
                            </ul>
                        </div>
                    )}
                    {opportunity.candidate_solutions?.length > 0 && (
                        <div>
                            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>Candidate solutions</div>
                            <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: 1.6 }}>
                                {opportunity.candidate_solutions.map((s, i) => <li key={i}>{s}</li>)}
                            </ul>
                        </div>
                    )}
                </div>
            )}
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
            Researcher returned a non-JSON response — showing raw output.
        </div>
    );
}

function prettyLabel(key) {
    const map = { tam: 'TAM', sam: 'SAM', som: 'SOM', growth_rate: 'Growth rate' };
    return map[key] || key;
}

function hasAnyValue(obj) {
    return obj && Object.values(obj).some(v => v && (typeof v !== 'string' || v.trim()));
}

function tryParseResearchPayload(content) {
    if (!content || typeof content !== 'string') return null;
    let candidate = content.trim();
    const fenceMatch = candidate.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    if (fenceMatch) candidate = fenceMatch[1].trim();
    try {
        const obj = JSON.parse(candidate);
        if (obj && typeof obj === 'object' && (obj.icp || obj.market_sizing || obj.opportunity_tree)) {
            return obj;
        }
    } catch {
        // fall through
    }
    return null;
}
