import { useState, useEffect, useRef } from 'react'
import './phases.css'

export default function Phase6_GlobalAdoptionInsight({
  api,
  getWsBase,
  session,
  participant,
  mode = 'participant',
  onComplete,
}) {
  const [benchmark, setBenchmark] = useState(session?.workshop_data?.benchmark || null)
  const [revealed, setRevealed] = useState(false)
  const [loading, setLoading] = useState(mode === 'host' && !session?.workshop_data?.benchmark)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)

  const industry = session?.industry || 'your industry'
  const useCases = session?.workshop_data?.use_cases || []

  // ── WebSocket for live reveal (host can trigger, everyone sees update) ──
  useEffect(() => {
    if (!session?.code) return

    const ws = new WebSocket(
      `${getWsBase()}/ws/${session.code}?participant_id=${participant?.id || 'host'}`
    )
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'benchmark_reveal' || msg.type === 'benchmark_ready') {
          setBenchmark(msg.data)
          setRevealed(true)
          setLoading(false)
        }
      } catch {}
    }

    return () => ws.close()
  }, [session?.code, participant?.id, getWsBase])

  // ── Host auto-generates / reveals on mount; participants wait for reveal ──
  const generateBenchmark = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api('/phase/benchmark', {
        method: 'POST',
        body: JSON.stringify({
          session_code: session.code,
          // Agent 5 (Industry Benchmark) will enrich with Gemini using Phase 0 industry + Phase 4 use cases
        }),
      })
      setBenchmark(data)
      setRevealed(true)
    } catch (err) {
      setError('Could not load industry benchmark. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (session?.workshop_data?.benchmark) {
      setBenchmark(session.workshop_data.benchmark)
      setRevealed(true)
      setLoading(false)
      return
    }

    if (mode === 'host' && !revealed) {
      generateBenchmark()
      return
    }

    if (mode !== 'host') {
      setLoading(false)
    }
  }, [mode, revealed, session?.workshop_data?.benchmark])

  // ── Visual helpers ──
  const getAdoptionColor = (pct) => {
    if (pct >= 65) return 'var(--green)'
    if (pct >= 40) return 'var(--amber)'
    return 'var(--red)'
  }

  const validatedUseCases = benchmark?.validated_use_cases || useCases

  return (
    <div className="phase-shell fade-up">
      <div className="phase-header">
        <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-ind-dot"></div>
          <span className="phase-ind-label">Phase 6 — Global Adoption Insight</span>
        </div>
      </div>

      {/* Live indicator */}
      <div className="live-bar">
        <span className="live-dot pulse" />
        <span className="live-text">
          {revealed ? 'Industry benchmark live' : 'Waiting for host reveal...'}
        </span>
      </div>

      <div className="phase-body">
        {!revealed && !loading && mode !== 'host' && (
          <div className="fade-up" style={{ textAlign: 'center', padding: '80px 20px' }}>
            <div className="ai-thinking" style={{ margin: '0 auto', maxWidth: 320 }}>
              <div className="thinking-dots">
                <span className="thinking-dot" />
                <span className="thinking-dot" style={{ animationDelay: '0.2s' }} />
                <span className="thinking-dot" style={{ animationDelay: '0.4s' }} />
              </div>
              <p className="thinking-label">Host is revealing the industry benchmark...</p>
              <p className="thinking-sub">
                This is the education window — see how your team’s instincts compare to real-world adoption
              </p>
            </div>
          </div>
        )}

        {loading && (
          <div className="ai-thinking fade-up">
            <div className="thinking-dots">
              <span className="thinking-dot" />
              <span className="thinking-dot" style={{ animationDelay: '0.2s' }} />
              <span className="thinking-dot" style={{ animationDelay: '0.4s' }} />
            </div>
            <p className="thinking-label">Enriching benchmark with live industry data...</p>
            <p className="thinking-sub">
              Cross-referencing your {useCases.length} use cases • Pulling Gemini insights
            </p>
          </div>
        )}

        {revealed && benchmark && (
          <div className="fade-up">
            <div className="phase-title-block">
              <span className="badge badge-purple">Education Window</span>
              <h1 className="phase-title">How does your team stack up?</h1>
              <p className="phase-desc">
                Industry AI adoption in <strong>{industry}</strong>. Your voted use cases vs. what leading companies are actually deploying.
              </p>
            </div>

            {/* Headline */}
            <div className="insight-cluster" style={{ marginBottom: 24 }}>
              <div className="cluster-header">
                <span className="cluster-icon">◈</span>
                <span className="cluster-theme">Market Context</span>
              </div>
              <p className="cluster-summary" style={{ fontSize: 15, lineHeight: 1.5 }}>
                {benchmark.headline}
              </p>
            </div>

            {/* Adoption Rate */}
            <div className="summary-card" style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <div>
                  <span className="summary-title">AI Adoption Rate</span>
                  <div style={{ fontSize: 42, fontWeight: 700, color: getAdoptionColor(benchmark.adoption_rate) }}>
                    {benchmark.adoption_rate}%
                  </div>
                  <span style={{ fontSize: 13, color: 'var(--text-2)' }}>of {industry} organizations have deployed AI at scale</span>
                </div>
                <div className="severity-bar-track" style={{ width: 180, height: 12 }}>
                  <div
                    className="severity-bar-fill"
                    style={{
                      width: `${benchmark.adoption_rate}%`,
                      background: getAdoptionColor(benchmark.adoption_rate),
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Top 5 Industry Use Cases */}
            <div style={{ marginBottom: 32 }}>
              <p className="summary-title" style={{ marginBottom: 12 }}>Top 5 Most-Deployed AI Use Cases in {industry}</p>
              <div className="opp-grid" style={{ gridTemplateColumns: '1fr', gap: 10 }}>
                {benchmark.top_use_cases?.slice(0, 5).map((uc, i) => (
                  <div key={i} className="opp-card" style={{ padding: '14px 16px' }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                      <span style={{ fontSize: 18 }}>{i + 1}</span>
                      <div style={{ flex: 1 }}>
                        <h3 className="opp-title" style={{ fontSize: 14 }}>{uc.title}</h3>
                        <p className="opp-desc" style={{ fontSize: 11 }}>{uc.description}</p>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 600 }}>
                          {uc.industry_adoption_pct}%
                        </span>
                        <div style={{ fontSize: 10, color: 'var(--text-3)' }}>adoption</div>
                        {uc.avg_roi && (
                          <div style={{ fontSize: 10, color: 'var(--green)', marginTop: 2 }}>
                            ~{uc.avg_roi} ROI
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Your Voted Use Cases vs Industry */}
            <div className="phase-title-block" style={{ marginBottom: 12 }}>
              <p className="summary-title">Your Poll 1 Votes — Industry Validation</p>
            </div>
            <div className="poll-results" style={{ marginBottom: 32 }}>
              {validatedUseCases.map((uc) => {
                const isValidated = uc.sector_validated === true
                return (
                  <div key={uc.id} className="poll-result-row">
                    <div className="poll-content" style={{ flex: 1 }}>
                      <div className="poll-title-row">
                        <span className="poll-title">{uc.title}</span>
                        {isValidated && <span className="badge badge-green">✓ Sector validated</span>}
                        {!isValidated && <span className="badge badge-default">Emerging</span>}
                      </div>
                    </div>
                    <div className="poll-stats">
                      <span style={{ fontSize: 13, color: isValidated ? 'var(--green)' : 'var(--text-3)' }}>
                        {uc.industry_adoption_pct || 0}%
                      </span>
                      <span style={{ fontSize: 10, color: 'var(--text-3)' }}>industry</span>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* AI Insights */}
            <div className="insight-cluster">
              <div className="cluster-header">
                <span className="cluster-icon">◈</span>
                <span className="cluster-theme">AI Alignment Assessment</span>
              </div>
              <p className="cluster-summary">{benchmark.org_alignment}</p>
            </div>

            {/* Hidden Opportunity */}
            {benchmark.hidden_opportunity && (
              <div className="insight-cluster" style={{ marginTop: 16 }}>
                <div className="cluster-header">
                  <span className="cluster-icon">⬡</span>
                  <span className="cluster-theme">Hidden Opportunity</span>
                </div>
                <p className="cluster-summary" style={{ fontStyle: 'italic' }}>
                  {benchmark.hidden_opportunity}
                </p>
              </div>
            )}

            {/* Urgency Signal */}
            {benchmark.urgency_signal && (
              <div className="tone-adaptation-box" style={{ marginTop: 16, background: 'var(--red-light)', borderColor: 'var(--red-border)' }}>
                <span style={{ fontSize: 22, color: 'var(--red)' }}>⚠</span>
                <div>
                  <div style={{ fontFamily: 'var(--font-h)', fontWeight: 700, fontSize: '13px', color: 'var(--red)' }}>
                    Cost of delay
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-2)', lineHeight: '1.6' }}>
                    {benchmark.urgency_signal}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="error-banner" style={{ margin: '20px 0' }}>
            ⚠ {error}
            {mode === 'host' && (
              <button className="btn btn-ghost btn-sm" onClick={generateBenchmark} style={{ marginLeft: 12 }}>
                Retry
              </button>
            )}
          </div>
        )}
      </div>

      <div className="phase-footer">
        {revealed && (
          <>
            <div />
              <button className="btn btn-primary" onClick={() => onComplete?.(benchmark)}>
              Proceed to Poll 2 (Post-Benchmark) →
            </button>
          </>
        )}
        {!revealed && mode === 'host' && (
          <button className="btn btn-primary" onClick={generateBenchmark} disabled={loading}>
            {loading ? <span className="spinner spinner-blue" /> : 'Reveal Benchmark to Team →'}
          </button>
        )}
      </div>
    </div>
  )
}
