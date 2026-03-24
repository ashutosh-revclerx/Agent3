import { useState, useEffect, useRef } from 'react'
import './phases.css'

const PROBLEM_TAGS = [
  'Repetitive', 'Time-consuming', 'Manual', 'Error-prone',
  'Slow decision-making', 'Data scattered', 'No visibility',
  'Customer-facing', 'Compliance risk',
]

const SEVERITY_LABELS = {
  1: { label: 'Minor inconvenience', color: 'var(--text-3)' },
  2: { label: 'Regular friction',    color: 'var(--amber)' },
  3: { label: 'Significant impact',  color: 'var(--amber)' },
  4: { label: 'Major bottleneck',    color: '#e07040' },
  5: { label: 'Critical blocker',    color: 'var(--red)' },
}


export default function Phase3_Problems({ api, getWsBase, session, participant, onComplete }) {
  const role = participant?.role || 'Other'
  // Use the LLM-summarised workflow from onboarding; fall back to raw daily_work
  const onboardingWorkflow = participant?.workflow_summary || participant?.daily_work || ''

  const [step,         setStep]         = useState('submit')
  const [problems,     setProblems]     = useState([
    { id: 1, text: '', tags: [], severity: 3,
      department: participant?.department || '',
      workflow_description: participant?.workflow_summary || participant?.daily_work || '' },
  ])
  const [liveProblems, setLiveProblems] = useState([])
  const [clusters,     setClusters]    = useState(null)
  const [submitting,   setSubmitting]  = useState(false)
  const [error,        setError]       = useState(null)
  const [liveCount,    setLiveCount]   = useState(1)
  const wsRef = useRef(null)

  // WebSocket
  useEffect(() => {
    if (!session?.code) return
    const ws = new WebSocket(
      `${getWsBase()}/ws/${session.code}?participant_id=${participant?.id || 'host'}`
    )
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'problems_count')   setLiveCount(msg.count)
        if (msg.type === 'live_problems')    setLiveProblems(msg.problems)
        if (msg.type === 'problem_clusters') setClusters(msg.data)
      } catch {}
    }
    ws.onerror = () => {}
    return () => ws.close()
  }, [session?.code])

  const updateProblem = (id, key, val) =>
    setProblems(ps => ps.map(p => p.id === id ? { ...p, [key]: val } : p))

  const toggleTag = (id, tag) =>
    setProblems(ps => ps.map(p => {
      if (p.id !== id) return p
      const tags = p.tags.includes(tag) ? p.tags.filter(t => t !== tag) : [...p.tags, tag]
      return { ...p, tags }
    }))

  const addProblem = () => {
    if (problems.length >= 5) return
    setProblems(ps => [...ps, {
      id: Date.now(), text: '', tags: [], severity: 3,
      department: participant?.department || '',
      workflow_description: participant?.workflow_summary || participant?.daily_work || '',
    }])
  }

  const removeProblem = (id) =>
    setProblems(ps => ps.filter(p => p.id !== id))

  const validProblems = problems.filter(p => p.text.trim().length > 10)

  const handleSubmit = async () => {
    if (validProblems.length === 0) return
    setSubmitting(true)
    setError(null)
    try {
      const result = await api('/phase/problems', {
        method: 'POST',
        body: JSON.stringify({
          session_code:   session.code,
          participant_id: participant?.id,
          problems: validProblems.map(({ id, ...rest }) => rest),
        }),
      })
      setClusters(result.clusters)
      setLiveProblems(result.all_problems || [])
      setStep('clusters')
    } catch {
      setError('Could not submit. Is the backend running?')
    } finally {
      setSubmitting(false)
    }
  }


  return (
    <div className="phase-shell fade-up">

      <div className="phase-header">
        <div className="phase-logo">◈ AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-dot pulse" />
          <span className="phase-label">Phase 3 — Problem Discovery</span>
        </div>
      </div>

      <div className="step-track">
        {['Submit Problems', 'Problem Clusters'].map((s, i) => {
          const idx = ['submit', 'clusters'].indexOf(step)
          return (
            <div key={s} className={`step-item ${i <= idx ? 'active' : ''} ${i < idx ? 'done' : ''}`}>
              <div className="step-dot">{i < idx ? '✓' : i + 1}</div>
              <span className="step-name">{s}</span>
            </div>
          )
        })}
      </div>

      <div className="live-bar">
        <span className="live-dot pulse" />
        <span className="live-text">{liveCount} participant{liveCount !== 1 ? 's' : ''} submitting problems</span>
      </div>

      <div className="phase-body">

        {/* ── STEP 1: Submit ── */}
        {step === 'submit' && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-accent">Problem Identification</p>
              <h2 className="phase-title">What slows your<br />team down the most?</h2>
              <p className="phase-desc">
                Describe up to 5 problems. Your workflow from onboarding
                has been carried over automatically to help the AI identify
                which steps can be automated.
              </p>
            </div>

            <div className="problems-list">
              {problems.map((problem, idx) => (
                <div
                  key={problem.id}
                  className="problem-card fade-up"
                  style={{ animationDelay: `${idx * 0.06}s` }}
                >
                  {/* Header */}
                  <div className="problem-card-header">
                    <span className="problem-num">Problem {idx + 1}</span>
                    {problems.length > 1 && (
                      <button className="remove-btn" onClick={() => removeProblem(problem.id)}>✕</button>
                    )}
                  </div>

                  {/* Problem description */}
                  <textarea
                    className="input"
                    rows={3}
                    placeholder={
                      idx === 0
                        ? 'e.g. Our team manually copies data from emails into our CRM every day — takes 2+ hours and causes errors...'
                        : 'Describe another operational problem...'
                    }
                    value={problem.text}
                    onChange={e => updateProblem(problem.id, 'text', e.target.value)}
                    style={{ resize: 'vertical' }}
                  />

                  {/* Tags */}
                  <div className="tag-row">
                    <span className="tag-label">Characteristics:</span>
                    <div className="tag-group">
                      {PROBLEM_TAGS.map(tag => (
                        <button
                          key={tag}
                          className={`tag-btn ${problem.tags.includes(tag) ? 'selected' : ''}`}
                          onClick={() => toggleTag(problem.id, tag)}
                          type="button"
                        >
                          {tag}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Severity */}
                  <div className="severity-row">
                    <span className="tag-label">Severity:</span>
                    <div className="severity-track">
                      {[1, 2, 3, 4, 5].map(n => (
                        <button
                          key={n}
                          className={`severity-btn ${problem.severity === n ? 'selected' : ''}`}
                          style={problem.severity === n
                            ? { borderColor: SEVERITY_LABELS[n].color, color: SEVERITY_LABELS[n].color }
                            : {}}
                          onClick={() => updateProblem(problem.id, 'severity', n)}
                          type="button"
                        >
                          {n}
                        </button>
                      ))}
                      <span className="severity-desc" style={{ color: SEVERITY_LABELS[problem.severity]?.color }}>
                        {SEVERITY_LABELS[problem.severity]?.label}
                      </span>
                    </div>
                  </div>

                  {/* Workflow pre-filled from onboarding — shown read-only if present */}
                  {onboardingWorkflow && (
                    <div className="workflow-field">
                      <div className="workflow-field-header">
                        <span className="tag-label">Your workflow (from onboarding)</span>
                        <span className="workflow-optional">carried over automatically</span>
                      </div>
                      <div className="workflow-readonly">
                        {onboardingWorkflow}
                      </div>
                      {detectSteps(onboardingWorkflow).length > 0 && (
                        <div className="workflow-steps-preview">
                          {detectSteps(onboardingWorkflow).map((s, i) => (
                            <span key={i} className="workflow-step-chip">
                              {i + 1}. {s}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                </div>
              ))}
            </div>

            {problems.length < 5 && (
              <button className="add-problem-btn" onClick={addProblem} type="button">
                + Add another problem
              </button>
            )}


            {error && <div className="error-banner">⚠ {error}</div>}
          </div>
        )}

        {/* ── STEP 2: Clusters ── */}
        {step === 'clusters' && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-accent">Insight Mining Agent</p>
              <h2 className="phase-title">Problem clusters<br />detected</h2>
              <p className="phase-desc">
                Problems and workflows have been analysed and grouped into
                strategic themes. Manual steps identified in workflows are
                highlighted as automation targets.
              </p>
            </div>

            {clusters ? (
              <div className="insight-clusters">
                {clusters.map((cluster, i) => (
                  <div key={i} className="insight-cluster">
                    <div className="cluster-header">
                      <span className="cluster-icon">{cluster.icon || '◈'}</span>
                      <span className="cluster-theme">{cluster.theme}</span>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <span className="badge badge-default">
                          {cluster.problem_count} problem{cluster.problem_count !== 1 ? 's' : ''}
                        </span>
                        {cluster.cross_department && (
                          <span className="badge badge-green">Cross-dept ⬡</span>
                        )}
                        {cluster.manual_steps_identified > 0 && (
                          <span className="badge badge-amber">
                            {cluster.manual_steps_identified} manual step{cluster.manual_steps_identified !== 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="cluster-summary">{cluster.summary}</p>

                    {cluster.departments?.length > 0 && (
                      <div className="cluster-depts">
                        {cluster.departments.map(d => (
                          <span key={d} className="chip chip-dim">{d}</span>
                        ))}
                      </div>
                    )}

                    {/* Automation targets from workflow analysis */}
                    {cluster.automation_targets?.length > 0 && (
                      <div className="automation-targets">
                        <span className="automation-targets-label">Automatable steps identified →</span>
                        <div className="automation-targets-list">
                          {cluster.automation_targets.map((t, ti) => (
                            <span key={ti} className="automation-target-chip">{t}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="cluster-potential">
                      <span className="potential-label">AI Opportunity →</span>
                      <span className="potential-text">{cluster.ai_opportunity}</span>
                    </div>

                    <div className="severity-bar-row">
                      <span className="severity-bar-label">Avg severity</span>
                      <div className="severity-bar-track">
                        <div
                          className="severity-bar-fill"
                          style={{ width: `${(cluster.avg_severity / 5) * 100}%` }}
                        />
                      </div>
                      <span className="severity-bar-val">{cluster.avg_severity?.toFixed(1)}/5</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="ai-thinking">
                <div className="thinking-dots">
                  <span className="thinking-dot" />
                  <span className="thinking-dot" style={{ animationDelay: '0.2s' }} />
                  <span className="thinking-dot" style={{ animationDelay: '0.4s' }} />
                </div>
                <p className="thinking-label">Analysing problems and workflows...</p>
                <p className="thinking-sub">Clustering themes · Detecting manual steps · Identifying automation targets</p>
              </div>
            )}

            {liveProblems.length > validProblems.length && (
              <div className="live-problems-box">
                <p className="live-problems-title">
                  <span className="live-dot pulse" style={{ marginRight: 8 }} />
                  {liveProblems.length} total problems submitted by all participants
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="phase-footer">
        {step === 'submit' && (
          <>
            <div />
            <button
              className="btn btn-primary"
              disabled={validProblems.length === 0 || submitting}
              onClick={handleSubmit}
            >
              {submitting
                ? <><span className="spinner spinner-blue" /> Analysing...</>
                : `Submit ${validProblems.length} Problem${validProblems.length !== 1 ? 's' : ''} →`}
            </button>
          </>
        )}
        {step === 'clusters' && clusters && (
          <>
            <div />
            <button className="btn btn-primary" onClick={onComplete}>
              Proceed to Activities →
            </button>
          </>
        )}
      </div>
    </div>
  )
}

// ── Utility: detect discrete steps from workflow text ──────────────────────
// Splits workflow description into recognisable step chunks for the preview
function detectSteps(text) {
  if (!text || text.trim().length < 20) return []
  // Split on numbered lists, "then", "after that", "next", commas between verbs
  const parts = text
    .split(/(?:\d+\.\s|\bthen\b|\bafter that\b|\bnext\b|\bfinally\b)/i)
    .map(s => s.replace(/[,;]+$/, '').trim())
    .filter(s => s.length > 8 && s.length < 80)
    .slice(0, 5)
  return parts.length > 1 ? parts : []
}