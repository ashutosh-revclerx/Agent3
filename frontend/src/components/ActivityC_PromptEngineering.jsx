import React, { useState } from 'react';

const STEPS = [
  { num: 1, name: 'Write Prompt' },
  { num: 2, name: 'Get Scored' },
  { num: 3, name: 'Live Simulation' },
];

function ActivityC_PromptEngineering({ api, session, participant, mode, onComplete }) {
  const [step, setStep] = useState(1);
  const [taskContext, setTaskContext] = useState('');
  const [prompt, setPrompt] = useState('');
  const [scoreData, setScoreData] = useState(null);
  const [simData, setSimData] = useState(null);
  const [loading, setLoading] = useState(false);

  const getScoreColor = (s) => s >= 4 ? 'var(--green)' : s >= 3 ? 'var(--amber)' : '#ff7a50';

  const handleScore = async () => {
    setLoading(true);
    try {
      const data = await api('/activity/prompt-engineering', {
        method: 'POST',
        body: JSON.stringify({
          session_code: session.code,
          participant_id: participant?.id,
          prompt, task_context: taskContext
        })
      });
      setScoreData(data);
      setStep(2);
    } catch { alert('Error scoring prompt.'); }
    finally { setLoading(false); }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const data = await api('/activity/prompt-simulation', {
        method: 'POST',
        body: JSON.stringify({
          session_code: session.code,
          participant_id: participant?.id,
          prompt: scoreData?.improved_prompt || prompt,
          task_context: taskContext
        })
      });
      setSimData(data);
      setStep(3);
    } catch { alert('Error running simulation.'); }
    finally { setLoading(false); }
  };

  const totalScore = scoreData?.scores ? Object.values(scoreData.scores).reduce((a, b) => a + b, 0) : 0;
  const totalColor = totalScore >= 16 ? 'var(--green)' : totalScore >= 12 ? 'var(--amber)' : '#ff7a50';

  return (
    <div className="phase-shell fade-up">
      <header className="phase-header">
        <div className="phase-logo"><span className="logo-icon">◈</span> AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-ind-dot"></div>
          <span className="phase-ind-label">Activity C — Prompt Engineering</span>
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
              <h1 className="phase-title">Write Your Prompt</h1>
              <p className="phase-desc">Imagine a task you want AI to accomplish. Describe it as a detailed prompt.</p>
            </div>

            <div className="prompt-example-box">
              <div className="prompt-example-label">Example</div>
              <div className="prompt-example-text">
                Every Monday I receive a CSV of last week's sales. Analyse it,
                highlight the top 5 products, flag any down &gt;20% from prior week,
                write a 3-bullet Slack summary.
              </div>
            </div>

            <div className="input-group">
              <label className="input-label">Task context (optional)</label>
              <input className="input" placeholder="e.g. Weekly sales reporting for UK region"
                value={taskContext} onChange={e => setTaskContext(e.target.value)} />
            </div>

            <div className="input-group">
              <label className="input-label">Your Prompt</label>
              <textarea className="input" rows="6"
                style={{ fontFamily: 'var(--font-b)', resize: 'vertical' }}
                placeholder="Write a detailed prompt..."
                value={prompt} onChange={e => setPrompt(e.target.value)} />
              <span className="input-hint" style={{ textAlign: 'right' }}>{prompt.length} characters</span>
            </div>
          </div>
        )}

        {step === 2 && scoreData && (
          <div className="fade-up">
            <div className="phase-title-block">
              <span className="badge badge-accent">Prompt Analysis</span>
              <h1 className="phase-title">Your Prompt Score</h1>
            </div>

            <div className="score-grid">
              {scoreData.breakdown?.map((item, i) => (
                <div key={i} className="score-card">
                  <div className="score-label">{item.label}</div>
                  <div className="score-value" style={{ color: getScoreColor(item.score) }}>
                    {item.score}/5
                  </div>
                  <div className="score-bar">
                    <div className="score-bar-fill"
                      style={{ width: `${(item.score / 5) * 100}%`, background: getScoreColor(item.score) }}></div>
                  </div>
                  <div className="score-feedback">{item.feedback}</div>
                </div>
              ))}
            </div>

            <div className="total-score-box">
              <div className="total-score-label">Overall Prompt Score</div>
              <div className="total-score-value" style={{ color: totalColor }}>{totalScore}/20</div>
            </div>

            <div className="prompt-compare">
              <div className="compare-box">
                <div className="compare-box-label">Your Original Prompt</div>
                {prompt}
              </div>
              <div className="compare-arrow">→</div>
              <div className="compare-box improved">
                <div className="compare-box-label">Improved by AI</div>
                {scoreData.improved_prompt || 'No improvement available'}
              </div>
            </div>

            {scoreData.key_improvement && (
              <div className="insight-cluster">
                <div className="cluster-header">
                  <span className="cluster-icon">◈</span>
                  <span className="cluster-theme">Key Improvement</span>
                </div>
                <p className="cluster-summary">{scoreData.key_improvement}</p>
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="fade-up">
            <div className="phase-title-block">
              <span className="badge badge-green">Live Simulation</span>
              <h1 className="phase-title">AI Response</h1>
            </div>

            <div className="sim-output-box">
              <div className="sim-output-header">
                <span>◈</span> Claude's Response
              </div>
              <div className="sim-output-content">
                {simData?.output || 'Loading simulation...'}
              </div>
            </div>

            {simData?.insight && (
              <div className="sim-insight-box">
                <div className="sim-insight-label">What this shows →</div>
                <div className="sim-insight-text">{simData.insight}</div>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="phase-footer">
        <button className="btn btn-ghost" onClick={() => step > 1 ? setStep(step - 1) : null}>← Back</button>
        {step === 1 && (
          <button className="btn btn-primary" disabled={prompt.length <= 20 || loading} onClick={handleScore}>
            {loading ? <div className="spinner"></div> : 'Score My Prompt →'}
          </button>
        )}
        {step === 2 && (
          <button className="btn btn-primary" disabled={loading} onClick={handleSimulate}>
            {loading ? <div className="spinner"></div> : 'Run Live Simulation →'}
          </button>
        )}
        {step === 3 && (
          <button className="btn btn-primary" onClick={onComplete}>
            Proceed to Opportunity Generation →
          </button>
        )}
      </footer>
    </div>
  );
}

export default ActivityC_PromptEngineering;
