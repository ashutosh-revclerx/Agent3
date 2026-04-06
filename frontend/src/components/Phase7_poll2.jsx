import { useState, useEffect, useRef } from 'react'

// ── Pillar icon map (matches Phase 5) ────────────────────────────────────────
const PILLAR_ICONS = {
  'Sales & Marketing':       '◆',
  'Operations & Fulfillment':'◈',
  'Finance & Administration':'▣',
  'Cross-functional':        '⬡',
}

// ── Shift indicator helpers ──────────────────────────────────────────────────
function ShiftBadge({ delta }) {
  if (delta === 0 || delta === undefined || delta === null) {
    return (
      <span style={{
        fontSize: 10, fontFamily: 'var(--font-h)', fontWeight: 600,
        color: 'var(--text-3)', padding: '2px 7px',
        border: '1px solid var(--border)', borderRadius: 20,
      }}>
        — same
      </span>
    )
  }
  const up = delta > 0
  return (
    <span style={{
      fontSize: 10, fontFamily: 'var(--font-h)', fontWeight: 700,
      color: up ? 'var(--green)' : '#e05050',
      padding: '2px 7px',
      border: `1px solid ${up ? 'var(--green-border)' : '#ffc9c9'}`,
      background: up ? 'var(--green-light)' : '#fff0f0',
      borderRadius: 20,
      display: 'inline-flex', alignItems: 'center', gap: 3,
    }}>
      {up ? '▲' : '▼'} {up ? '+' : ''}{delta}
    </span>
  )
}

// ── Mini benchmark strip shown while voting ──────────────────────────────────
function BenchmarkStrip({ benchmark, expanded, onToggle }) {
  if (!benchmark) return null
  const topUC = benchmark.top_use_cases?.slice(0, 3) || []

  return (
    <div style={{
      border: '1px solid var(--accent-mid)',
      borderRadius: 'var(--r-lg)',
      overflow: 'hidden',
      marginBottom: 16,
      background: 'var(--accent-light)',
    }}>
      {/* Header — always visible */}
      <button
        onClick={onToggle}
        type="button"
        style={{
          width: '100%', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', gap: 10,
          padding: '10px 16px',
          background: 'none', border: 'none', cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 14, color: 'var(--accent)' }}>◈</span>
          <span style={{
            fontSize: 11, fontFamily: 'var(--font-h)', fontWeight: 700,
            color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.07em',
          }}>
            Industry benchmark — {benchmark.adoption_rate}% adoption
          </span>
        </div>
        <span style={{ fontSize: 11, color: 'var(--accent)', fontFamily: 'var(--font-h)', fontWeight: 600 }}>
          {expanded ? '▲ hide' : '▼ show context'}
        </span>
      </button>

      {expanded && (
        <div style={{ borderTop: '1px solid var(--accent-mid)', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Headline */}
          <p style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.6, marginBottom: 4 }}>
            {benchmark.headline}
          </p>

          {/* Top 3 use cases */}
          {topUC.map((uc, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '7px 10px',
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 'var(--r-sm)',
            }}>
              <span style={{ fontSize: 12, color: 'var(--text)', fontFamily: 'var(--font-h)', fontWeight: 500 }}>
                {i + 1}. {uc.title}
              </span>
              <span style={{ fontSize: 11, color: 'var(--accent)', fontFamily: 'var(--font-h)', fontWeight: 600, flexShrink: 0, marginLeft: 8 }}>
                {uc.industry_adoption_pct}%
              </span>
            </div>
          ))}

          {/* Urgency signal */}
          {benchmark.urgency_signal && (
            <p style={{
              fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5,
              padding: '7px 10px',
              background: 'var(--bg-subtle)', borderRadius: 'var(--r-sm)',
              borderLeft: '2px solid var(--accent)',
            }}>
              ⚠ {benchmark.urgency_signal}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function Phase7_Poll2({
  api,
  getWsBase,
  session,
  participant,
  mode = 'participant',
  onComplete,
}) {
  const [useCases,        setUseCases]        = useState(session?.workshop_data?.use_cases || [])
  const [selectedVotes,   setSelectedVotes]   = useState([])
  const [voted,           setVoted]           = useState(false)
  const [results,         setResults]         = useState(null)    // final ranked results
  const [liveResults,     setLiveResults]     = useState(null)    // real-time WS updates
  const [shift,           setShift]           = useState(null)    // vote shift array
  const [consensusInsight,setConsensusInsight]= useState(null)
  const [submitting,      setSubmitting]      = useState(false)
  const [error,           setError]           = useState(null)
  const [benchmarkOpen,   setBenchmarkOpen]   = useState(false)   // benchmark strip toggle
  const wsRef = useRef(null)

  const benchmark    = session?.workshop_data?.benchmark || null
  const poll1Results = session?.workshop_data?.poll1_results || []

  // Poll 1 lookup map: id → { vote_count, rank }
  const poll1Map = Object.fromEntries(
    poll1Results.map(r => [r.id, { votes: r.vote_count, rank: r.rank }])
  )

  // ── Load use cases ────────────────────────────────────────────────────────
  useEffect(() => {
    if (session?.workshop_data?.use_cases?.length) {
      setUseCases(session.workshop_data.use_cases)
    }
  }, [session])

  // ── WebSocket ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!session?.code) return
    let disposed = false
    const ws = new WebSocket(
      `${getWsBase()}/ws/${session.code}?participant_id=${participant?.id || 'host'}`
    )
    wsRef.current = ws
    ws.onopen = () => {
      if (disposed) ws.close()
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'poll_2_update') {
          setLiveResults(msg.results)
          if (msg.consensus?.ai_insight) setConsensusInsight(msg.consensus.ai_insight)
          if (voted) setResults(msg.results)
        }
      } catch {}
    }

    return () => {
      disposed = true
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CLOSING) {
        ws.close()
      }
    }
  }, [session?.code, participant?.id, voted])

  // ── Toggle vote ───────────────────────────────────────────────────────────
  const toggleVote = (id) =>
    setSelectedVotes(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (selectedVotes.length === 0) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await api('/phase/vote', {
        method: 'POST',
        body: JSON.stringify({
          session_code:   session.code,
          participant_id: participant?.id,
          poll_number:    2,
          voted_ids:      selectedVotes,
        }),
      })
      setResults(res.results)
      setLiveResults(res.results)
      setShift(res.shift || null)
      if (res.consensus?.ai_insight) setConsensusInsight(res.consensus.ai_insight)
      setVoted(true)
    } catch {
      setError('Could not submit votes. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  const getVotePct = (ucId) => {
    const r = (liveResults || []).find(r => r.id === ucId)
    return r ? r.vote_pct : 0
  }

  const getShiftDelta = (ucId) => {
    if (!shift) {
      // Calculate from poll1Map + liveResults
      const p1 = poll1Map[ucId]?.votes || 0
      const p2 = (liveResults || []).find(r => r.id === ucId)?.vote_count || 0
      return p2 - p1
    }
    return shift.find(s => s.id === ucId)?.shift ?? 0
  }

  const isEducationValidated = (ucId) => {
    if (shift) return shift.find(s => s.id === ucId)?.education_validated || false
    const delta = getShiftDelta(ucId)
    return delta > 0
  }

  const getPoll1Rank = (ucId) => poll1Map[ucId]?.rank || null

  const activeResults = liveResults || results

  return (
    <div className="phase-shell fade-up">

      {/* Header */}
      <div className="phase-header">
        <div className="phase-logo">◈ AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-dot pulse" />
          <span className="phase-label">Phase 7 — Poll 2 (Post-Benchmark)</span>
        </div>
      </div>

      {/* Live bar */}
      <div className="live-bar">
        <span className="live-dot pulse" />
        <span className="live-text">
          {activeResults?.length
            ? `${(liveResults || results)?.reduce((s, r) => Math.max(s, r.vote_count || 0), 0) > 0
                ? (liveResults || []).filter((r, i, a) => i === a.findIndex(x => x.id === r.id)).length + ' use cases receiving votes'
                : 'Voting in progress'}`
            : 'Waiting for votes…'}
        </span>
      </div>

      {/* ── PRE-VOTE VIEW ────────────────────────────────────────────────── */}
      {!voted && (
        <>
          <div className="phase-body">
            <div className="phase-title-block">
              <span className="badge badge-purple">Poll 2 — After Benchmark</span>
              <h1 className="phase-title">Has the data<br />changed your mind?</h1>
              <p className="phase-desc">
                Vote again — knowing what you now know about global AI adoption in your industry.
                Your Poll 1 rank is shown on each card.
                <br />
                <strong>Multi-select · Votes are anonymous</strong>
              </p>
            </div>

            {/* Benchmark strip — collapsible reference panel */}
            <BenchmarkStrip
              benchmark={benchmark}
              expanded={benchmarkOpen}
              onToggle={() => setBenchmarkOpen(o => !o)}
            />

            {/* Use case cards */}
            <div className="opp-grid poll-grid">
              {useCases.map(uc => {
                const p1rank = getPoll1Rank(uc.id)
                const isSelected = selectedVotes.includes(uc.id)
                const validated = useCases.find
                  ? (session?.workshop_data?.benchmark?.validated_use_cases || []).find(v => v.id === uc.id)
                  : null
                const industryPct = validated?.industry_adoption_pct || uc.industry_adoption_pct || 0

                return (
                  <div
                    key={uc.id}
                    className={`opp-card poll-card ${isSelected ? 'poll-card-selected' : ''}`}
                    onClick={() => toggleVote(uc.id)}
                    style={{ position: 'relative' }}
                  >
                    {/* Poll 1 rank badge */}
                    {p1rank && (
                      <div style={{
                        position: 'absolute', top: 10, right: 10,
                        fontSize: 10, fontFamily: 'var(--font-h)', fontWeight: 700,
                        color: 'var(--text-3)',
                        background: 'var(--bg-subtle)',
                        border: '1px solid var(--border)',
                        borderRadius: 20, padding: '2px 8px',
                      }}>
                        Poll 1 #{p1rank}
                      </div>
                    )}

                    <div className="opp-card-header" style={{ paddingRight: p1rank ? 64 : 0 }}>
                      <span className="opp-pillar-icon">
                        {PILLAR_ICONS[uc.pillar] || '◎'}
                      </span>
                      <div className="opp-badges">
                        {uc.quick_win && <span className="badge badge-green">Quick win</span>}
                        {uc.data_ready && <span className="badge badge-accent">Data ready</span>}
                        {industryPct > 0 && (
                          <span className="badge badge-default" style={{ color: 'var(--accent)' }}>
                            {industryPct}% industry
                          </span>
                        )}
                      </div>
                    </div>

                    <h3 className="opp-title">{uc.title}</h3>
                    <p className="opp-desc">{uc.description}</p>

                    {/* Selection indicator */}
                    <div className="poll-select-indicator">
                      {isSelected
                        ? <span className="poll-selected-check">✓ Selected</span>
                        : <span className="poll-select-hint">Tap to vote</span>
                      }
                    </div>
                  </div>
                )
              })}
            </div>

            {error && <div className="error-banner">⚠ {error}</div>}
          </div>

          <div className="phase-footer">
            <div />
            <button
              className="btn btn-primary"
              disabled={selectedVotes.length === 0 || submitting}
              onClick={handleSubmit}
            >
              {submitting
                ? <><span className="spinner spinner-blue" /> Submitting…</>
                : `Cast ${selectedVotes.length} Vote${selectedVotes.length !== 1 ? 's' : ''} →`
              }
            </button>
          </div>
        </>
      )}

      {/* ── POST-VOTE VIEW ───────────────────────────────────────────────── */}
      {voted && (
        <>
          <div className="phase-body">
            <div className="phase-title-block">
              <span className="badge badge-green">Votes Submitted</span>
              <h2 className="phase-title">What changed<br />after the data?</h2>
              <p className="phase-desc">
                Use cases marked <strong style={{ color: 'var(--green)' }}>↑ education-validated</strong> gained
                votes after the industry benchmark — the strongest signal of strategic alignment.
              </p>
            </div>

            {/* Live ranked results with shift indicators */}
            <div className="poll-results">
              {(activeResults || []).map((item, i) => {
                const uc = useCases.find(u => u.id === item.id) || {}
                const delta = getShiftDelta(item.id)
                const eduValidated = isEducationValidated(item.id)

                return (
                  <div key={item.id} className="poll-result-row" style={{ position: 'relative' }}>
                    <div className="poll-rank">{i + 1}</div>

                    <div className="poll-content">
                      <div className="poll-title-row" style={{ flexWrap: 'wrap', gap: 5 }}>
                        <span className="poll-title">{uc.title || item.title}</span>
                        {/* Education validated badge */}
                        {eduValidated && (
                          <span className="badge badge-green" style={{ fontSize: 10 }}>
                            ↑ education-validated
                          </span>
                        )}
                        {/* Cross-pillar badge */}
                        {item.cross_pillar_flag && (
                          <span className="badge badge-purple" style={{ fontSize: 10 }}>
                            cross-pillar
                          </span>
                        )}
                      </div>

                      {/* Vote bar */}
                      <div className="poll-bar-track">
                        <div className="poll-bar-fill" style={{ width: `${getVotePct(item.id)}%` }} />
                      </div>

                      {/* Shift row */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                        <span style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-h)' }}>
                          Poll 1: {poll1Map[item.id]?.votes ?? '—'} votes
                          {poll1Map[item.id]?.rank ? ` (#${poll1Map[item.id].rank})` : ''}
                        </span>
                        <span style={{ fontSize: 10, color: 'var(--text-3)' }}>→</span>
                        <span style={{ fontSize: 10, color: 'var(--text)', fontFamily: 'var(--font-h)', fontWeight: 600 }}>
                          Poll 2: {item.vote_count} votes
                        </span>
                        <ShiftBadge delta={delta} />
                      </div>
                    </div>

                    <div className="poll-stats">
                      <span className="poll-votes">{item.vote_count}</span>
                      <span className="poll-pct">{item.vote_pct}%</span>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Vote shift summary — top movers */}
            {shift && shift.filter(s => Math.abs(s.shift) > 0).length > 0 && (
              <div style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-lg)',
                padding: '14px 16px',
                marginTop: 8,
              }}>
                <p style={{
                  fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em',
                  color: 'var(--text-3)', fontWeight: 600, marginBottom: 10,
                }}>
                  Biggest movers after benchmark education
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {shift
                    .filter(s => Math.abs(s.shift) > 0)
                    .sort((a, b) => Math.abs(b.shift) - Math.abs(a.shift))
                    .slice(0, 4)
                    .map(s => (
                      <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 12, color: 'var(--text)', flex: 1 }}>{s.title}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                          <span style={{ fontSize: 10, color: 'var(--text-3)' }}>{s.poll1_votes} → {s.poll2_votes}</span>
                          <ShiftBadge delta={s.shift} />
                          {s.education_validated && (
                            <span style={{
                              fontSize: 10, color: 'var(--green)', fontFamily: 'var(--font-h)', fontWeight: 700,
                            }}>✓</span>
                          )}
                        </div>
                      </div>
                    ))
                  }
                </div>
              </div>
            )}

            {/* Consensus insight from Gemini */}
            {consensusInsight && (
              <div
                className="insight-cluster fade-up"
                style={{ marginTop: 16, borderLeft: '3px solid var(--accent)' }}
              >
                <div className="cluster-header">
                  <span className="cluster-icon">◈</span>
                  <span className="cluster-theme">AI Consensus Analysis</span>
                </div>
                <p className="cluster-summary" style={{ fontSize: 13, lineHeight: 1.6 }}>
                  {consensusInsight}
                </p>
              </div>
            )}
          </div>

          <div className="phase-footer">
            <div />
            <button
              className="btn btn-primary"
              onClick={() => onComplete?.({ results: activeResults, shift })}
            >
              Proceed to Prioritisation Matrix →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
