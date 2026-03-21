import React, { useState } from 'react';
import './App.css';
import './styles/phases.css';
import Phase0_Setup from './components/Phase0_Setup';
import Phase1_Onboarding from './components/Phase1_Onboarding';
import Phase2_Context from './components/Phase2_Context';
import Phase3_Problems from './components/Phase3_Problems';
import ActivityA_DataAudit from './components/ActivityA_DataAudit';
import ActivityB_Confidence from './components/ActivityB_Confidence';
import ActivityC_PromptEngineering from './components/ActivityC_PromptEngineering';

const API_BASE = import.meta.env.VITE_API_URL;

const api = async (path, options = {}) => {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true',
      ...options.headers,
    },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
};

const getWsBase = () => API_BASE.replace(/^http/, 'ws');

const PHASES = {
  HOME: 'HOME', SETUP: 'SETUP', ONBOARDING: 'ONBOARDING',
  CONTEXT: 'CONTEXT', PROBLEMS: 'PROBLEMS',
  ACTIVITY_A: 'ACTIVITY_A', ACTIVITY_B: 'ACTIVITY_B', ACTIVITY_C: 'ACTIVITY_C',
};

function App() {
  const [phase, setPhase] = useState(PHASES.HOME);
  const [session, setSession] = useState(null);
  const [participant, setParticipant] = useState(null);
  const [role, setRole] = useState(null); // 'host' | 'participant'

  const shared = { api, getWsBase, session, participant, mode: role };

  const renderPhase = () => {
    switch (phase) {
      case PHASES.HOME:
        return (
          <div className="app-home fade-up">
            <div className="home-logo">
              <span className="logo-icon">◈</span> AI Copilot
            </div>

            <div className="home-hero">
              <span className="badge badge-accent">Workshop Platform</span>
              <h1 className="home-title">AI Consulting<br/>Copilot</h1>
              <p className="home-sub">
                Accelerate your AI strategy from discovery to implementation
                in a single collaborative session.
              </p>
            </div>

            <div className="home-cards">
              <div className="role-card" onClick={() => { setRole('host'); setPhase(PHASES.SETUP); }}>
                <span className="role-icon">⬡</span>
                <span className="role-label">Host a Workshop</span>
                <span className="role-desc">Configure and launch a new session</span>
                <span className="role-arrow">→</span>
              </div>

              <div className="role-card" onClick={() => { setRole('participant'); setPhase(PHASES.ONBOARDING); }}>
                <span className="role-icon">◎</span>
                <span className="role-label">Join a Workshop</span>
                <span className="role-desc">Enter your session code and onboard</span>
                <span className="role-arrow">→</span>
              </div>
            </div>

            <div className="home-version">v1.0 — AI Discovery Platform</div>
          </div>
        );

      case PHASES.SETUP:
        return <Phase0_Setup {...shared}
          onComplete={(data) => { setSession(data); setPhase(PHASES.ONBOARDING); }}
          onBack={() => setPhase(PHASES.HOME)}
        />;

      case PHASES.ONBOARDING:
        return <Phase1_Onboarding {...shared} role={role}
          onComplete={(data) => {
            setParticipant(data.participant || data);
            if (data.session) setSession(data.session);
            setPhase(PHASES.CONTEXT);
          }}
          onBack={() => setPhase(PHASES.HOME)}
        />;

      case PHASES.CONTEXT:
        return <Phase2_Context {...shared}
          onComplete={() => setPhase(PHASES.PROBLEMS)}
        />;

      case PHASES.PROBLEMS:
        return <Phase3_Problems {...shared}
          onComplete={() => setPhase(PHASES.ACTIVITY_A)}
        />;

      case PHASES.ACTIVITY_A:
        return <ActivityA_DataAudit {...shared}
          onComplete={() => setPhase(PHASES.ACTIVITY_B)}
        />;

      case PHASES.ACTIVITY_B:
        return <ActivityB_Confidence {...shared}
          onComplete={() => setPhase(PHASES.ACTIVITY_C)}
        />;

      case PHASES.ACTIVITY_C:
        return <ActivityC_PromptEngineering {...shared}
          onComplete={() => setPhase(PHASES.HOME)}
        />;

      default:
        return null;
    }
  };

  return renderPhase();
}

export default App;
