import { useState, useEffect } from 'react'
import './phases.css'

const SCORE_DIMENSIONS = [
  { key: 'clarity',     label: 'Clarity',     desc: 'Is the task clearly stated?' },
  { key: 'context',     label: 'Context',      desc: 'Is enough background provided?' },
  { key: 'output',      label: 'Output',       desc: 'Is the expected result defined?' },
  { key: 'constraints', label: 'Constraints',  desc: 'Are limits or format specified?' },
]

export default function ActivityC_PromptEngineering({ api, session, participant, mode = 'participant', onComplete }) {
  // step: loading → scenario → write → scored → simulation
  const [step,        setStep]       = useState('loading')
  const [scenario,    setScenario]   = useState(null)   // { title, situation, task, data_available, expected_output }
  const [prompt,      setPrompt]     = useState('')
  const [scored,      setScored]     = useState(null)
  const [simulation,  setSimulation] = useState(null)
  const [submitting,  setSubmitting] = useState(false)
  const [simRunning,  setSimRunning] = useState(false)
  const [error,       setError]      = useState(null)
  const [loadError,   setLoadError]  = useState(null)

  // ── Load scenario on mount ─────────────────────────────────────────────────
  useEffect(() => {
    loadScenario()
  }, [])

  const loadScenario = async () => {
    setStep('loading')
    setLoadError(null)
    try {
      const result = await api('/activity/prompt-scenario', {
        method: 'POST',
        body: JSON.stringify({
          session_code:   session.code,
          participant_id: participant?.id,
          role:           participant?.role || 'Other',
          department:     participant?.department || '',
        }),
      })
      setScenario(result)
      setStep('scenario')
    } catch {
      setLoadError('Could not generate scenario. Is the backend running?')
      setStep('scenario') // show error state
    }
  }

  // ── Score the prompt ───────────────────────────────────────────────────────
  const handleScorePrompt = async () => {
    if (prompt.trim().length < 20) return
    setSubmitting(true)
    setError(null)
    try {
      const result = await api('/activity/prompt-engineering', {
        method: 'POST',
        body: JSON.stringify({
          session_code:    session.code,
          participant_id:  participant?.id,
          prompt:          prompt.trim(),
          task_context:    scenario?.situation || '',
          scenario_id:     scenario?.id,
        }),
      })
      setScored(result)
      setStep('scored')
    } catch {
      setError('Could not score prompt. Is the backend running?')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Run simulation ─────────────────────────────────────────────────────────
  const handleRunSimulation = async () => {
    setSimRunning(true)
    setError(null)
    try {
      const result = await api('/activity/prompt-simulation', {
        method: 'POST',
        body: JSON.stringify({
          session_code:   session.code,
          participant_id: participant?.id,
          prompt:         scored?.improved_prompt || prompt.trim(),
          task_context:   scenario?.situation || '',
          scenario:       scenario,
        }),
      })
      setSimulation(result)
      setStep('simulation')
    } catch {
      setError('Could not run simulation.')
    } finally {
      setSimRunning(false)
    }
  }

  const scoreColor = (v) => v >= 4 ? 'var(--green)' : v >= 3 ? 'var(--amber)' : '#e07040'

  const stepList = ['scenario', 'write', 'scored', 'simulation']
  const stepIdx  = stepList.indexOf(step)

  return (
    <div className="phase-shell fade-up">

      <div className="phase-header">
        <div className="phase-logo">◈ AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-dot pulse" />
          <span className="phase-label">Activity C — Prompt Engineering</span>
        </div>
      </div>

      <div className="step-track">
        {['Your Scenario', 'Write Prompt', 'Get Scored', 'Live Demo'].map((s, i) => (
          <div key={s} className={`step-item ${i <= stepIdx ? 'active' : ''} ${i < stepIdx ? 'done' : ''}`}>
            <div className="step-dot">{i < stepIdx ? '✓' : i + 1}</div>
            <span className="step-name">{s}</span>
          </div>
        ))}
      </div>

      <div className="phase-body">

        {/* ── LOADING ── */}
        {step === 'loading' && (
          <div className="ai-thinking fade-up">
            <div className="thinking-dots">
              <span className="thinking-dot" />
              <span className="thinking-dot" style={{ animationDelay: '0.2s' }} />
              <span className="thinking-dot" style={{ animationDelay: '0.4s' }} />
            </div>
            <p className="thinking-label">Generating your scenario...</p>
            <p className="thinking-sub">
              Creating a real-world situation for {participant?.role || 'your role'} in {participant?.department || 'your department'}
            </p>
          </div>
        )}

        {/* ── SCENARIO REVEAL ── */}
        {step === 'scenario' && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-purple">Your Scenario</p>
              <h2 className="phase-title">Read this carefully —<br />then write your prompt</h2>
              <p className="phase-desc">
                The AI has generated a realistic work situation for a <strong style={{ color: 'var(--text)', fontWeight: 600 }}>{participant?.role}</strong> in <strong style={{ color: 'var(--text)', fontWeight: 600 }}>{participant?.department}</strong>.
                Your job is to write an AI prompt that would handle this situation.
              </p>
            </div>

            {loadError ? (
              <div className="error-banner" style={{ marginBottom: 12 }}>
                ⚠ {loadError}
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ marginLeft: 12 }}
                  onClick={loadScenario}
                >
                  Try again
                </button>
              </div>
            ) : scenario && (
              <div className="scenario-card">
                {/* Title bar */}
                <div className="scenario-header">
                  <span className="scenario-icon">◈</span>
                  <span className="scenario-title">{scenario.title}</span>
                </div>

                {/* The situation */}
                <div className="scenario-section">
                  <span className="scenario-section-label">The situation</span>
                  <p className="scenario-text">{scenario.situation}</p>
                </div>

                {/* What you need to do */}
                <div className="scenario-section">
                  <span className="scenario-section-label">Your task</span>
                  <p className="scenario-text scenario-task">{scenario.task}</p>
                </div>

                {/* Data available */}
                {scenario.data_available?.length > 0 && (
                  <div className="scenario-section">
                    <span className="scenario-section-label">Data you have access to</span>
                    <div className="scenario-data-list">
                      {scenario.data_available.map((d, i) => (
                        <span key={i} className="scenario-data-chip">◇ {d}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Expected output hint */}
                {scenario.expected_output && (
                  <div className="scenario-output-hint">
                    <span className="scenario-output-label">What good output looks like →</span>
                    <span className="scenario-output-text">{scenario.expected_output}</span>
                  </div>
                )}
              </div>
            )}

            {scenario && (
              <div className="scenario-tip">
                <span className="scenario-tip-label">Tip</span>
                <span className="scenario-tip-text">
                  A great prompt tells the AI exactly what to do, what data it has, what format the output should be in, and any constraints. Write it as if briefing a smart new team member.
                </span>
              </div>
            )}
          </div>
        )}

        {/* ── WRITE PROMPT ── */}
        {step === 'write' && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-purple">Write Your Prompt</p>
              <h2 className="phase-title">Now write the AI<br />instruction</h2>
              <p className="phase-desc">
                Based on the scenario, write a prompt that would instruct an AI assistant to complete your task. Be specific about inputs, outputs, and format.
              </p>
            </div>

            {/* Scenario recap */}
            {scenario && (
              <div className="scenario-recap">
                <span className="scenario-recap-label">Your scenario</span>
                <p className="scenario-recap-text">{scenario.task}</p>
              </div>
            )}

            <div className="phase-form">
              <div className="input-group">
                <label>Your prompt</label>
                <textarea
                  className="input"
                  rows={7}
                  placeholder={`Write your AI instruction here. Reference the specific data, format, and constraints relevant to your ${participant?.role || 'role'} scenario...`}
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  style={{ resize: 'vertical', fontFamily: 'var(--font-b)', fontSize: 13, lineHeight: 1.7 }}
                  autoFocus
                />
                <div style={{ textAlign: 'right', fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>
                  {prompt.length} characters
                </div>
              </div>
              {error && <div className="error-banner">⚠ {error}</div>}
            </div>
          </div>
        )}

        {/* ── SCORED ── */}
        {step === 'scored' && scored && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-purple">Prompt Coaching Agent</p>
              <h2 className="phase-title">Here's how your<br />prompt was scored</h2>
              <p className="phase-desc">
                Evaluated against your specific scenario — not generic criteria.
                The improved version is tailored to the {participant?.role} situation.
              </p>
            </div>

            {/* Score grid */}
            <div className="score-grid">
              {SCORE_DIMENSIONS.map(dim => {
                const val = scored.scores?.[dim.key] || 0
                return (
                  <div key={dim.key} className="score-card">
                    <div className="score-header">
                      <span className="score-dim-label">{dim.label}</span>
                      <span className="score-val" style={{ color: scoreColor(val) }}>{val}/5</span>
                    </div>
                    <div className="score-bar-track">
                      <div className="score-bar-fill"
                        style={{ width: `${(val / 5) * 100}%`, background: scoreColor(val) }} />
                    </div>
                    <p className="score-dim-desc">{dim.desc}</p>
                    {scored.feedback?.[dim.key] && (
                      <p className="score-feedback">{scored.feedback[dim.key]}</p>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Total */}
            <div className="total-score-box">
              <span className="total-score-label">Overall Prompt Score</span>
              <span className="total-score-val" style={{ color: scoreColor((scored.total_score / 20) * 5) }}>
                {scored.total_score}/20
              </span>
            </div>

            {/* Original vs improved */}
            <div className="prompt-compare">
              <div className="compare-col">
                <p className="compare-label">Your original prompt</p>
                <div className="compare-box">{prompt}</div>
              </div>
              <div className="compare-arrow">→</div>
              <div className="compare-col">
                <p className="compare-label">Improved by AI</p>
                <div className="compare-box improved">{scored.improved_prompt}</div>
              </div>
            </div>

            {/* Key improvement */}
            {scored.key_improvement && (
              <div className="insight-cluster">
                <div className="cluster-header">
                  <span className="cluster-icon">◈</span>
                  <span className="cluster-theme">Key improvement</span>
                </div>
                <p className="cluster-summary">{scored.key_improvement}</p>
              </div>
            )}

            {/* Scenario alignment */}
            {scored.scenario_alignment && (
              <div className="scenario-alignment-box">
                <span className="scenario-alignment-label">Scenario fit →</span>
                <span className="scenario-alignment-text">{scored.scenario_alignment}</span>
              </div>
            )}

            {error && <div className="error-banner">⚠ {error}</div>}
          </div>
        )}

        {/* ── SIMULATION ── */}
        {step === 'simulation' && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-purple">Live AI Demo</p>
              <h2 className="phase-title">This is what AI does<br />with your scenario</h2>
              <p className="phase-desc">
                The improved prompt ran against your actual {participant?.role} situation.
                This is what the output would look like in production.
              </p>
            </div>

            {simulation ? (
              <>
                <div className="sim-prompt-box">
                  <p className="sim-prompt-label">Prompt used</p>
                  <p className="sim-prompt-text">{scored?.improved_prompt || prompt}</p>
                </div>

                <div className="sim-output-box">
                  <div className="sim-output-header">
                    <span className="sim-output-icon">◈</span>
                    <span className="sim-output-label">AI Response</span>
                  </div>
                  <div className="sim-output-content">{simulation.output}</div>
                </div>

                {simulation.insight && (
                  <div className="sim-insight-box">
                    <span className="sim-insight-label">What this shows →</span>
                    <span className="sim-insight-text">{simulation.insight}</span>
                  </div>
                )}

                {simulation.time_saved && (
                  <div className="time-saved-box">
                    <span className="time-saved-icon">◉</span>
                    <div>
                      <p className="time-saved-label">Estimated time saving</p>
                      <p className="time-saved-value">{simulation.time_saved}</p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="ai-thinking">
                <div className="thinking-dots">
                  <span className="thinking-dot" />
                  <span className="thinking-dot" style={{ animationDelay: '0.2s' }} />
                  <span className="thinking-dot" style={{ animationDelay: '0.4s' }} />
                </div>
                <p className="thinking-label">Running your scenario through the AI...</p>
                <p className="thinking-sub">Using your improved prompt on real {participant?.role} data</p>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Footer */}
      <div className="phase-footer">
        {step === 'scenario' && scenario && !loadError && (
          <>
            <button className="btn btn-ghost" onClick={loadScenario}>↺ New scenario</button>
            <button className="btn btn-primary" onClick={() => setStep('write')}>
              Write My Prompt →
            </button>
          </>
        )}
        {step === 'write' && (
          <>
            <button className="btn btn-ghost" onClick={() => setStep('scenario')}>← Scenario</button>
            <button
              className="btn btn-primary"
              disabled={prompt.trim().length < 20 || submitting}
              onClick={handleScorePrompt}
            >
              {submitting ? <><span className="spinner spinner-blue" /> Scoring...</> : 'Score My Prompt →'}
            </button>
          </>
        )}
        {step === 'scored' && (
          <>
            <button className="btn btn-ghost" onClick={() => setStep('write')}>← Edit Prompt</button>
            <button
              className="btn btn-primary"
              disabled={simRunning}
              onClick={handleRunSimulation}
            >
              {simRunning ? <><span className="spinner spinner-blue" /> Running...</> : 'Run Live Demo →'}
            </button>
          </>
        )}
        {step === 'simulation' && simulation && (
          <>
            <div />
            <button className="btn btn-primary" onClick={onComplete}>
              Proceed to Opportunity Generation →
            </button>
          </>
        )}
      </div>
    </div>
  )
}
