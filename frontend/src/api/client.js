const API_URL = import.meta.env.VITE_API_URL;

const headers = {
  'Content-Type': 'application/json',
  'ngrok-skip-browser-warning': 'true'
};

/**
 * Centralized API client.
 * Each method maps frontend camelCase → backend snake_case fields.
 */
const client = {

  // ── Phase 0: Session Setup ──────────────────────────────────────────
  createSession: async (data) => {
    // Parse duration string like "90 min" → 90
    const durationMins = parseInt(data.duration) || 90;
    const res = await fetch(`${API_URL}/session/create`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        host_name: data.hostName,
        company: data.company,
        industry: data.industry,
        participant_count: data.participants,
        duration_mins: durationMins,
        company_url: data.companyUrl || '',
        company_linkedin_url: data.companyLinkedinUrl || ''
      })
    });
    if (!res.ok) throw new Error('Failed to create session');
    return res.json();
  },

  getSession: async (code) => {
    const res = await fetch(`${API_URL}/session/${code.trim().toUpperCase()}`, { headers });
    if (!res.ok) throw new Error('Session not found');
    return res.json();
  },

  // ── Phase 1: Participant Onboarding ─────────────────────────────────
  joinSession: async (data) => {
    const res = await fetch(`${API_URL}/participant/join`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_code: data.sessionCode.trim().toUpperCase(),
        name: data.fullName,
        role: data.role,
        department: data.department,
        top_challenge: data.topChallenge,
        ai_confidence: data.confidence
      })
    });
    if (!res.ok) throw new Error('Failed to join');
    return res.json();
  },

  // ── Phase 2: Business Context ───────────────────────────────────────
  submitContext: async (data) => {
    const res = await fetch(`${API_URL}/phase/context`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_code: data.sessionCode,
        participant_id: data.participantId,
        objectives: data.objectives,
        growth_areas: data.growthPriorities,
        challenges: data.challenges
      })
    });
    if (!res.ok) throw new Error('Failed to submit context');
    return res.json();
  },

  // ── Phase 3: Problem Discovery ──────────────────────────────────────
  submitProblems: async (data) => {
    const res = await fetch(`${API_URL}/phase/problems`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_code: data.sessionCode,
        participant_id: data.participantId,
        problems: data.problems.map(p => ({
          text: p.text,
          tags: p.tags || [],
          severity: p.severity === 'High' ? 5 : p.severity === 'Medium' ? 3 : 1,
          department: p.department || ''
        }))
      })
    });
    if (!res.ok) throw new Error('Failed to submit problems');
    return res.json();
  },

  // ── Activity A: Data Audit ──────────────────────────────────────────
  submitDataAudit: async (data) => {
    const res = await fetch(`${API_URL}/activity/data-audit`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_code: data.sessionCode,
        participant_id: data.participantId,
        datasets: data.audits.map(a => ({
          dataset: a.dataset,
          label: a.dataset,
          scores: a.scores,
          readiness: Object.values(a.scores).reduce((s, v) => s + v, 0) / Object.keys(a.scores).length
        }))
      })
    });
    if (!res.ok) throw new Error('Failed to submit audit');
    return res.json();
  },

  // ── Activity B: AI Confidence ───────────────────────────────────────
  submitConfidence: async (data) => {
    const res = await fetch(`${API_URL}/activity/confidence`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_code: data.sessionCode,
        participant_id: data.participantId,
        confidence_level: data.confidence,
        concerns: data.concerns,
        expectations: ''
      })
    });
    if (!res.ok) throw new Error('Failed to submit confidence');
    return res.json();
  },

  // ── Activity C: Prompt Engineering ──────────────────────────────────
  submitPromptEng: async (data) => {
    const res = await fetch(`${API_URL}/activity/prompt-engineering`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_code: data.sessionCode,
        participant_id: data.participantId,
        prompt: data.originalPrompt,
        task_context: data.taskContext || ''
      })
    });
    if (!res.ok) throw new Error('Failed to submit prompt');
    return res.json();
  }
};

export default client;
