import React, { useState, useEffect } from 'react';

const LEVELS = [
  { n: 1, label: 'Skeptical', desc: 'Not convinced AI is relevant to my work', color: 'var(--red)' },
  { n: 2, label: 'Curious', desc: 'Interested but have limited knowledge', color: 'var(--amber)' },
  { n: 3, label: 'Informed', desc: 'Understand basics, exploring use cases', color: '#ffda6b' },
  { n: 4, label: 'Practitioner', desc: 'Have used or deployed AI tools', color: 'var(--green)' },
  { n: 5, label: 'Expert', desc: 'Deep AI knowledge, hands-on experience', color: 'var(--accent)' },
];

const CONCERNS = [
  { id: 'job', icon: '◎', label: 'Job Replacement', desc: 'AI might replace roles in our team' },
  { id: 'security', icon: '▣', label: 'Data Security', desc: 'Sensitive data going into AI systems' },
  { id: 'cost', icon: '◆', label: 'Implementation Cost', desc: 'AI projects being too expensive' },
  { id: 'accuracy', icon: '◈', label: 'Accuracy & Reliability', desc: 'AI making wrong decisions' },
  { id: 'privacy', icon: '⬡', label: 'Privacy & Compliance', desc: 'GDPR, data residency concerns' },
  { id: 'complexity', icon: '◇', label: 'Complexity', desc: 'Too hard to implement and maintain' },
  { id: 'buyin', icon: '◉', label: 'Team Buy-in', desc: 'Getting people to actually use AI tools' },
  { id: 'quality', icon: '⬢', label: 'Data Quality', desc: "Our data isn't good enough for AI" },
];

function ActivityB_Confidence({ api, getWsBase, session, participant, mode, onComplete }) {
  const [confidence, setConfidence] = useState(null);
  const [concerns, setConcerns] = useState([]);
  const [expectations, setExpectations] = useState('');
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session?.code) return;
    const ws = new WebSocket(`${getWsBase()}/ws/${session.code}?participant_id=${participant?.id || 'host'}`);
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'team_confidence_profile') setProfile(msg.data);
      } catch {}
    };
    return () => ws.close();
  }, [getWsBase, participant?.id, session?.code]);

  const toggleConcern = (id) => setConcerns(concerns.includes(id) ? concerns.filter(c => c !== id) : [...concerns, id]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const data = await api('/activity/confidence', {
        method: 'POST',
        body: JSON.stringify({
          session_code: session.code,
          participant_id: participant?.id,
          confidence_level: confidence, concerns, expectations
        })
      });
      setProfile(data);
    } catch { alert('Error submitting confidence data.'); }
    finally { setLoading(false); }
  };

  const selected = LEVELS.find(l => l.n === confidence);

  if (profile) {
    return (
      <div className="phase-shell fade-up">
        <header className="phase-header">
          <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
          <div className="phase-indicator">
            <div className="phase-ind-dot"></div>
            <span className="phase-ind-label">Activity B — Confidence</span>
          </div>
        </header>

        <main className="phase-body">
          <div className="phase-title-block">
            <span className="badge badge-green">Analysis Complete</span>
            <h1 className="phase-title">Team Confidence Profile</h1>
          </div>

          <div className="confidence-dist">
            {LEVELS.map(l => (
              <div key={l.n} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ width: '80px', fontSize: '11px', color: l.color, fontWeight: 600 }}>{l.label}</span>
                <div className="severity-bar-track" style={{ flex: 1 }}>
                  <div className="severity-bar-fill" style={{
                    width: `${(profile.distribution?.[l.n] || 0) * 100}%`,
                    background: l.color
                  }}></div>
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-2)', minWidth: '24px' }}>
                  {profile.distribution?.[l.n] || 0}
                </span>
              </div>
            ))}
          </div>

          <div className="tone-adaptation-box">
            <span style={{ fontSize: '22px' }}>◈</span>
            <div>
              <div style={{ fontFamily: 'var(--font-h)', fontWeight: 700, fontSize: '13px', color: 'var(--text)' }}>
                AI has adapted its approach
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-2)', lineHeight: '1.6', marginTop: '4px' }}>
                {profile.tone_adaptation || "AI-generated content has been tuned to match the team's collective confidence level."}
              </div>
            </div>
          </div>

          {profile.top_concerns && (
            <div className="insight-cluster">
              <div className="cluster-header">
                <span className="cluster-icon">◈</span>
                <span className="cluster-theme">Top Concerns</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {profile.top_concerns.map(c => <span key={c} className="chip">{c}</span>)}
              </div>
            </div>
          )}
        </main>

        <footer className="phase-footer">
          <div></div>
          <button className="btn btn-primary" onClick={onComplete}>Proceed to Activity C →</button>
        </footer>
      </div>
    );
  }

  return (
    <div className="phase-shell fade-up">
      <header className="phase-header">
        <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-ind-dot"></div>
          <span className="phase-ind-label">Activity B — Confidence</span>
        </div>
      </header>

      <main className="phase-body">
        <div className="phase-title-block">
          <h1 className="phase-title">AI Confidence Spectrum</h1>
          <p className="phase-desc">Your honest assessment helps the AI calibrate its recommendations to your experience level.</p>
        </div>

        <div>
          <span className="input-label" style={{ marginBottom: '10px', display: 'block' }}>Your AI confidence level</span>
          <div className="spectrum-track">
            {LEVELS.map(l => (
              <button key={l.n} className={`spectrum-btn ${confidence === l.n ? 'selected' : ''}`}
                onClick={() => setConfidence(l.n)}
                style={{ borderColor: confidence === l.n ? l.color : 'var(--border)' }}>
                <span className="spectrum-num" style={{ color: confidence === l.n ? l.color : 'var(--text-3)' }}>{l.n}</span>
                <span className="spectrum-label">{l.label}</span>
              </button>
            ))}
          </div>
          {selected && (
            <div className="spectrum-desc" style={{ borderLeft: `2px solid ${selected.color}`, marginTop: '12px' }}>
              {selected.desc}
            </div>
          )}
        </div>

        <div>
          <span className="input-label" style={{ marginBottom: '10px', display: 'block' }}>What concerns you most about AI?</span>
          <div className="concerns-grid">
            {CONCERNS.map(c => (
              <div key={c.id} className={`concern-card ${concerns.includes(c.id) ? 'selected' : ''}`}
                onClick={() => toggleConcern(c.id)}>
                <span className="concern-icon">{c.icon}</span>
                <span className="concern-label">{c.label}</span>
                <span className="concern-desc">{c.desc}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="input-group">
          <label className="input-label">What would success look like for you? (optional)</label>
          <textarea className="input" rows="3" placeholder="Describe your ideal AI outcome..."
            value={expectations} onChange={e => setExpectations(e.target.value)} />
        </div>
      </main>

      <footer className="phase-footer">
        <div></div>
        <button className="btn btn-primary" disabled={!confidence || loading} onClick={handleSubmit}>
          {loading ? <div className="spinner"></div> : 'Submit & View Profile →'}
        </button>
      </footer>
    </div>
  );
}

export default ActivityB_Confidence;
