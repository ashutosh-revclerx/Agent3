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

  const [name, setName] = useState(role === 'host' ? (session?.host_name || '') : '')
  const [selectedRole, setSelectedRole] = useState('')
  const [department, setDepartment] = useState('')

  const [chatDone, setChatDone] = useState(false)
  const [topChallenge, setTopChallenge] = useState('')
  const [dailyWork, setDailyWork] = useState('')
  const [conversation, setConversation] = useState([])

  const handleCodeSubmit = async () => {
    if (!sessionCode.trim()) return
    setLoading(true)
    setError(null)
    try {
      const normalizedCode = sessionCode.trim().toUpperCase()
      const data = await api(`/session/${normalizedCode}`)
      setResolvedSession(data)
      setSessionCode(normalizedCode)
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
      const activeSession = resolvedSession || session || {
        code: (resolvedSession?.code || sessionCode).trim().toUpperCase(),
      }
      const data = await api('/participant/join', {
        method: 'POST',
        body: JSON.stringify({
          session_code: activeSession.code,
          name,
          role: selectedRole,
          department,
          top_challenge: topChallenge,
          daily_work: dailyWork,
          ai_confidence: 3,
          conversation: conversation.map(m => ({ role: m.type === 'user' ? 'user' : 'agent', text: m.text })),
        }),
      })
      onComplete({
        participant: data,
        session: activeSession,
      })
    } catch (err) {
      setError(err.message || 'Could not join session. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const [dynamicChallengeQuestion, setDynamicChallengeQuestion] = useState(null)

  // Builds a personalised challenge question by weaving the workflow answer + role together
  const buildChallengeQuestion = (workflowAnswer) => {
    if (!workflowAnswer || !selectedRole) return null

    const lower = workflowAnswer.toLowerCase()

    // Pick out any tools/systems the user mentioned so the follow-up feels specific
    const toolKeywords = [
      'excel', 'spreadsheet', 'crm', 'salesforce', 'hubspot', 'slack',
      'email', 'jira', 'notion', 'dashboard', 'report', 'database',
      'pipeline', 'script', 'code', 'meeting', 'call', 'ticket',
      'invoice', 'forecast', 'powerpoint', 'sheets', 'sql',
    ]
    const mentioned = toolKeywords.filter(k => lower.includes(k))
    const toolPhrase = mentioned.length > 0
      ? ` — especially around ${mentioned.slice(0, 2).join(' and ')} —`
      : ''

    const templates = {
      'CEO / Founder':
        `Based on what you've just described${toolPhrase}, what's the single thing that's slowing down your ability to scale or make fast decisions right now?`,
      'CTO / Technology Leader':
        `Given the workflow you described${toolPhrase}, where does your team hit the most technical friction — deployments, data quality, legacy systems, or something else?`,
      'COO / Operations':
        `With the day-to-day you've outlined${toolPhrase}, which operational bottleneck keeps resurfacing in your leadership reviews?`,
      'Product Manager':
        `From the workflow you described${toolPhrase}, what's the biggest thing slowing your team's ability to ship valuable product to customers?`,
      'Data / AI Engineer':
        `Given what you've described${toolPhrase}, what's the biggest obstacle — data reliability, deployment friction, or tooling gaps — preventing you from delivering AI at production quality?`,
      'Business Analyst':
        `Based on your workflow${toolPhrase}, which reporting or analysis task takes the most manual effort and still produces unreliable output?`,
      'Department Head':
        `From what you've shared about your day-to-day${toolPhrase}, what keeps your team from performing at their best consistently?`,
      'Consultant':
        `Given the workflow you've described${toolPhrase}, what's the most common reason AI initiatives fail to reach production in your experience?`,
      'Other':
        `Based on what you've described${toolPhrase}, what's the biggest operational challenge you face day to day?`,
    }

    return templates[selectedRole] || templates['Other']
  }

  const chatQuestions = useMemo(() => {
    const firstName = name ? name.split(' ')[0] : ''
    const greeting = firstName
      ? `Hey ${firstName}! 👋 I'm your AI facilitator. Say hello to start our conversation!`
      : `Hey there! 👋 I'm your AI facilitator. Say hello to start our conversation!`

    return selectedRole
      ? [
          {
            id: 'daily_work',
            question: greeting,
            hint: 'Just say or type "hello" to begin.',
            placeholder: 'Say hello to start...',
            field: 'daily_work',
            required: true,
          },
          {
            id: 'challenge',
            // Dynamic question built from the workflow answer; falls back to static if not yet available
            question: dynamicChallengeQuestion || CHALLENGE_QUESTION[selectedRole] || CHALLENGE_QUESTION.Other,
            hint: CHALLENGE_HINT[selectedRole] || CHALLENGE_HINT.default,
            placeholder: 'Describe it in your own words - specific examples help most.',
            field: 'top_challenge',
            required: true,
          },
        ]
      : []
  }, [selectedRole, name, dynamicChallengeQuestion])

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
                    Lets walk through how you start the work
                    <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--accent)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      Interactive
                    </span>
                  </label>
                  <AgentChat
                    key={selectedRole}
                    questions={chatQuestions}
                    dynamicEndpoint="/ai/onboarding-chat"
                    context={{ name, role: selectedRole, department }}
                    agentName="Facilitator Agent"
                    agentAvatar="◇"
                    apiBase={apiBase}
                    onStepComplete={(field, value) => {
                      // As soon as the workflow answer is in, build the contextual challenge question
                      if (field === 'daily_work' && value) {
                        setDailyWork(value)
                        setDynamicChallengeQuestion(buildChallengeQuestion(value))
                      }
                    }}
                    onComplete={(answers) => {
                      const { _conversation, ...fields } = answers
                      setTopChallenge(fields.top_challenge || '')
                      setDailyWork(fields.daily_work || '')
                      setConversation(_conversation || [])
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
