import { useState, useEffect, useRef } from 'react'
import AvatarGuidedOnboarding from './AvatarGuidedOnboarding'

const ROLES = [
  'CEO / Founder', 'CTO / Technology Leader', 'COO / Operations',
  'Product Manager', 'Data / AI Engineer', 'Business Analyst',
  'Department Head', 'Consultant', 'Lead Generation', 'Other',
]

export default function Phase1_Onboarding({ api, getWsBase, session, role, onComplete, onBack }) {
  const [sessionCode, setSessionCode] = useState(session?.code || '')
  const [step, setStep] = useState(role === 'host' ? 'profile' : 'code')
  const [resolvedSession, setResolvedSession] = useState(session)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [name, setName] = useState(role === 'host' ? (session?.host_name || '') : '')
  const [selectedRole, setSelectedRole] = useState('')
  const [customRole, setCustomRole] = useState('')
  const [linkedinUrl, setLinkedinUrl] = useState('')

  const [dna, setDna] = useState(null)
  const [profile, setProfile] = useState(null)
  const [isReviewing, setIsReviewing] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!sessionCode || !getWsBase) return
    let disposed = false
    const ws = new WebSocket(
      `${getWsBase()}/ws/${sessionCode}?participant_id=${role === 'host' ? 'host' : 'joining'}`
    )
    wsRef.current = ws
    ws.onopen = () => {
      if (disposed) ws.close()
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'company_dna_ready') {
          setDna(msg.dna)
          if (role === 'host') setIsReviewing(true)
        }
        if (msg.type === 'participant_profile_ready' && msg.participant_id === session?.participant_id) {
          setProfile(msg.profile)
          setIsReviewing(true)
        }
      } catch (err) {
        console.error('WS Error:', err)
      }
    }

    return () => {
      disposed = true
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CLOSING) {
        ws.close()
      }
    }
  }, [sessionCode, getWsBase, role, session?.participant_id])

  const activeRole = selectedRole === 'Other' ? (customRole.trim() || 'Other') : selectedRole
  const isFormValid = Boolean(name.trim() && activeRole && linkedinUrl.trim())
  const avatarReady = Boolean(activeRole && linkedinUrl.trim())

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
          role: activeRole,
          department: activeRole,
          top_challenge: `LinkedIn provided for ${activeRole}`,
          ai_confidence: 3,
          conversation: [],
          linkedin_url: linkedinUrl,
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

  const handleConfirm = async () => {
    setLoading(true)
    setError(null)
    try {
      if (role === 'host' && dna) {
        await api(`/session/${sessionCode}/dna`, {
          method: 'POST',
          body: JSON.stringify(dna),
        })
      } else if (profile) {
        await api(`/participant/${session?.participant_id}/profile`, {
          method: 'POST',
          body: JSON.stringify(profile),
        })
        setName(profile.name)
        setSelectedRole(profile.role)
      }
      setIsReviewing(false)
    } catch {
      setError('Could not save your confirmation. Please try again.')
    } finally {
      setLoading(false)
    }
  }

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
            <input className="input" style={{ fontSize: 28, letterSpacing: '0.2em', textAlign: 'center', textTransform: 'uppercase' }} maxLength={6} placeholder="AB12CD" value={sessionCode} onChange={e => setSessionCode(e.target.value.toUpperCase())} onKeyDown={e => e.key === 'Enter' && handleCodeSubmit()} autoFocus />
          </div>
          {error && <div className="error-banner">{error}</div>}
          <div className="phase-footer" style={{ marginTop: 'auto' }}>
            <div />
            <button className="btn btn-primary" onClick={handleCodeSubmit} disabled={loading || !sessionCode.trim()}>
              {loading ? <><span className="spinner" /> Checking...</> : 'Join ->'}
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
                {resolvedSession.company} | {resolvedSession.code}
              </span>
            </div>
          )}

          <div className="phase-body">
            {isReviewing ? (
              <div className="review-step fade-up">
                <div className="phase-title-block">
                  <span className="badge badge-accent">Review Required</span>
                  <h2 className="phase-title">Confirm {role === 'host' ? 'Company DNA' : 'Your Profile'}</h2>
                  <p className="phase-desc">Our AI has researched the details below. Please correct anything that isn't accurate.</p>
                </div>
                <div className="phase-form">
                  {role === 'host' && dna && (
                    <>
                      <div className="input-group">
                        <label className="input-label">Vision</label>
                        <textarea className="input" rows={3} value={dna.vision} onChange={e => setDna({ ...dna, vision: e.target.value })} />
                      </div>
                      <div className="input-group">
                        <label className="input-label">Key Goals (Comma separated)</label>
                        <input className="input" value={dna.goals.join(', ')} onChange={e => setDna({ ...dna, goals: e.target.value.split(',').map(s => s.trim()) })} />
                      </div>
                    </>
                  )}
                  {role !== 'host' && profile && (
                    <>
                      <div className="input-group">
                        <label className="input-label">Identified Role</label>
                        <input className="input" value={profile.role} onChange={e => setProfile({ ...profile, role: e.target.value })} />
                      </div>
                      <div className="input-group">
                        <label className="input-label">Profile Summary</label>
                        <textarea className="input" rows={3} value={profile.summary} onChange={e => setProfile({ ...profile, summary: e.target.value })} />
                      </div>
                    </>
                  )}
                </div>
                <div className="phase-footer" style={{ marginTop: 24 }}>
                  <button className="btn btn-primary btn-block" onClick={handleConfirm} disabled={loading}>
                    {loading ? 'Saving...' : 'Confirm and Continue ->'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="phase-form">
                <div className="phase-title-block">
                  <span className="badge badge-accent">Your Profile</span>
                  <h2 className="phase-title">Tell us about<br />yourself</h2>
                  <p className="phase-desc">Enter the basics first, then continue through the avatar-guided onboarding flow.</p>
                </div>

                <div className="input-group">
                  <label className="input-label">Full name</label>
                  <input className="input" placeholder="Your name" value={name} onChange={e => setName(e.target.value)} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="input-group">
                    <label className="input-label">Your role</label>
                    <select className="input" value={selectedRole} onChange={e => setSelectedRole(e.target.value)}>
                      <option value="">Select role...</option>
                      {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </div>
                  {selectedRole === 'Other' && (
                    <div className="input-group fade-in">
                      <label className="input-label">Custom Role Name</label>
                      <input className="input" placeholder="e.g. Sales Manager" value={customRole} onChange={e => setCustomRole(e.target.value)} autoFocus />
                    </div>
                  )}
                  <div className="input-group">
                    <label className="input-label">LinkedIn (Optional)</label>
                    <input className="input" placeholder="https://linkedin.com/..." value={linkedinUrl} onChange={e => setLinkedinUrl(e.target.value)} />
                  </div>
                </div>

                {activeRole && !avatarReady && (
                  <div className="input-group">
                    <label className="input-label">Next window: avatar guide</label>
                    <div className="live-avatar-help">
                      Add your LinkedIn URL and the avatar will open in the next step with the first question.
                    </div>
                  </div>
                )}

                {avatarReady && (
                  <div className="input-group">
                    <label className="input-label">
                      Next window: avatar guide
                      <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--accent)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>HeyGen Live</span>
                    </label>
                    <AvatarGuidedOnboarding
                      api={api}
                      sessionCode={resolvedSession?.code || sessionCode}
                      name={name}
                      role={activeRole}
                      linkedinUrl={linkedinUrl}
                    />
                  </div>
                )}

                {error && <div className="error-banner">{error}</div>}

                <div className="phase-footer" style={{ marginTop: 32 }}>
                  <button className="btn btn-ghost" onClick={onBack}>Back</button>
                  <button className="btn btn-primary" onClick={handleJoin} disabled={!isFormValid || loading}>
                    {loading ? <><span className="spinner" /> Joining...</> : 'Enter Workshop ->'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
