import React, { useState, useEffect } from 'react';

const TAGS = [
  'Repetitive', 'Time-consuming', 'Manual', 'Error-prone',
  'Slow decision-making', 'Data scattered', 'No visibility',
  'Customer-facing', 'Compliance risk'
];

const SEV_COLORS = { 1: '#5a6a7a', 2: '#f0a830', 3: '#f0a830', 4: '#ff7a50', 5: '#f04848' };
const SEV_LABELS = { 1: 'Minor', 2: 'Low', 3: 'Medium', 4: 'High', 5: 'Critical' };

const STEPS = [
  { num: 1, name: 'Submit Problems' },
  { num: 2, name: 'Problem Clusters' },
];

const emptyProblem = () => ({
  id: Date.now(), text: '', tags: [], severity: 3, department: ''
});

function Phase3_Problems({ api, getWsBase, session, participant, mode, onComplete }) {
  const [step, setStep] = useState(1);
  const [problems, setProblems] = useState([emptyProblem()]);
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [liveCount, setLiveCount] = useState(0);

  useEffect(() => {
    if (step === 2 && session) {
      const ws = new WebSocket(`${getWsBase()}/ws/${session.code}`);
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'problem_clusters') setClusters(msg.data);
        if (msg.type === 'problems_count') setLiveCount(msg.count);
      };
      return () => ws.close();
    }
  }, [step, session]);

  const updateProblem = (id, field, value) => {
    setProblems(problems.map(p => p.id === id ? { ...p, [field]: value } : p));
  };

  const toggleTag = (id, tag) => {
    setProblems(problems.map(p => {
      if (p.id !== id) return p;
      return { ...p, tags: p.tags.includes(tag) ? p.tags.filter(t => t !== tag) : [...p.tags, tag] };
    }));
  };

  const removeProblem = (id) => setProblems(problems.filter(p => p.id !== id));
  const addProblem = () => { if (problems.length < 5) setProblems([...problems, emptyProblem()]); };

  const validCount = problems.filter(p => p.text.length > 10).length;

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const data = await api('/phase/problems', {
        method: 'POST',
        body: JSON.stringify({
          session_code: session.code,
          participant_id: participant?.id,
          problems: problems.filter(p => p.text.length > 10)
        })
      });
      setClusters(data.clusters || []);
      setStep(2);
    } catch { alert('Error submitting problems.'); }
    finally { setLoading(false); }
  };

  return (
    <div className="phase-shell fade-up">
      <header className="phase-header">
        <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-ind-dot"></div>
          <span className="phase-ind-label">Phase 3 — Problems</span>
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
        <span className="live-text">{liveCount || problems.length} problems submitted</span>
      </div>

      <main className="phase-body">
        {step === 1 && (
          <div className="fade-up">
            <div className="phase-title-block">
              <h1 className="phase-title">Problem Discovery</h1>
              <p className="phase-desc">What slows you down in your own work? (Specific and tactical pain points)</p>
            </div>

            <div className="problems-list">
              {problems.map((p, idx) => (
                <div key={p.id} className="problem-card">
                  <div className="problem-header">
                    <span className="problem-num">Problem {idx + 1}</span>
                    {problems.length > 1 && (
                      <button className="remove-btn" onClick={() => removeProblem(p.id)}>✕</button>
                    )}
                  </div>
                  <textarea className="input" rows="3" placeholder="Describe the specific task or workflow bottleneck..."
                    value={p.text} onChange={e => updateProblem(p.id, 'text', e.target.value)} />

                  <div>
                    <span className="input-label" style={{ marginBottom: '8px', display: 'block' }}>Characteristics:</span>
                    <div className="tag-group">
                      {TAGS.map(tag => (
                        <button key={tag} className={`tag-btn ${p.tags.includes(tag) ? 'selected' : ''}`}
                          onClick={() => toggleTag(p.id, tag)}>{tag}</button>
                      ))}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="input-label">Severity:</span>
                    <div className="severity-track">
                      {[1,2,3,4,5].map(s => (
                        <button key={s} className={`severity-btn ${p.severity === s ? 'selected' : ''}`}
                          style={{
                            borderColor: p.severity === s ? SEV_COLORS[s] : 'var(--border)',
                            color: p.severity === s ? SEV_COLORS[s] : 'var(--text-3)'
                          }}
                          onClick={() => updateProblem(p.id, 'severity', s)}>{s}</button>
                      ))}
                    </div>
                    <span className="severity-desc" style={{ color: SEV_COLORS[p.severity] }}>
                      {SEV_LABELS[p.severity]}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {problems.length < 5 && (
              <button className="add-btn-dashed" onClick={addProblem}>+ Add another problem</button>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="fade-up">
            <div className="phase-title-block">
              <span className="badge badge-accent">Detection Engine</span>
              <h1 className="phase-title">Emerging Patterns</h1>
              <p className="phase-desc">The AI is clustering your team's pain points into core problem areas.</p>
            </div>

            {clusters.length > 0 ? clusters.map((c, i) => (
              <div key={i} className="insight-cluster fade-up">
                <div className="cluster-header">
                  <span className="cluster-icon">{c.icon || '◈'}</span>
                  <span className="cluster-theme">{c.theme || c.title}</span>
                  <span className="badge badge-amber">{c.count || 0} Mentions</span>
                  {c.cross_department && <span className="badge badge-green">Cross-dept ⬡</span>}
                </div>
                <p className="cluster-summary">{c.description || c.summary}</p>
                {c.departments && (
                  <div className="cluster-depts">
                    {c.departments.map(d => <span key={d} className="chip chip-dim">{d}</span>)}
                  </div>
                )}
                {c.avg_severity && (
                  <div className="severity-bar-row">
                    <span className="input-label">Severity</span>
                    <div className="severity-bar-track">
                      <div className="severity-bar-fill" style={{ width: `${(c.avg_severity / 5) * 100}%` }}></div>
                    </div>
                    <span className="severity-bar-val">{c.avg_severity}/5</span>
                  </div>
                )}
                <div className="cluster-potential">
                  <span className="potential-label">AI Opportunity →</span>
                  <span className="potential-text">{c.potential || c.ai_opportunity || 'Automation potential detected'}</span>
                </div>
              </div>
            )) : (
              <div className="ai-thinking">
                <div className="thinking-dots">
                  <div className="thinking-dot"></div><div className="thinking-dot"></div><div className="thinking-dot"></div>
                </div>
                <div className="thinking-label">Clustering problems</div>
                <div className="thinking-sub">Analyzing operational data...</div>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="phase-footer">
        <button className="btn btn-ghost" onClick={() => step > 1 ? setStep(1) : null}>← Back</button>
        {step === 1 ? (
          <button className="btn btn-primary" disabled={validCount === 0 || loading} onClick={handleSubmit}>
            {loading ? <div className="spinner"></div> : `Analyze ${validCount} Problem${validCount !== 1 ? 's' : ''} →`}
          </button>
        ) : (
          <button className="btn btn-primary" onClick={onComplete}>Proceed to Data Audit →</button>
        )}
      </footer>
    </div>
  );
}

export default Phase3_Problems;
