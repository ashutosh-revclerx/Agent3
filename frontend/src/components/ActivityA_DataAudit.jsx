import React, { useState } from 'react';

const DATASETS = [
  { id: 'customer', label: 'Customer Data', desc: 'CRM, contacts, purchase history' },
  { id: 'sales', label: 'Sales & Revenue Data', desc: 'Pipeline, forecasts, invoices' },
  { id: 'support', label: 'Support / Tickets', desc: 'Helpdesk, emails, chat logs' },
  { id: 'ops', label: 'Operations Data', desc: 'Process logs, workflows, SLAs' },
  { id: 'finance', label: 'Financial Data', desc: 'P&L, budgets, expenses' },
  { id: 'hr', label: 'HR / People Data', desc: 'Headcount, performance, payroll' },
  { id: 'product', label: 'Product / Usage Data', desc: 'Feature usage, analytics, logs' },
  { id: 'marketing', label: 'Marketing Data', desc: 'Campaigns, leads, attribution' },
];

const DIMENSIONS = [
  { key: 'location', title: 'Location', sub: 'Where does this data live?',
    opts: ['Scattered/unknown', 'Multiple silos', 'One system hard access', 'Centralised accessible'] },
  { key: 'quality', title: 'Quality', sub: 'How clean and reliable is it?',
    opts: ['Full of errors', 'Inconsistent', 'Mostly clean', 'Clean standardised'] },
  { key: 'history', title: 'History', sub: 'How much historical data exists?',
    opts: ['< 3 months', '3–12 months', '1–3 years', '3+ years'] },
  { key: 'ownership', title: 'Ownership', sub: 'Who controls and maintains it?',
    opts: ['No owner', 'Owned rarely updated', 'Owned some governance', 'Clear owner governed'] },
];

const STEPS = [
  { num: 1, name: 'Select Datasets' },
  { num: 2, name: 'Score Each One' },
  { num: 3, name: 'Readiness Map' },
];

function ActivityA_DataAudit({ api, session, participant, mode, onComplete }) {
  const [step, setStep] = useState(1);
  const [selected, setSelected] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [scores, setScores] = useState({});
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const toggleDs = (id) => setSelected(selected.includes(id) ? selected.filter(i => i !== id) : [...selected, id]);

  const setDimScore = (dsId, dimKey, val) => {
    setScores(prev => ({
      ...prev,
      [dsId]: { ...(prev[dsId] || {}), [dimKey]: val }
    }));
  };

  const currentDs = DATASETS.find(d => d.id === selected[currentIdx]);
  const currentScores = scores[selected[currentIdx]] || {};
  const allDimensionsScored = DIMENSIONS.every(d => currentScores[d.key]);

  const nextDataset = () => {
    if (currentIdx < selected.length - 1) setCurrentIdx(currentIdx + 1);
    else handleSubmit();
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const datasets = selected.map(id => {
        const ds = DATASETS.find(d => d.id === id);
        const sc = scores[id] || {};
        const vals = Object.values(sc);
        const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
        return { dataset: id, label: ds.label, scores: sc, readiness: Math.round(avg * 10) / 10 };
      });
      const data = await api('/activity/data-audit', {
        method: 'POST',
        body: JSON.stringify({ session_code: session.code, participant_id: participant?.id, datasets })
      });
      setResults(data);
      setStep(3);
    } catch { alert('Error submitting audit.'); }
    finally { setLoading(false); }
  };

  const getColor = (score) => score >= 3.5 ? 'var(--green)' : score >= 2.5 ? 'var(--amber)' : '#ff7a50';

  return (
    <div className="phase-shell fade-up">
      <header className="phase-header">
        <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-ind-dot"></div>
          <span className="phase-ind-label">Activity A — Data Audit</span>
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

      <main className="phase-body">
        {step === 1 && (
          <div className="fade-up">
            <div className="phase-title-block">
              <h1 className="phase-title">Select Datasets</h1>
              <p className="phase-desc">Which data sources are relevant to your AI ambitions?</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {DATASETS.map(ds => (
                <div key={ds.id} className={`dataset-card ${selected.includes(ds.id) ? 'selected' : ''}`}
                  onClick={() => toggleDs(ds.id)}>
                  <div style={{ flex: 1 }}>
                    <span className="ds-name">{ds.label}</span>
                    <div className="ds-desc">{ds.desc}</div>
                  </div>
                  <span className="ds-check">✓</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === 2 && currentDs && (
          <div className="fade-up">
            <div style={{ display: 'flex', gap: '6px', marginBottom: '20px', flexWrap: 'wrap' }}>
              {selected.map((id, i) => (
                <span key={id} className={`ds-pill ${i === currentIdx ? 'active' : i < currentIdx ? 'done' : ''}`}>
                  {i < currentIdx ? '✓' : ''} {DATASETS.find(d => d.id === id)?.label}
                </span>
              ))}
            </div>

            <div className="phase-title-block">
              <h1 className="phase-title">{currentDs.label}</h1>
              <p className="phase-desc">{currentDs.desc}</p>
            </div>

            {DIMENSIONS.map(dim => (
              <div key={dim.key} className="dimension-card">
                <div className="dim-title">{dim.title}</div>
                <div className="dim-subtitle">{dim.sub}</div>
                <div className="dim-options">
                  {dim.opts.map((opt, i) => (
                    <div key={i} className={`dim-option ${currentScores[dim.key] === i + 1 ? 'selected' : ''}`}
                      onClick={() => setDimScore(selected[currentIdx], dim.key, i + 1)}>
                      <div className="dim-num">{i + 1}</div>
                      <span>{opt}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {step === 3 && results && (
          <div className="fade-up">
            <div className="phase-title-block">
              <span className="badge badge-accent">Readiness Assessment</span>
              <h1 className="phase-title">Data Readiness Map</h1>
            </div>

            <div className="readiness-map">
              {results.datasets?.map((ds, i) => (
                <div key={i} className="readiness-row">
                  <span className="readiness-ds-name">{ds.label}</span>
                  <div className="readiness-bar-track">
                    <div className="readiness-bar-fill"
                      style={{ width: `${(ds.avg_score / 4) * 100}%`, background: getColor(ds.avg_score) }}></div>
                  </div>
                  <span className="readiness-badge"
                    style={{ borderColor: getColor(ds.avg_score), color: getColor(ds.avg_score) }}>
                    {ds.avg_score}/4
                  </span>
                </div>
              ))}
            </div>

            {results.summary && (
              <div className="insight-cluster">
                <div className="cluster-header">
                  <span className="cluster-icon">◈</span>
                  <span className="cluster-theme">Summary</span>
                </div>
                <p className="cluster-summary">{results.summary}</p>
                {results.recommendation && (
                  <div className="cluster-potential">
                    <span className="potential-label">Recommendation →</span>
                    <span className="potential-text">{results.recommendation}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="phase-footer">
        <button className="btn btn-ghost" onClick={() => {
          if (step === 2 && currentIdx > 0) setCurrentIdx(currentIdx - 1);
          else if (step > 1) setStep(step - 1);
        }}>← Back</button>
        {step === 1 && (
          <button className="btn btn-primary" disabled={selected.length === 0}
            onClick={() => { setCurrentIdx(0); setStep(2); }}>
            Score {selected.length} Dataset{selected.length !== 1 ? 's' : ''} →
          </button>
        )}
        {step === 2 && (
          <button className="btn btn-primary" disabled={!allDimensionsScored || loading} onClick={nextDataset}>
            {loading ? <div className="spinner"></div> : currentIdx < selected.length - 1 ? 'Next Dataset →' : 'Generate Readiness Map →'}
          </button>
        )}
        {step === 3 && (
          <button className="btn btn-primary" onClick={onComplete}>Proceed to AI Confidence →</button>
        )}
      </footer>
    </div>
  );
}

export default ActivityA_DataAudit;
