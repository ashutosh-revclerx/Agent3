import { useState, useEffect, useRef } from 'react'

const PILLAR_ICONS = {
  'Sales & Marketing':        '◆',
  'Operations & Fulfillment': '◈',
  'Finance & Administration': '▣',
  'Cross-functional':         '⬡',
}

export default function Phase5_Poll1({
  api,
  getWsBase,
  session,
  participant,
  mode = 'participant',
  onComplete,
}) {
  const [useCases,      setUseCases]      = useState(session?.workshop_data?.use_cases || [])
  const [selectedVotes, setSelectedVotes] = useState([])
  const [voted,         setVoted]         = useState(false)
  const [results,       setResults]       = useState(null)       // final poll1_results
  const [liveResults,   setLiveResults]   = useState(null)       // real-time WS updates
  const [voterCount,    setVoterCount]    = useState(0)          // distinct voters
  const [submitting,    setSubmitting]    = useState(false)
  const [error,         setError]         = useState(null)
  const wsRef = useRef(null)

  // ── Load use cases ─────────────────────────────────────────────────────
  useEffect(() => {
    if (session?.workshop_data?.use_cases?.length) {
      setUseCases(session.workshop_data.use_cases)
    }
  }, [session])

  // ── WebSocket for live poll updates ────────────────────────────────────
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
        if (msg.type === 'poll_1_update') {
          const r = msg.results || []
          setLiveResults(r)
          // Derive voter count: highest vote_count in results ≈ voters who picked that item.
          // The backend returns vote_pct as (count / total_voters)*100, so we back-calculate.
          // Safest approach: use msg.total_voters if present, else take max vote_count.
          const total = msg.total_voters
            ?? Math.max(0, ...r.map(x => x.vote_count || 0))
          setVoterCount(total)
          if (voted) setResults(r)
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

  // ── Toggle vote ────────────────────────────────────────────────────────
  const toggleVote = (id) =>
    setSelectedVotes(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )

  // ── Submit ─────────────────────────────────────────────────────────────
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
          poll_number:    1,
          voted_ids:      selectedVotes,
        }),
      })
      const r = res.results || []
      setResults(r)
      setLiveResults(r)
      // Back-calculate total voters from pct: if vote_count=1 and pct=100, total=1
      const best = r.find(x => x.vote_count > 0 && x.vote_pct > 0)
      if (best) setVoterCount(Math.round((best.vote_count / best.vote_pct) * 100))
      setVoted(true)
    } catch {
      setError('Could not submit votes. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  const getVotePct = (ucId) => {
    const r = (liveResults || []).find(r => r.id === ucId)
    return r ? Math.round(r.vote_pct) : 0
  }
  const isCrossPillar = (ucId) => {
    const r = (liveResults || []).find(r => r.id === ucId)
    return r?.cross_pillar_flag || false
  }

  const activeResults = liveResults || results

  return (
    <div className="phase-shell fade-up">
      <div className="phase-header">
        <div className="phase-logo">◈ AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-dot pulse" />
          <span className="phase-label">Phase 5 — Poll 1 (Baseline)</span>
        </div>
      </div>

      {/* Live participants bar */}
      <div className="live-bar">
        <span className="live-dot pulse" />
        <span className="live-text">
          {voterCount} participant{voterCount !== 1 ? 's' : ''} voted
        </span>
      </div>

      <div className="phase-body">
        <div className="phase-title-block">
          <span className="badge badge-accent">Poll 1 — Before Benchmark</span>
          <h1 className="phase-title">Baseline Vote</h1>
          <p className="phase-desc">
            Before you see any industry benchmarks, vote for the use cases you
            believe will have the biggest impact on your work.
            <br />
            <strong>Multi-select · Your votes stay anonymous</strong>
          </p>
        </div>

        {/* ── VOTING VIEW ──────────────────────────────────────────────── */}
        {!voted && (
          <>
            <div className="opp-grid poll-grid">
              {useCases.map(uc => (
                <div
                  key={uc.id}
                  className={`opp-card poll-card ${selectedVotes.includes(uc.id) ? 'poll-card-selected' : ''}`}
                  onClick={() => toggleVote(uc.id)}
                >
                  <div className="opp-card-header">
                    <span className="opp-pillar-icon">
                      {PILLAR_ICONS[uc.pillar] || '◎'}
                    </span>
                    <div className="opp-badges">
                      {uc.quick_win  && <span className="badge badge-green">Quick win</span>}
                      {uc.data_ready && <span className="badge badge-accent">Data ready</span>}
                    </div>
                  </div>

                  <h3 className="opp-title">{uc.title}</h3>
                  <p className="opp-desc">{uc.description}</p>

                  <div className="poll-select-indicator">
                    {selectedVotes.includes(uc.id)
                      ? <span className="poll-selected-check">✓ Selected</span>
                      : <span className="poll-select-hint">Tap to vote</span>
                    }
                  </div>
                </div>
              ))}
            </div>

            {error && <div className="error-banner">⚠ {error}</div>}
          </>
        )}

        {/* ── POST-VOTE VIEW ───────────────────────────────────────────── */}
        {voted && (
          <div className="fade-up">
            <div className="phase-title-block">
              <span className="badge badge-green">Votes Submitted</span>
              <h2 className="phase-title">Voting in progress</h2>
              <p className="phase-desc">
                Thank you! The group is still voting. Live results update below.
                {mode === 'host' && ' (Host view — you can reveal anytime)'}
              </p>
            </div>

            <div className="poll-results">
              {activeResults?.map((item, i) => {
                const uc = useCases.find(u => u.id === item.id) || {}
                return (
                  <div key={item.id} className="poll-result-row">
                    <div className="poll-rank">{i + 1}</div>
                    <div className="poll-content">
                      <div className="poll-title-row">
                        <span className="poll-title">{uc.title || item.title}</span>
                        {isCrossPillar(item.id) && (
                          <span className="badge badge-purple">Cross-pillar</span>
                        )}
                      </div>
                      <div className="poll-bar-track">
                        <div className="poll-bar-fill" style={{ width: `${getVotePct(item.id)}%` }} />
                      </div>
                    </div>
                    <div className="poll-stats">
                      <span className="poll-votes">{item.vote_count}</span>
                      <span className="poll-pct">{Math.round(item.vote_pct)}%</span>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Consensus insight */}
            {(activeResults?.[0]?.consensus?.has_consensus || activeResults?.consensus?.ai_insight ||
              liveResults?.consensus?.ai_insight || results?.consensus?.ai_insight) && (
              <div className="insight-cluster fade-up" style={{ marginTop: 24, borderLeft: '3px solid var(--accent)' }}>
                <div className="cluster-header">
                  <span className="cluster-icon">◈</span>
                  <span className="cluster-theme">AI Consensus Analysis</span>
                </div>
                <p className="cluster-summary" style={{ fontSize: 13, lineHeight: 1.6 }}>
                  {liveResults?.consensus?.ai_insight
                    || results?.consensus?.ai_insight
                    || `${results?.consensus?.consensus_strength ?? ''}% agreement detected on key strategic priorities.`
                  }
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="phase-footer">
        {!voted ? (
          <>
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
          </>
        ) : (
          <>
            <div />
            <button className="btn btn-primary" onClick={() => onComplete?.({ results: activeResults })}>
              Proceed to Industry Benchmark →
            </button>
          </>
        )}
      </div>
    </div>
  )
}
