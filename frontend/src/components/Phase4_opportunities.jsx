import { useState, useEffect, useRef } from 'react'

const IMPACT_COLOR  = { High: 'var(--green)', Medium: 'var(--amber)', Low: 'var(--text-3)' }
const EFFORT_COLOR  = { Low: 'var(--green)',  Medium: 'var(--amber)', High: 'var(--red)' }
const MATURITY_MAP  = {
  Proven:       { label: 'Proven',       color: 'var(--green)' },
  Emerging:     { label: 'Emerging',     color: 'var(--amber)' },
  Experimental: { label: 'Experimental', color: 'var(--text-3)' },
}
const PILLAR_ICONS  = {
  'Sales & Marketing':       '◆',
  'Operations & Fulfillment':'◈',
  'Finance & Administration':'▣',
  'Cross-functional':        '⬡',
}

export default function Phase4_Opportunities({ api, getWsBase, session, participant, mode = 'participant', onComplete }) {
  const [step,        setStep]        = useState('loading')   // loading → reveal → detail
  const [result,      setResult]      = useState(null)        // full API response
  const [selected,    setSelected]    = useState(null)        // selected use case for detail
  const [error,       setError]       = useState(null)
  const [liveCount,   setLiveCount]   = useState(0)
  const [filter,      setFilter]      = useState('All')       // All | Quick Win | High Impact | Data Ready | <Tag>
  const wsRef = useRef(null)

  // ── WebSocket ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!session?.code) return
    let disposed = false
    const ws = new WebSocket(`${getWsBase()}/ws/${session.code}?participant_id=${participant?.id || 'host'}`)
    wsRef.current = ws
    ws.onopen = () => {
      if (disposed) ws.close()
    }
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'use_cases_ready') setLiveCount(msg.count)
      } catch {}
    }
    ws.onerror = () => {}
    return () => {
      disposed = true
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CLOSING) {
        ws.close()
      }
    }
  }, [session?.code])

  // ── Generate on mount ───────────────────────────────────────────────────
  useEffect(() => {
    generateOpportunities()
  }, [])

  const generateOpportunities = async () => {
    setStep('loading')
    setError(null)
    try {
      const data = await api('/phase/opportunities', {
        method: 'POST',
        body: JSON.stringify({ session_code: session.code }),
      })
      setResult(data)
      setStep('reveal')
    } catch (err) {
      setError(err.message || 'Could not generate use cases. Is the backend running?')
      setStep('error')
    }
  }

  // ── Filtered use cases ──────────────────────────────────────────────────
  const useCases = result?.use_cases || []
  const allTags  = [...new Set(useCases.flatMap(uc => uc.tags || []))].sort()

  const filtered = useCases.filter(uc => {
    if (filter === 'Quick Win')    return uc.quick_win
    if (filter === 'High Impact')  return uc.impact === 'High'
    if (filter === 'Data Ready')   return uc.data_ready
    if (allTags.includes(filter))  return uc.tags?.includes(filter)
    return true
  })

  const meta = result?.generation_metadata || {}
  const verif = result?.verification_summary || {}

  return (
    <div className="phase-shell fade-up">

      <div className="phase-header">
        <div className="phase-logo">◈ AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-dot pulse" />
          <span className="phase-label">Phase 4 — AI Opportunities</span>
        </div>
      </div>

      {/* ── LOADING ── */}
      {step === 'loading' && (
        <div className="phase-body">
          <div className="ai-thinking" style={{ paddingTop: 60 }}>
            <div className="thinking-dots">
              <span className="thinking-dot" />
              <span className="thinking-dot" style={{ animationDelay: '0.2s' }} />
              <span className="thinking-dot" style={{ animationDelay: '0.4s' }} />
            </div>
            <p className="thinking-label">Generating AI opportunities...</p>
            <div className="opp-loading-steps">
              {[
                'Reading your objectives and problem clusters',
                'Grounding use cases with real-world evidence',
                'Self-verifying quality and relevance',
                'Ranking by impact and data readiness',
              ].map((s, i) => (
                <div key={i} className="opp-loading-step" style={{ animationDelay: `${i * 0.8}s` }}>
                  <span className="opp-loading-dot" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── ERROR ── */}
      {step === 'error' && (
        <div className="phase-body">
          <div className="error-banner">⚠ {error}</div>
          <button className="btn btn-primary" onClick={generateOpportunities} style={{ marginTop: 16 }}>
            Retry
          </button>
        </div>
      )}

      {/* ── REVEAL ── */}
      {step === 'reveal' && result && (
        <>
          {/* Verification banner */}
          {verif.passed > 0 && (
            <div className="opp-verif-banner">
              <span className="opp-verif-icon">✓</span>
              <span className="opp-verif-text">
                {verif.passed} use cases passed self-verification
                {verif.rejected > 0 && ` · ${verif.rejected} rejected for low relevance`}
                {verif.quality_assessment && ` · ${verif.quality_assessment}`}
              </span>
            </div>
          )}

          {/* Generation metadata */}
          <div className="opp-meta-bar">
            <span className="opp-meta-item">
              <span className="opp-meta-val">{meta.candidates_generated || '—'}</span>
              <span className="opp-meta-lbl">generated</span>
            </span>
            <span className="opp-meta-sep">→</span>
            <span className="opp-meta-item">
              <span className="opp-meta-val">{meta.candidates_verified || '—'}</span>
              <span className="opp-meta-lbl">verified</span>
            </span>
            <span className="opp-meta-sep">→</span>
            <span className="opp-meta-item">
              <span className="opp-meta-val" style={{ color: 'var(--green)' }}>{useCases.length}</span>
              <span className="opp-meta-lbl">final</span>
            </span>
          </div>

          {/* Filter bar */}
          <div className="opp-filter-bar" style={{ flexWrap: 'wrap', gap: '6px' }}>
            {['All', 'Quick Win', 'High Impact', 'Data Ready', ...allTags].map(f => (
              <button
                key={f}
                className={`opp-filter-btn ${filter === f ? 'active' : ''}`}
                onClick={() => setFilter(f)}
                type="button"
                style={{ marginBottom: 4 }}
              >
                {f}
                <span className="opp-filter-count">
                  {f === 'All'         ? useCases.length
                  : f === 'Quick Win'  ? useCases.filter(u => u.quick_win).length
                  : f === 'High Impact'? useCases.filter(u => u.impact === 'High').length
                  : f === 'Data Ready' ? useCases.filter(u => u.data_ready).length
                  :                     useCases.filter(u => u.tags?.includes(f)).length}
                </span>
              </button>
            ))}
          </div>

          <div className="phase-body">
            <div className="opp-grid">
              {filtered.map((uc, i) => (
                <div
                  key={uc.id}
                  className={`opp-card fade-up ${selected?.id === uc.id ? 'opp-card-selected' : ''}`}
                  style={{ animationDelay: `${i * 0.05}s` }}
                  onClick={() => setSelected(selected?.id === uc.id ? null : uc)}
                >
                  {/* Card header */}
                  <div className="opp-card-header">
                    <span className="opp-pillar-icon">{PILLAR_ICONS[uc.pillar] || '◎'}</span>
                    <div className="opp-badges">
                      {uc.quick_win && <span className="badge badge-green">Quick win</span>}
                      {uc.data_ready && <span className="badge badge-accent">Data ready</span>}
                      {uc.adoption_maturity && (
                        <span className="badge badge-default" style={{ color: MATURITY_MAP[uc.adoption_maturity]?.color }}>
                          {MATURITY_MAP[uc.adoption_maturity]?.label || uc.adoption_maturity}
                        </span>
                      )}
                    </div>
                  </div>

                  <h3 className="opp-title">{uc.title}</h3>
                  <p className="opp-desc">{uc.description}</p>

                  {/* Impact / Effort / ROI */}
                  <div className="opp-metrics">
                    <div className="opp-metric">
                      <span className="opp-metric-lbl">Impact</span>
                      <span className="opp-metric-val" style={{ color: IMPACT_COLOR[uc.impact] }}>
                        {uc.impact}
                      </span>
                    </div>
                    <div className="opp-metric-div" />
                    <div className="opp-metric">
                      <span className="opp-metric-lbl">Effort</span>
                      <span className="opp-metric-val" style={{ color: EFFORT_COLOR[uc.effort] }}>
                        {uc.effort}
                      </span>
                    </div>
                    <div className="opp-metric-div" />
                    <div className="opp-metric">
                      <span className="opp-metric-lbl">ROI estimate</span>
                      <span className="opp-metric-val" style={{ fontSize: 11, color: 'var(--text)' }}>
                        {uc.estimated_roi}
                      </span>
                    </div>
                  </div>

                  {/* Source cluster tag */}
                  {uc.source_cluster && (
                    <div className="opp-source">
                      <span className="opp-source-lbl">↳ from</span>
                      <span className="opp-source-val">{uc.source_cluster}</span>
                    </div>
                  )}

                  {/* Expanded detail */}
                  {selected?.id === uc.id && (
                    <div className="opp-detail fade-up" onClick={e => e.stopPropagation()}>
                      {uc.real_world_evidence && (
                        <div className="opp-evidence">
                          <span className="opp-evidence-lbl">Real-world evidence</span>
                          <p className="opp-evidence-text">{uc.real_world_evidence}</p>
                        </div>
                      )}
                      {uc.risk_flag && (
                        <div className="opp-risk">
                          <span className="opp-risk-lbl">⚠ Risk to note</span>
                          <p className="opp-risk-text">{uc.risk_flag}</p>
                        </div>
                      )}
                      <div className="opp-data-req">
                        <span className="opp-data-lbl">Data requirement</span>
                        <p className="opp-data-text">{uc.data_requirement}</p>
                      </div>
                      {uc.tags?.length > 0 && (
                        <div className="opp-tags">
                          {uc.tags.map(t => <span key={t} className="chip chip-dim">{t}</span>)}
                        </div>
                      )}
                      {uc.verification_score && (
                        <div className="opp-score-row">
                          <span className="opp-score-lbl">Verification score</span>
                          <span className="opp-score-val">{uc.verification_score}/25</span>
                          <div className="opp-score-bar">
                            <div className="opp-score-fill"
                              style={{ width: `${(uc.verification_score / 25) * 100}%` }} />
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="phase-footer">
            <button className="btn btn-ghost" onClick={generateOpportunities} type="button">
              ↺ Regenerate
            </button>
            <button className="btn btn-primary" onClick={() => onComplete?.(result)} type="button">
              Proceed to Voting →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
