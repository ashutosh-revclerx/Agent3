import React, { useState } from 'react';
import './App.css';
import './styles/phases.css';
import Phase0_Setup from './components/Phase0_Setup';
import Phase1_Onboarding from './components/Phase1_Onboarding';
import Phase2_Context from './components/Phase2_Context';
import Phase3_Problems from './components/Phase3_Problems';
import Phase4_Opportunities from './components/Phase4_opportunities';
import Phase5_Poll1 from './components/Phase5_Poll1';
import Phase6_GlobalAdoptionInsight from './components/Phase6_GlobalAdoptionInsight';
import Phase7_Poll2 from './components/Phase7_poll2';
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
  if (!res.ok) {
    let message = `API error ${res.status}`;
    try {
      const data = await res.json();
      message = data?.detail || data?.message || message;
    } catch {}
    throw new Error(message);
  }
  return res.json();
};

const getWsBase = () => API_BASE.replace(/^http/, 'ws');

const PHASES = {
  HOME: 'HOME', SETUP: 'SETUP', ONBOARDING: 'ONBOARDING',
  CONTEXT: 'CONTEXT', PROBLEMS: 'PROBLEMS', OPPORTUNITIES: 'OPPORTUNITIES',
  POLL_1: 'POLL_1', BENCHMARK: 'BENCHMARK', POLL_2: 'POLL_2',
  ACTIVITY_A: 'ACTIVITY_A', ACTIVITY_B: 'ACTIVITY_B', ACTIVITY_C: 'ACTIVITY_C',
};

function App() {
  const [phase, setPhase] = useState(PHASES.HOME);
  const [session, setSession] = useState(null);
  const [participant, setParticipant] = useState(null);
  const [role, setRole] = useState(null); // 'host' | 'participant'

  const shared = { api, apiBase: API_BASE, getWsBase, session, participant, mode: role };

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
          onComplete={() => setPhase(PHASES.OPPORTUNITIES)}
        />;

      case PHASES.OPPORTUNITIES:
        return <Phase4_Opportunities {...shared}
          onComplete={(data) => {
            if (data?.use_cases?.length) {
              setSession((prev) => ({
                ...(prev || {}),
                workshop_data: {
                  ...(prev?.workshop_data || {}),
                  use_cases: data.use_cases,
                  verification_summary: data.verification_summary,
                  generation_metadata: data.generation_metadata,
                  search_evidence: data.search_evidence,
                },
              }));
            }
            setPhase(PHASES.POLL_1);
          }}
        />;

      case PHASES.POLL_1:
        return <Phase5_Poll1 {...shared}
          onComplete={(data) => {
            if (data?.results) {
              setSession((prev) => ({
                ...(prev || {}),
                workshop_data: {
                  ...(prev?.workshop_data || {}),
                  poll1_results: data.results,
                },
              }));
            }
            setPhase(PHASES.BENCHMARK);
          }}
        />;

      case PHASES.BENCHMARK:
        return <Phase6_GlobalAdoptionInsight {...shared}
          onComplete={(data) => {
            if (data) {
              setSession((prev) => ({
                ...(prev || {}),
                workshop_data: {
                  ...(prev?.workshop_data || {}),
                  benchmark: data,
                },
              }));
            }
            setPhase(PHASES.POLL_2);
          }}
        />;

      case PHASES.POLL_2:
        return <Phase7_Poll2 {...shared}
          onComplete={(data) => {
            if (data?.results || data?.shift) {
              setSession((prev) => ({
                ...(prev || {}),
                workshop_data: {
                  ...(prev?.workshop_data || {}),
                  ...(data?.results ? { poll2_results: data.results } : {}),
                  ...(data?.shift ? { vote_shift: data.shift } : {}),
                },
              }));
            }
            setPhase(PHASES.HOME);
          }}
        />;

      default:
        return null;
    }
  };

  return renderPhase();
}

export default App;
