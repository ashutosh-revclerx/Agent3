import React, { useState, useEffect } from 'react';

const OBJECTIVES = [
  { id: 'revenue', icon: '◆', label: 'Revenue Growth', desc: 'Increase sales, expand markets' },
  { id: 'efficiency', icon: '◈', label: 'Operational Efficiency', desc: 'Reduce costs, streamline processes' },
  { id: 'cx', icon: '◎', label: 'Customer Experience', desc: 'Improve satisfaction & retention' },
  { id: 'innovation', icon: '⬡', label: 'Product Innovation', desc: 'Launch new products or features' },
  { id: 'talent', icon: '◉', label: 'Talent & Productivity', desc: 'Empower teams, reduce manual work' },
  { id: 'risk', icon: '▣', label: 'Risk & Compliance', desc: 'Reduce errors, improve governance' },
  { id: 'insights', icon: '◇', label: 'Data & Insights', desc: 'Better decisions from data' },
  { id: 'scaling', icon: '⬢', label: 'Scaling Operations', desc: 'Grow without proportional cost' },
];

const GROWTH = [
  'Entering new markets',
  'Increasing revenue per customer',
  'Launching new products or services',
  'Improving customer retention',
  'Reducing operational costs',
  'Automating manual workflows',
  'Improving data quality & access',
  'Building AI capabilities in-house',
];

const STEPS = [
  { num: 1, name: 'Objectives' },
  { num: 2, name: 'Growth' },
  { num: 3, name: 'Challenges' },
  { num: 4, name: 'Insights' },
];

function Phase2_Context({ api, getWsBase, session, participant, mode, onComplete }) {
  const [step, setStep] = useState(1);
  const [objectives, setObjectives] = useState([]);
  const [growth, setGrowth] = useState([]);
  const [challenges, setChallenges] = useState('');
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [liveCount, setLiveCount] = useState(0);

  useEffect(() => {
    if (step === 4 && session) {
      const ws = new WebSocket(`${getWsBase()}/ws/${session.code}`);
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'objective_map') setInsights(msg.data);
        if (msg.type === 'context_count') setLiveCount(msg.count);
      };
      return () => ws.close();
    }
  }, [step, session]);

  const toggle = (arr, set, id) => set(arr.includes(id) ? arr.filter(i => i !== id) : [...arr, id]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const data = await api('/phase/context', {
        method: 'POST',
        body: JSON.stringify({
          session_code: session.code,
          participant_id: participant?.id,
          objectives, growth_areas: growth, challenges
        })
      });
      setInsights(data.objective_map);
      setStep(4);
    } catch { alert('Error submitting context.'); }
    finally { setLoading(false); }
  };

  const next = () => { if (step < 3) setStep(step + 1); else handleSubmit(); };
  const canContinue = (step === 1 && objectives.length > 0) || (step === 2 && growth.length > 0) || (step === 3 && challenges.length > 20);

  return (
    <div className="phase-shell fade-up">
      <header className="phase-header">
        <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-ind-dot"></div>
          <span className="phase-ind-label">Phase 2 — Context</span>
        </div>
      </header>

      <div className="step-track">
        {STEPS.map(s => (
          <div key={s.num} className={`step-item ${step === s.num ? 'active' : ''} ${step > s.num ? 'done' : ''}`}>
            <div className="step-dot">{step > s.num ? '✓' : s.num}</div>
            <span className="step-name">{s.name}</span>
          </div>
        ))}
      </div>

      <div className="live-bar">
        <div className="live-dot pulse"></div>
        <span className="live-text">{liveCount} participants submitted</span>
      </div>

      <main className="phase-body">
        {step === 1 && (
          <div className="fade-up">
            <div className="phase-title-block">
              <h1 className="phase-title">Strategic Objectives</h1>
              <p className="phase-desc">What are the 2-3 most critical goals for your organization this year?</p>
            </div>
            <div className="objective-grid">
              {OBJECTIVES.map(o => (
                <div key={o.id} className={`objective-card ${objectives.includes(o.id) ? 'selected' : ''}`}
                  onClick={() => toggle(objectives, setObjectives, o.id)}>
                  <span className="obj-icon">{o.icon}</span>
                  <span className="obj-label">{o.label}</span>
                  <span className="obj-check" style={{ visibility: objectives.includes(o.id) ? 'visible' : 'hidden' }}>✓</span>
                  <span className="obj-desc">{o.desc}</span>
                </div>
              ))}
            </div>
            <p className="selected-count">{objectives.length} selected</p>
          </div>
        )}

        {step === 2 && (
          <div className="fade-up">
            <div className="phase-title-block">
              <h1 className="phase-title">Growth Priorities</h1>
              <p className="phase-desc">Where is the organization focused on expanding or improving?</p>
            </div>
            <div className="growth-list">
              {GROWTH.map(g => (
                <div key={g} className={`growth-item ${growth.includes(g) ? 'selected' : ''}`}
                  onClick={() => toggle(growth, setGrowth, g)}>
                  <div className="growth-check">{growth.includes(g) ? '✓' : '○'}</div>
                  <span className="growth-label">{g}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="fade-up">
            <div className="phase-title-block">
              <h1 className="phase-title">Strategic Blockers</h1>
              <p className="phase-desc">What's holding your company back strategically? (Big picture context)</p>
            </div>
            <div className="input-group">
              <textarea className="input" rows="6" placeholder="Describe the most significant organizational blockers..."
                value={challenges} onChange={e => setChallenges(e.target.value)} />
              <span className="input-hint" style={{ textAlign: 'right' }}>{challenges.length} characters</span>
            </div>
            <div className="summary-card">
              <div className="summary-title">Your Selections</div>
              <div className="summary-chips">
                {objectives.map(id => {
                  const o = OBJECTIVES.find(x => x.id === id);
                  return <span key={id} className="chip">{o?.label}</span>;
                })}
                {growth.map(g => <span key={g} className="chip chip-green">{g}</span>)}
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="fade-up">
            <div className="phase-title-block">
              <span className="badge badge-accent">Objective Map</span>
              <h1 className="phase-title">Strategic Alignment</h1>
              <p className="phase-desc">We've clustered your team's inputs. Here are the dominant themes for {session?.company}.</p>
            </div>

            {insights ? (
              <>
                {insights.clusters?.map((c, i) => (
                  <div key={i} className="insight-cluster fade-up">
                    <div className="cluster-header">
                      <span className="cluster-icon">{c.icon || '◈'}</span>
                      <span className="cluster-theme">{c.theme}</span>
                      <span className="badge badge-default">{c.signals || 0} Signals</span>
                    </div>
                    <p className="cluster-summary">{c.summary}</p>
                    <div className="cluster-potential">
                      <span className="potential-label">AI Opportunity →</span>
                      <span className="potential-text">{c.potential || 'High automation potential detected'}</span>
                    </div>
                  </div>
                ))}
                {insights.dominantTheme && (
                  <div className="dominant-theme-box">
                    <div className="dominant-theme-label">Dominant Theme</div>
                    <div className="dominant-theme-value">{insights.dominantTheme}</div>
                  </div>
                )}
              </>
            ) : (
              <div className="ai-thinking">
                <div className="thinking-dots">
                  <div className="thinking-dot"></div>
                  <div className="thinking-dot"></div>
                  <div className="thinking-dot"></div>
                </div>
                <div className="thinking-label">Synthesizing team inputs</div>
                <div className="thinking-sub">Building objective map...</div>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="phase-footer">
        <button className="btn btn-ghost" onClick={() => step > 1 ? setStep(step - 1) : null}>← Back</button>
        {step < 4 ? (
          <button className="btn btn-primary" disabled={!canContinue || loading} onClick={next}>
            {loading ? <div className="spinner"></div> : step === 3 ? 'Synthesize Insights →' : 'Continue →'}
          </button>
        ) : (
          <button className="btn btn-primary" onClick={onComplete}>Proceed to Problem Discovery →</button>
        )}
      </footer>
    </div>
  );
}

export default Phase2_Context;
