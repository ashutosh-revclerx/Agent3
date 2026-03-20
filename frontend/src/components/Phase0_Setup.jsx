import React, { useState } from 'react';

const INDUSTRIES = [
  'Technology & Software', 'Financial Services & Banking',
  'Healthcare & Life Sciences', 'Retail & E-commerce',
  'Manufacturing & Supply Chain', 'Professional Services & Consulting',
  'Real Estate & Property', 'Education & Training',
  'Logistics & Transportation', 'Media & Entertainment', 'Other'
];

function Phase0_Setup({ api, onComplete, onBack }) {
  const [form, setForm] = useState({
    host_name: '', company: '', industry: '',
    participant_count: 10, duration_mins: 90
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const valid = form.host_name && form.company && form.industry && form.participant_count > 0;

  const handleSubmit = async () => {
    if (!valid) return;
    setLoading(true); setError('');
    try {
      const data = await api('/session/create', {
        method: 'POST',
        body: JSON.stringify(form)
      });
      onComplete(data);
    } catch (err) {
      setError('Failed to create session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="phase-shell fade-up">
      <header className="phase-header">
        <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-ind-dot"></div>
          <span className="phase-ind-label">Phase 0 — Setup</span>
        </div>
      </header>

      <main className="phase-body">
        <div className="phase-title-block">
          <span className="badge badge-accent">Host Configuration</span>
          <h1 className="phase-title">Set up your workshop session</h1>
          <p className="phase-desc">Configure the session context so the AI can pre-load industry benchmarks before participants join.</p>
        </div>

        <div className="phase-form">
          <div className="input-group">
            <label className="input-label">Your Name</label>
            <input className="input" placeholder="e.g. Alex Rivera"
              value={form.host_name}
              onChange={e => setForm({...form, host_name: e.target.value})} />
          </div>

          <div className="input-group">
            <label className="input-label">Company / Organisation</label>
            <input className="input" placeholder="e.g. Future Corp"
              value={form.company}
              onChange={e => setForm({...form, company: e.target.value})} />
          </div>

          <div className="input-group">
            <label className="input-label">Industry</label>
            <select className="input" value={form.industry}
              onChange={e => setForm({...form, industry: e.target.value})}>
              <option value="" disabled>Select industry...</option>
              {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>

          <div className="grid-2">
            <div className="input-group">
              <label className="input-label">Expected Participants</label>
              <input type="number" className="input" min="1" max="100"
                value={form.participant_count}
                onChange={e => setForm({...form, participant_count: parseInt(e.target.value) || 1})} />
            </div>
            <div className="input-group">
              <label className="input-label">Session Duration</label>
              <select className="input" value={form.duration_mins}
                onChange={e => setForm({...form, duration_mins: parseInt(e.target.value)})}>
                <option value={60}>60 min — Quick Discovery</option>
                <option value={90}>90 min — Standard Workshop</option>
                <option value={120}>120 min — Deep Dive</option>
              </select>
            </div>
          </div>

          {error && <div className="error-banner">{error}</div>}
        </div>
      </main>

      <footer className="phase-footer">
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <button className="btn btn-primary" disabled={!valid || loading} onClick={handleSubmit}>
          {loading ? <div className="spinner"></div> : 'Launch Session →'}
        </button>
      </footer>
    </div>
  );
}

export default Phase0_Setup;
