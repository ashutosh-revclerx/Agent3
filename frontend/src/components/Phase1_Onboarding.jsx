import { useMemo, useState } from 'react'
import AgentChat from './Agentchat'
import './phases.css'

const ROLES = [
  'CEO / Founder', 'CTO / Technology Leader', 'COO / Operations',
  'Product Manager', 'Data / AI Engineer', 'Business Analyst',
  'Department Head', 'Consultant', 'Other',
]

const CHALLENGE_QUESTION = {
  'CEO / Founder': 'What is the single biggest thing holding your business back from its next stage of growth right now?',
  'CTO / Technology Leader': 'What technical or infrastructure limitation is creating the most friction for your team right now?',
  'COO / Operations': 'What operational bottleneck comes up most often in your leadership reviews?',
  'Product Manager': 'What is slowing your team\'s ability to ship valuable product to customers?',
  'Data / AI Engineer': 'What is the biggest technical obstacle preventing your team from delivering AI at production quality?',
  'Business Analyst': 'Which reporting or analysis task takes the most manual effort and produces the least reliable output?',
  'Department Head': 'What keeps your team from performing at its best day to day?',
  'Consultant': 'What is the most common reason client AI initiatives fail to reach production, in your experience?',
  'Other': 'What is the biggest operational challenge in your day-to-day work right now?',
}

const CHALLENGE_HINT = {
  'CTO / Technology Leader': 'Think about legacy systems, data pipelines, deployment speed, or team capability gaps.',
  'Data / AI Engineer': 'Think about data quality, model reliability, tooling gaps, or deployment friction.',
  'Business Analyst': 'Think about data gathering, spreadsheet wrangling, or insight-to-decision delays.',
  default: 'Be specific - the more detail you give, the more precisely the AI can identify relevant use cases.',
}

export default function Phase1_Onboarding({ api, apiBase, session, role, onComplete, onBack }) {
  const [sessionCode, setSessionCode] = useState(session?.code || '')
  const [step, setStep] = useState(role === 'host' ? 'profile' : 'code')
  const [resolvedSession, setResolvedSession] = useState(session)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [name, setName] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  const [department, setDepartment] = useState('')

  const [chatDone, setChatDone] = useState(false)
  const [topChallenge, setTopChallenge] = useState('')
  const [dailyWork, setDailyWork] = useState('')

  const handleCodeSubmit = async () => {
    if (!sessionCode.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await api(`/session/${sessionCode.toUpperCase()}`)
      setResolvedSession(data)
      setStep('profile')
    } catch {
      setError('Session not found. Check your code and try again.')
    } finally {
      setLoading(false)
    }
  }

  const isFormValid = name.trim() && selectedRole && department.trim() && chatDone

  const handleJoin = async () => {
    if (!isFormValid) return
    setLoading(true)
    setError(null)
    try {
      const data = await api('/participant/join', {
        method: 'POST',
        body: JSON.stringify({
          session_code: resolvedSession?.code || sessionCode,
          name,
          role: selectedRole,
          department,
          top_challenge: topChallenge,
          daily_work: dailyWork,
          ai_confidence: 3,
        }),
      })
      onComplete(data)
    } catch (err) {
      setError(err.message || 'Could not join session. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const chatQuestions = useMemo(() => (
    selectedRole
      ? [
          {
            id: 'daily_work',
            question: 'What is the most time-consuming or repetitive part of your daily work?',
            hint: 'Think about manual reporting, data entry, email processing, or coordinating across systems.',
            placeholder: 'Briefly describe your main daily activities.',
            field: 'daily_work',
            required: true,
          },
          {
            id: 'challenge',
            question: CHALLENGE_QUESTION[selectedRole] || CHALLENGE_QUESTION.Other,
            hint: CHALLENGE_HINT[selectedRole] || CHALLENGE_HINT.default,
            placeholder: 'Describe it in your own words - specific examples help most.',
            field: 'top_challenge',
            required: true,
          }
        ]
      : []
  ), [selectedRole])

  return (
    <div className="phase-shell fade-up">
      <div className="phase-header">
        <div className="phase-logo">AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-dot pulse" />
          <span className="phase-label">Phase 1 Onboarding</span>
        </div>
      </div>

      {step === 'code' && (
        <div className="phase-body">
          <div className="phase-title-block">
            <span className="badge badge-accent">Join Session</span>
            <h2 className="phase-title">Enter your<br />session code</h2>
            <p className="phase-desc">Your host will share a 6-character code. Enter it below.</p>
          </div>
          <div className="input-group">
            <input
              className="input"
              style={{ fontSize: 28, letterSpacing: '0.2em', textAlign: 'center', textTransform: 'uppercase' }}
              maxLength={6}
              placeholder="AB12CD"
              value={sessionCode}
              onChange={e => setSessionCode(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && handleCodeSubmit()}
              autoFocus
            />
          </div>
          {error && <div className="error-banner">⚠️ {error}</div>}
          <div className="phase-footer" style={{ marginTop: 'auto' }}>
            <div />
            <button className="btn btn-primary" onClick={handleCodeSubmit} disabled={loading || !sessionCode.trim()}>
              {loading ? <><span className="spinner" /> Checking...</> : 'Join →'}
            </button>
          </div>
        </div>
      )}

      {step === 'profile' && (
        <>
          {resolvedSession && (
            <div style={{ padding: '8px 22px', background: 'var(--accent-light)', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
              <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--accent)' }}>Joining</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', fontFamily: 'var(--font-h)' }}>
                {resolvedSession.company} · {resolvedSession.code}
              </span>
            </div>
          )}

          <div className="phase-body">
            <div className="phase-title-block">
              <span className="badge badge-accent">Your Profile</span>
              <h2 className="phase-title">Tell us about<br />yourself</h2>
              <p className="phase-desc">This shapes the questions and AI use cases tailored to your role.</p>
            </div>

            <div className="phase-form">
              <div className="input-group">
                <label className="input-label">Full name</label>
                <input className="input" placeholder="Your name" value={name} onChange={e => setName(e.target.value)} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="input-group">
                  <label className="input-label">Your role</label>
                  <select
                    className="input"
                    value={selectedRole}
                    onChange={e => {
                      setSelectedRole(e.target.value)
                      setChatDone(false)
                      setTopChallenge('')
                    }}
                  >
                    <option value="">Select role...</option>
                    {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div className="input-group">
                  <label className="input-label">Department</label>
                  <input className="input" placeholder="e.g. Engineering" value={department} onChange={e => setDepartment(e.target.value)} />
                </div>
              </div>

              {selectedRole && (
                <div className="input-group">
                  <label className="input-label">
                    One question from the AI
                    <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--accent)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      Interactive
                    </span>
                  </label>
                  <AgentChat
                    key={selectedRole}
                    questions={chatQuestions}
                    agentName="Facilitator Agent"
                    agentAvatar="◇"
                    apiBase={apiBase}
                    onComplete={(answers) => {
                      setTopChallenge(answers.top_challenge || '')
                      setDailyWork(answers.daily_work || '')
                      setChatDone(true)
                    }}
                  />
                </div>
              )}

              {!selectedRole && (
                <div style={{ padding: '12px 14px', background: 'var(--bg-subtle)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', fontSize: 12, color: 'var(--text-3)' }}>
                  Select your role above to unlock the AI question.
                </div>
              )}
            </div>

            {error && <div className="error-banner">⚠️ {error}</div>}
          </div>

          <div className="phase-footer">
            <button className="btn btn-ghost" onClick={onBack}>â† Back</button>
            <button className="btn btn-primary" onClick={handleJoin} disabled={!isFormValid || loading}>
              {loading ? <><span className="spinner" /> Joining...</> : 'Enter Workshop →'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
