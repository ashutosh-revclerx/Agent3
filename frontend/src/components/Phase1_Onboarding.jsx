import React, { useState } from 'react';

const ROLES = [
  'CEO/Founder', 'CTO/Technology Leader', 'COO/Operations',
  'Product Manager', 'Data/AI Engineer', 'Business Analyst',
  'Department Head', 'Consultant', 'Other'
];

const FAMILIARITY = [
  { level: 1, label: 'Getting Started', desc: 'New to AI tools and their capabilities' },
  { level: 3, label: 'Intermediate', desc: 'Have used some AI tools for specific tasks' },
  { level: 5, label: 'Regular User', desc: 'Work with AI tools deeply and regularly' },
];

const cleanCode = (value) => value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);

function Phase1_Onboarding({ api, session, role, onComplete, onBack }) {
  const [sub, setSub] = useState(role === 'participant' && !session ? 'CODE' : 'PROFILE');
  const [code, setCode] = useState('');
  const [currentSession, setCurrentSession] = useState(session);
  const [form, setForm] = useState({
    name: '', role: '', department: '', top_challenge: '',
    ai_confidence: 3
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleValidateCode = async () => {
    const cleaned = cleanCode(code);
    setCode(cleaned);
    if (cleaned.length !== 6) { setError('Enter the 6-character code shown by the host.'); return; }
    setLoading(true); setError('');
    try {
      const data = await api(`/session/${cleaned}`);
      setCurrentSession(data);
      setSub('PROFILE');
    } catch {
      setError('Invalid session code or session not found.');
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async () => {
    setLoading(true); setError('');
    try {
      const data = await api('/participant/join', {
        method: 'POST',
        body: JSON.stringify({
          session_code: currentSession.code,
          ...form
        })
      });
      onComplete({ participant: data, session: currentSession });
    } catch {
      setError('Error joining session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (sub === 'CODE') {
    return (
      <div className="phase-shell fade-up">
        <header className="phase-header">
          <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
          <div className="phase-indicator">
            <div className="phase-ind-dot"></div>
            <span className="phase-ind-label">Join Session</span>
          </div>
        </header>
        <main className="phase-body" style={{ justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
          <span className="badge badge-accent">Participant Join</span>
          <h1 className="phase-title">Enter Session Code</h1>
          <p className="phase-desc">Check your email or host screen for the 6-character code.</p>
          <input className="input" style={{ fontSize: '28px', letterSpacing: '0.2em', textAlign: 'center', textTransform: 'uppercase', maxWidth: '280px' }}
            maxLength={6} placeholder="000000" value={code}
            onChange={e => setCode(cleanCode(e.target.value))} autoFocus
            onKeyDown={e => e.key === 'Enter' && handleValidateCode()} />
          {error && <div className="error-banner">{error}</div>}
          <button className="btn btn-primary" disabled={code.length < 4 || loading} onClick={handleValidateCode}>
            {loading ? <div className="spinner"></div> : 'Find Session'}
          </button>
        </main>
        <footer className="phase-footer">
          <button className="btn btn-ghost" onClick={onBack}>← Back</button>
          <div></div>
        </footer>
      </div>
    );
  }

  const profileValid = form.name && form.role && form.department;

  return (
    <div className="phase-shell fade-up">
      <header className="phase-header">
        <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-ind-dot"></div>
          <span className="phase-ind-label">Phase 1 — Onboarding</span>
        </div>
      </header>

      <main className="phase-body">
        {currentSession && (
          <div className="session-code-box">
            <span className="session-code-label">Active Session</span>
            <span className="session-code-value">{currentSession.code}</span>
            <div className="info-card" style={{ marginTop: '8px' }}>
              <div className="info-row"><span className="info-key">Company</span><span className="info-val">{currentSession.company}</span></div>
              <div className="info-row"><span className="info-key">Industry</span><span className="info-val">{currentSession.industry}</span></div>
              <div className="info-row"><span className="info-key">Duration</span><span className="info-val">{currentSession.duration_mins} min</span></div>
            </div>
            {role === 'host' && <span className="session-code-hint">Share this code with participants</span>}
          </div>
        )}

        <div className="phase-title-block">
          <h1 className="phase-title">Complete your profile</h1>
        </div>

        <div className="phase-form">
          <div className="input-group">
            <label className="input-label">Full Name</label>
            <input className="input" placeholder="e.g. Jordan Smith"
              value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
          </div>

          <div className="grid-2">
            <div className="input-group">
              <label className="input-label">Your Role</label>
              <select className="input" value={form.role}
                onChange={e => setForm({...form, role: e.target.value})}>
                <option value="" disabled>Select role...</option>
                {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label className="input-label">Department</label>
              <input className="input" placeholder="e.g. Engineering"
                value={form.department} onChange={e => setForm({...form, department: e.target.value})} />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Top challenge you're facing</label>
            <textarea className="input" rows={3} placeholder="e.g. Streamlining reporting, reducing manual work..."
              value={form.top_challenge} onChange={e => setForm({...form, top_challenge: e.target.value})} />
          </div>

          <div className="input-group">
            <label className="input-label">How familiar are you with AI tools?</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {FAMILIARITY.map(c => (
                <button key={c.level} type="button" onClick={() => setForm({...form, ai_confidence: c.level})}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '16px', padding: '14px 16px',
                    background: form.ai_confidence === c.level ? 'var(--accent-glow)' : 'var(--bg-card)',
                    border: form.ai_confidence === c.level ? '0.5px solid var(--accent-soft)' : '0.5px solid var(--border)',
                    borderRadius: 'var(--r-md)', textAlign: 'left', cursor: 'pointer',
                    transition: 'all var(--t)',
                    boxShadow: form.ai_confidence === c.level ? 'var(--shadow-glow)' : 'none'
                  }}>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'var(--font-h)',
                      color: form.ai_confidence === c.level ? 'var(--text)' : 'var(--text-2)' }}>{c.label}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-3)' }}>{c.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {error && <div className="error-banner">{error}</div>}
        </div>
      </main>

      <footer className="phase-footer">
        <button className="btn btn-ghost" onClick={() => {
          if (sub === 'PROFILE' && role === 'participant' && !session) setSub('CODE');
          else onBack();
        }}>← Back</button>
        <button className="btn btn-primary" disabled={!profileValid || loading} onClick={handleJoin}>
          {loading ? <div className="spinner"></div> : 'Enter Workshop →'}
        </button>
      </footer>
    </div>
  );
}

export default Phase1_Onboarding;
