import VoiceTextInput from './Voicetextinput'
import AgentChat from './Agentchat'
import { useState, useEffect, useRef } from 'react'
import './phases.css'

// ─────────────────────────────────────────────────────────────────────────────
// ROLE-BASED QUESTION SETS
// Each role gets tailored objectives, growth options, and a challenge prompt
// ─────────────────────────────────────────────────────────────────────────────
const ROLE_CONFIG = {
  'CEO / Founder': {
    objectiveTitle: 'What are your top strategic priorities?',
    objectiveDesc:  'Select the outcomes most critical to your business this year.',
    growthTitle:    'Where are your biggest growth bets?',
    challengePrompt:'What is the single biggest thing holding your business back from its next stage of growth?',
    challengeHint:  'Think about competitive pressure, internal capability gaps, or market timing.',
    objectives: [
      { id: 'revenue',    icon: '◆', label: 'Revenue Growth',         desc: 'Increase sales, expand markets' },
      { id: 'scale',      icon: '⬢', label: 'Scaling the Business',   desc: 'Grow without proportional cost' },
      { id: 'cx',         icon: '◎', label: 'Customer Experience',    desc: 'Retention, NPS, loyalty' },
      { id: 'product',    icon: '⬡', label: 'Product Innovation',     desc: 'New offerings, new markets' },
      { id: 'efficiency', icon: '◈', label: 'Operational Efficiency', desc: 'Reduce cost, improve margins' },
      { id: 'talent',     icon: '◉', label: 'Talent & Culture',       desc: 'Attract, retain, develop people' },
      { id: 'risk',       icon: '▣', label: 'Risk & Governance',      desc: 'Compliance, resilience' },
      { id: 'data',       icon: '◇', label: 'Data-Driven Decisions',  desc: 'Better insight, faster choices' },
    ],
    growthOptions: [
      'Entering new markets or geographies',
      'Launching a new product or service line',
      'Increasing profitability without headcount growth',
      'Building a competitive moat through technology',
      'Improving investor or board confidence in AI strategy',
      'Reducing operational cost base',
      'Scaling revenue per customer (upsell/cross-sell)',
      'Building AI capabilities before competitors do',
    ],
  },

  'CTO / Technology Leader': {
    objectiveTitle: 'What are your core technology objectives?',
    objectiveDesc:  'Select the technology outcomes your team is being measured on.',
    growthTitle:    'Where is your team investing engineering effort?',
    challengePrompt:'What technical or infrastructure limitation is creating the most friction for your team right now?',
    challengeHint:  'Think about legacy systems, data pipelines, deployment speed, or team capability gaps.',
    objectives: [
      { id: 'infra',      icon: '◆', label: 'Infrastructure Modernisation', desc: 'Cloud, scalability, reliability' },
      { id: 'velocity',   icon: '◈', label: 'Engineering Velocity',          desc: 'Faster delivery, less toil' },
      { id: 'data',       icon: '◇', label: 'Data Platform & Quality',       desc: 'Pipelines, governance, access' },
      { id: 'security',   icon: '▣', label: 'Security & Compliance',         desc: 'Zero trust, audit readiness' },
      { id: 'ai_infra',   icon: '⬡', label: 'AI/ML Infrastructure',          desc: 'Models, APIs, MLOps' },
      { id: 'integration',icon: '◉', label: 'Systems Integration',           desc: 'APIs, legacy connectors' },
      { id: 'observ',     icon: '◎', label: 'Observability & Reliability',   desc: 'Uptime, monitoring, SLOs' },
      { id: 'talent',     icon: '⬢', label: 'Engineering Talent',            desc: 'Hiring, retaining, upskilling' },
    ],
    growthOptions: [
      'Reducing time-to-deploy for new features',
      'Migrating legacy systems to modern architecture',
      'Building internal AI/ML tooling and platforms',
      'Improving data quality and pipeline reliability',
      'Reducing technical debt blocking new work',
      'Enabling self-service data access for non-engineers',
      'Reducing on-call burden and operational toil',
      'Upskilling the team on AI/ML fundamentals',
    ],
  },

  'COO / Operations': {
    objectiveTitle: 'What are your operational priorities?',
    objectiveDesc:  'Select the areas where you need to improve performance or reduce cost.',
    growthTitle:    'Where do you see the most operational leverage?',
    challengePrompt:'Describe the operational bottleneck that is most frequently raised in your leadership reviews.',
    challengeHint:  'Think about process failures, manual steps, coordination costs, or quality issues.',
    objectives: [
      { id: 'efficiency', icon: '◈', label: 'Process Efficiency',        desc: 'Reduce steps, eliminate waste' },
      { id: 'quality',    icon: '◆', label: 'Quality & Error Reduction', desc: 'Fewer mistakes, better outcomes' },
      { id: 'cost',       icon: '◎', label: 'Cost Reduction',            desc: 'Do more with less' },
      { id: 'scale',      icon: '⬢', label: 'Capacity & Scaling',        desc: 'Handle more volume' },
      { id: 'visibility', icon: '◇', label: 'Operational Visibility',    desc: 'Real-time dashboards, alerts' },
      { id: 'compliance', icon: '▣', label: 'Compliance & Risk',         desc: 'SOPs, audit trails' },
      { id: 'workforce',  icon: '◉', label: 'Workforce Productivity',    desc: 'Output per head' },
      { id: 'cx',         icon: '⬡', label: 'Service Quality',           desc: 'Consistent delivery standards' },
    ],
    growthOptions: [
      'Automating high-volume manual processes',
      'Reducing error rates and rework costs',
      'Improving cross-department coordination',
      'Building real-time operational dashboards',
      'Reducing dependency on specific individuals',
      'Standardising processes across locations or teams',
      'Shortening decision-making cycles',
      'Improving supplier or vendor performance tracking',
    ],
  },

  'Product Manager': {
    objectiveTitle: 'What are your product and growth objectives?',
    objectiveDesc:  'Select what your product team is focused on delivering.',
    growthTitle:    'Where is your product investment going this year?',
    challengePrompt:'What is slowing your team\'s ability to ship valuable product to customers?',
    challengeHint:  'Think about discovery, prioritisation, engineering capacity, or feedback loops.',
    objectives: [
      { id: 'adoption',   icon: '◆', label: 'User Adoption & Activation',  desc: 'Get users to value faster' },
      { id: 'retention',  icon: '◈', label: 'Retention & Engagement',      desc: 'Keep users coming back' },
      { id: 'velocity',   icon: '⬡', label: 'Shipping Velocity',            desc: 'Deliver features faster' },
      { id: 'discovery',  icon: '◎', label: 'User Research & Insights',    desc: 'Understand what users need' },
      { id: 'cx',         icon: '◉', label: 'Customer Experience Quality', desc: 'NPS, support, satisfaction' },
      { id: 'data',       icon: '◇', label: 'Product Analytics',           desc: 'Usage data, funnels, A/B tests' },
      { id: 'revenue',    icon: '▣', label: 'Monetisation & Revenue',      desc: 'Pricing, upsell, conversion' },
      { id: 'ai',         icon: '⬢', label: 'AI-Powered Features',         desc: 'Build AI into the product' },
    ],
    growthOptions: [
      'Reducing time from idea to user feedback',
      'Improving product-led growth and onboarding',
      'Building AI features that create competitive advantage',
      'Improving data-driven prioritisation of roadmap',
      'Reducing support burden through better UX',
      'Personalising the product experience at scale',
      'Increasing cross-sell and upsell through the product',
      'Shortening release cycles and deployment risk',
    ],
  },

  'Data / AI Engineer': {
    objectiveTitle: 'What are your data and AI engineering priorities?',
    objectiveDesc:  'Select the technical outcomes your work is supporting.',
    growthTitle:    'Where is your data/AI work creating most value?',
    challengePrompt:'What is the biggest technical obstacle preventing your team from delivering AI at production quality?',
    challengeHint:  'Think about data quality, model reliability, tooling gaps, or deployment friction.',
    objectives: [
      { id: 'dataquality',icon: '◆', label: 'Data Quality & Reliability',  desc: 'Clean, trustworthy pipelines' },
      { id: 'mlops',      icon: '◈', label: 'MLOps & Model Deployment',    desc: 'Reliable, monitored models' },
      { id: 'platform',   icon: '⬡', label: 'Data Platform Scalability',   desc: 'Handle growing data volumes' },
      { id: 'selfservice',icon: '◎', label: 'Self-Service Analytics',      desc: 'Empower non-engineers' },
      { id: 'governance', icon: '◉', label: 'Data Governance & Lineage',   desc: 'Trust, compliance, access' },
      { id: 'realtime',   icon: '◇', label: 'Real-Time Data Processing',   desc: 'Streaming, low-latency feeds' },
      { id: 'llm',        icon: '▣', label: 'LLM & GenAI Integration',     desc: 'RAG, fine-tuning, agents' },
      { id: 'features',   icon: '⬢', label: 'Feature Engineering & Stores',desc: 'Reusable ML features' },
    ],
    growthOptions: [
      'Reducing time from raw data to model in production',
      'Improving model monitoring and drift detection',
      'Building a self-service analytics layer for business teams',
      'Improving data lineage and metadata management',
      'Reducing manual data preparation and cleaning work',
      'Building reusable AI components across the organisation',
      'Integrating LLMs into internal workflows and products',
      'Improving training data quality and labelling pipelines',
    ],
  },

  'Business Analyst': {
    objectiveTitle: 'What are your analytics and insight priorities?',
    objectiveDesc:  'Select the areas where better data and analysis would create most impact.',
    growthTitle:    'Where do you see the most opportunity for better decisions?',
    challengePrompt:'Describe the reporting or analysis task that takes the most manual effort and produces the least reliable output.',
    challengeHint:  'Think about data gathering, spreadsheet wrangling, or insight-to-decision delays.',
    objectives: [
      { id: 'reporting',  icon: '◆', label: 'Automated Reporting',         desc: 'Less manual, more reliable' },
      { id: 'visibility', icon: '◈', label: 'Business Visibility',         desc: 'Real-time KPIs and alerts' },
      { id: 'forecast',   icon: '⬡', label: 'Forecasting & Planning',      desc: 'Better predictions' },
      { id: 'selfservice',icon: '◎', label: 'Self-Service Insights',       desc: 'Stakeholders find answers themselves' },
      { id: 'dataquality',icon: '◉', label: 'Data Quality & Trust',        desc: 'Numbers everyone believes' },
      { id: 'speed',      icon: '◇', label: 'Faster Analysis Cycles',      desc: 'Less time waiting for data' },
      { id: 'segmentation',icon:'▣', label: 'Customer & Market Segmentation',desc:'Deeper understanding of patterns' },
      { id: 'compliance', icon: '⬢', label: 'Audit & Compliance Reporting',desc: 'Traceable, defensible numbers' },
    ],
    growthOptions: [
      'Eliminating manual data consolidation from multiple sources',
      'Building dashboards stakeholders actually use',
      'Automating recurring weekly and monthly reports',
      'Making forecasting models more accurate and explainable',
      'Reducing time from data request to insight delivery',
      'Improving data literacy across non-technical teams',
      'Connecting operational data to financial outcomes',
      'Building early-warning indicators for business performance',
    ],
  },

  'Department Head': {
    objectiveTitle: 'What does success look like for your department?',
    objectiveDesc:  'Select the outcomes your department is being measured on.',
    growthTitle:    'Where is your department investing time and budget?',
    challengePrompt:'What keeps your team from performing at its best? Be specific about where time is wasted or quality suffers.',
    challengeHint:  'Think about handoffs, approvals, tools, reporting, or coordination with other teams.',
    objectives: [
      { id: 'productivity',icon:'◆', label: 'Team Productivity',           desc: 'Output per person' },
      { id: 'quality',    icon: '◈', label: 'Work Quality',                desc: 'Fewer errors, higher standards' },
      { id: 'efficiency', icon: '⬡', label: 'Process Efficiency',          desc: 'Eliminate waste and delay' },
      { id: 'visibility', icon: '◎', label: 'Departmental Visibility',     desc: 'Dashboards, progress tracking' },
      { id: 'talent',     icon: '◉', label: 'Team Development',            desc: 'Skills, capacity, retention' },
      { id: 'cx',         icon: '◇', label: 'Internal Customer Satisfaction',desc:'Stakeholder experience' },
      { id: 'cost',       icon: '▣', label: 'Budget Efficiency',           desc: 'Do more within budget' },
      { id: 'compliance', icon: '⬢', label: 'Compliance & Risk',           desc: 'Policies, governance, audits' },
    ],
    growthOptions: [
      'Reducing time spent on manual and administrative tasks',
      'Improving handoff quality between my team and others',
      'Getting better real-time visibility into team workload',
      'Reducing reliance on tribal knowledge and key-person risk',
      'Speeding up approval and sign-off workflows',
      'Improving onboarding for new team members',
      'Better tracking of team KPIs and output',
      'Reducing meeting load while maintaining alignment',
    ],
  },

  'Consultant': {
    objectiveTitle: 'What outcomes are your clients asking for most?',
    objectiveDesc:  'Select the themes that dominate client conversations.',
    growthTitle:    'Where do you see the most AI opportunity for your clients?',
    challengePrompt:'What is the most common reason client AI initiatives fail to reach production, in your experience?',
    challengeHint:  'Think about data readiness, stakeholder buy-in, scope creep, or implementation quality.',
    objectives: [
      { id: 'roi',        icon: '◆', label: 'Demonstrable ROI',            desc: 'Tangible business value fast' },
      { id: 'adoption',   icon: '◈', label: 'Client Adoption',             desc: 'People actually use what\'s built' },
      { id: 'delivery',   icon: '⬡', label: 'Delivery Speed',              desc: 'Faster time to working solution' },
      { id: 'scale',      icon: '◎', label: 'Scalable Architecture',       desc: 'Solutions that grow with the client' },
      { id: 'change',     icon: '◉', label: 'Change Management',           desc: 'Embedding AI in workflows' },
      { id: 'data',       icon: '◇', label: 'Data Readiness',              desc: 'Foundations before AI' },
      { id: 'strategy',   icon: '▣', label: 'AI Strategy & Roadmap',       desc: 'Where to play, how to win' },
      { id: 'governance', icon: '⬢', label: 'AI Governance & Ethics',      desc: 'Responsible deployment' },
    ],
    growthOptions: [
      'Building proof-of-concepts that convert to full projects',
      'Helping clients build internal AI capability vs dependency',
      'Identifying quick wins that fund larger transformation',
      'Navigating data privacy and compliance requirements',
      'Getting exec sponsorship for AI initiatives',
      'Bridging the gap between IT and business teams',
      'Developing repeatable AI frameworks across client sectors',
      'Measuring and communicating AI ROI to stakeholders',
    ],
  },

  'Lead Generation': {
    objectiveTitle: 'What are your lead generation priorities?',
    objectiveDesc:  'Select the outcomes most critical to your pipeline growth.',
    growthTitle:    'Where are you investing in your lead funnel?',
    challengePrompt:'What is the biggest obstacle preventing your lead generation efforts from converting into qualified sales opportunities?',
    challengeHint:  'Think about lead quality, manual data entry, follow-up speed, or channel attribution.',
    objectives: [
      { id: 'volume',     icon: '◆', label: 'Lead Volume',               desc: 'Increase MQLs/SQLs' },
      { id: 'quality',    icon: '◈', label: 'Lead Quality & Scoring',    desc: 'Better qualification, less noise' },
      { id: 'conversion', icon: '⬢', label: 'Conversion Rates',          desc: 'Optimise funnel stages' },
      { id: 'attribution',icon: '▣', label: 'Channel Attribution',       desc: 'Understand what works' },
      { id: 'outreach',   icon: '◉', label: 'Automated Outreach',        desc: 'Scaled personalized contact' },
      { id: 'enrich',     icon: '◇', label: 'Data Enrichment',           desc: 'Better lead data/insights' },
      { id: 'crm',        icon: '⬡', label: 'CRM Sync',                  desc: 'Clean, real-time data flows' },
      { id: 'alignment',  icon: '◎', label: 'Sales/Marketing Alignment', desc: 'Smoother hand-offs' },
    ],
    growthOptions: [
      'Scaling outbound volume without proportional headcount',
      'Implementing AI-driven lead scoring and prioritisation',
      'Automating personalised follow-up at scale',
      'Improving data enrichment for better targeting',
      'Reducing lead response time (speed to lead)',
      'Expanding into new digital acquisition channels',
      'Improving attribution accuracy across the journey',
      'Optimising landing page conversion via AI',
    ],
  },

  'Other': {
    objectiveTitle: 'What are your top strategic priorities?',
    objectiveDesc:  'Select all that apply to your work this year.',
    growthTitle:    'Where are your biggest growth priorities?',
    challengePrompt:'Describe the biggest operational challenge in your day-to-day work.',
    challengeHint:  'Be specific about what is repetitive, slow, error-prone, or frustrating.',
    objectives: [
      { id: 'revenue',    icon: '◆', label: 'Revenue Growth',         desc: 'Increase sales, expand markets' },
      { id: 'efficiency', icon: '◈', label: 'Operational Efficiency', desc: 'Reduce costs, streamline processes' },
      { id: 'cx',         icon: '◎', label: 'Customer Experience',    desc: 'Improve satisfaction & retention' },
      { id: 'product',    icon: '⬡', label: 'Product Innovation',     desc: 'Launch new products or features' },
      { id: 'talent',     icon: '◉', label: 'Talent & Productivity',  desc: 'Empower teams, reduce manual work' },
      { id: 'risk',       icon: '▣', label: 'Risk & Compliance',      desc: 'Reduce errors, improve governance' },
      { id: 'data',       icon: '◇', label: 'Data & Insights',        desc: 'Better decisions from data' },
      { id: 'scale',      icon: '⬢', label: 'Scaling Operations',     desc: 'Grow without proportional cost' },
    ],
    growthOptions: [
      'Entering new markets',
      'Increasing revenue per customer',
      'Launching new products or services',
      'Improving customer retention',
      'Reducing operational costs',
      'Automating manual workflows',
      'Improving data quality & access',
      'Building AI capabilities in-house',
    ],
  },
}

// Fallback for any unrecognised role
const DEFAULT_CONFIG = ROLE_CONFIG['Other']

function getRoleConfig(role) {
  return ROLE_CONFIG[role] || DEFAULT_CONFIG
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function Phase2_Context({ api, apiBase, getWsBase, session, participant, onComplete }) {
  const role    = participant?.role || 'Other'
  const config  = getRoleConfig(role)

  const [step,        setStep]        = useState('objectives')
  const [objectives,  setObjectives]  = useState([])
  const [growthAreas, setGrowthAreas] = useState([])
  const [challenges,  setChallenges]  = useState('')
  const [submitting,       setSubmitting]       = useState(false)
  const [error,            setError]            = useState(null)
  const [insights,         setInsights]         = useState(null)
  const [liveCount,        setLiveCount]        = useState(1)
  // custom "other" entries
  const [customObjective,  setCustomObjective]  = useState('')
  const [customObjectives, setCustomObjectives] = useState([])
  const [showObjInput,     setShowObjInput]     = useState(false)
  const [customGrowth,     setCustomGrowth]     = useState('')
  const [customGrowths,    setCustomGrowths]    = useState([])
  const [showGrowthInput,  setShowGrowthInput]  = useState(false)
  const wsRef = useRef(null)

  // ── Custom objective helpers ─────────────────────────────────────────────
  const addCustomObjective = () => {
    const val = customObjective.trim()
    if (val.length < 3) return
    const id = `custom_obj_${Date.now()}`
    setCustomObjectives(prev => [...prev, { id, label: val, icon: '◇', desc: 'Custom', custom: true }])
    setObjectives(prev => [...prev, id])
    setCustomObjective('')
    setShowObjInput(false)
  }
  const removeCustomObjective = (id) => {
    setCustomObjectives(prev => prev.filter(o => o.id !== id))
    setObjectives(prev => prev.filter(x => x !== id))
  }

  // ── Custom growth helpers ────────────────────────────────────────────────
  const addCustomGrowth = () => {
    const val = customGrowth.trim()
    if (val.length < 3) return
    setCustomGrowths(prev => [...prev, val])
    setGrowthAreas(prev => [...prev, val])
    setCustomGrowth('')
    setShowGrowthInput(false)
  }
  const removeCustomGrowth = (g) => {
    setCustomGrowths(prev => prev.filter(x => x !== g))
    setGrowthAreas(prev => prev.filter(x => x !== g))
  }

  const allObjectives = [...config.objectives, ...customObjectives]

  // WebSocket
  useEffect(() => {
    if (!session?.code) return
    const ws = new WebSocket(
      `${getWsBase()}/ws/${session.code}?participant_id=${participant?.id || 'host'}`
    )
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'context_count') setLiveCount(msg.count)
        if (msg.type === 'objective_map')  setInsights(msg.data)
      } catch {}
    }
    ws.onerror = () => {}
    return () => ws.close()
  }, [session?.code])

  const toggleObjective = (id) =>
    setObjectives(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  const toggleGrowth = (g) =>
    setGrowthAreas(prev =>
      prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g]
    )

  const canSubmit =
    objectives.length > 0 &&
    growthAreas.length > 0 &&
    challenges.trim().length > 20

  const handleSubmit = async () => {
    if (!session?.code) {
      setError('Session context is missing. Rejoin the workshop and try again.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const result = await api('/phase/context', {
        method: 'POST',
        body: JSON.stringify({
          session_code:    session.code,
          participant_id:  participant?.id,
          participant_role: role,
          objectives: objectives.map(id => {
            const found = allObjectives.find(o => o.id === id)
            return found ? found.label : id
          }),
          growth_areas: growthAreas,
          challenges:      challenges.trim(),
        }),
      })
      setInsights(result.objective_map)
      setStep('insights')
    } catch (err) {
      setError(err.message || 'Could not submit. Is the backend running?')
    } finally {
      setSubmitting(false)
    }
  }

  const steps  = ['objectives', 'growth', 'challenges', 'insights']
  const stepIdx = steps.indexOf(step)

  return (
    <div className="phase-shell fade-up">

      <div className="phase-header">
        <div className="phase-logo">◈ AI Copilot</div>
        <div className="phase-indicator">
          <div className="phase-dot pulse" />
          <span className="phase-label">Phase 2 — Business Context</span>
        </div>
      </div>

      {/* Role badge so participant sees this is tailored to them */}
      <div style={{
        padding: '8px 22px',
        background: 'var(--accent-light)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
      }}>
        <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--accent)' }}>
          Questions tailored for
        </span>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', fontFamily: 'var(--font-h)' }}>
          {role}
        </span>
      </div>

      <div className="step-track">
        {['Objectives', 'Growth', 'Challenges', 'Insights'].map((s, i) => (
          <div key={s} className={`step-item ${i <= stepIdx ? 'active' : ''} ${i < stepIdx ? 'done' : ''}`}>
            <div className="step-dot">{i < stepIdx ? '✓' : i + 1}</div>
            <span className="step-name">{s}</span>
          </div>
        ))}
      </div>

      <div className="live-bar">
        <span className="live-dot pulse" />
        <span className="live-text">{liveCount} participant{liveCount !== 1 ? 's' : ''} active in this phase</span>
      </div>

      <div className="phase-body">

        {/* ── STEP 1: Objectives ── */}
        {step === 'objectives' && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-accent">Step 1 of 3</p>
              <h2 className="phase-title">{config.objectiveTitle}</h2>
              <p className="phase-desc">{config.objectiveDesc}</p>
            </div>

            <div className="objective-grid">
              {allObjectives.map(obj => (
                <button
                  key={obj.id}
                  className={`objective-card ${objectives.includes(obj.id) ? 'selected' : ''}`}
                  onClick={() => toggleObjective(obj.id)}
                  type="button"
                >
                  <div className="obj-top-row">
                    <span className="obj-icon">{obj.icon}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      {obj.custom && (
                        <span
                          style={{ fontSize: 11, color: 'var(--text-3)', cursor: 'pointer', padding: '0 2px' }}
                          onClick={e => { e.stopPropagation(); removeCustomObjective(obj.id) }}
                          title="Remove"
                        >✕</span>
                      )}
                      <span className="obj-check">{objectives.includes(obj.id) ? '✓' : ''}</span>
                    </div>
                  </div>
                  <span className="obj-label">{obj.label}</span>
                  <span className="obj-desc">{obj.custom ? 'Custom objective' : obj.desc}</span>
                </button>
              ))}
            </div>

            {/* Add custom objective */}
            {showObjInput ? (
              <div className="custom-add-row">
                <input
                  className="input custom-add-input"
                  placeholder="Describe your objective..."
                  value={customObjective}
                  onChange={e => setCustomObjective(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') addCustomObjective(); if (e.key === 'Escape') setShowObjInput(false) }}
                  autoFocus
                  maxLength={60}
                />
                <button className="btn btn-primary btn-sm" onClick={addCustomObjective} disabled={customObjective.trim().length < 3} type="button">Add</button>
                <button className="btn btn-ghost btn-sm" onClick={() => { setShowObjInput(false); setCustomObjective('') }} type="button">✕</button>
              </div>
            ) : (
              <button className="custom-add-trigger" onClick={() => setShowObjInput(true)} type="button">
                + Add your own objective
              </button>
            )}

            <div className="selected-count">{objectives.length} selected</div>
          </div>
        )}

        {/* ── STEP 2: Growth ── */}
        {step === 'growth' && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-accent">Step 2 of 3</p>
              <h2 className="phase-title">{config.growthTitle}</h2>
              <p className="phase-desc">Choose the initiatives you are most focused on this year.</p>
            </div>

            <div className="growth-list">
              {config.growthOptions.map(g => (
                <button
                  key={g}
                  className={`growth-item ${growthAreas.includes(g) ? 'selected' : ''}`}
                  onClick={() => toggleGrowth(g)}
                  type="button"
                >
                  <span className="growth-check">{growthAreas.includes(g) ? '✓' : '○'}</span>
                  <span className="growth-label">{g}</span>
                </button>
              ))}
              {customGrowths.map(g => (
                <div key={g} className={`growth-item selected custom-growth-item`}>
                  <span className="growth-check">✓</span>
                  <span className="growth-label" style={{ flex: 1 }}>{g}</span>
                  <button
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: 'var(--text-3)', padding: '0 4px', flexShrink: 0 }}
                    onClick={() => removeCustomGrowth(g)}
                    type="button"
                    title="Remove"
                  >✕</button>
                </div>
              ))}
            </div>

            {showGrowthInput ? (
              <div className="custom-add-row">
                <input
                  className="input custom-add-input"
                  placeholder="Describe your growth priority..."
                  value={customGrowth}
                  onChange={e => setCustomGrowth(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') addCustomGrowth(); if (e.key === 'Escape') setShowGrowthInput(false) }}
                  autoFocus
                  maxLength={80}
                />
                <button className="btn btn-primary btn-sm" onClick={addCustomGrowth} disabled={customGrowth.trim().length < 3} type="button">Add</button>
                <button className="btn btn-ghost btn-sm" onClick={() => { setShowGrowthInput(false); setCustomGrowth('') }} type="button">✕</button>
              </div>
            ) : (
              <button className="custom-add-trigger" onClick={() => setShowGrowthInput(true)} type="button">
                + Add your own priority
              </button>
            )}
          </div>
        )}

        {/* ── STEP 3: Challenges ── */}
        {step === 'challenges' && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-accent">Step 3 of 3</p>
              <h2 className="phase-title">Challenges that you face</h2>
              {/* <p className="phase-desc">The agent will ask you a tailored question based on your {role} role. Answer in your own words.</p> */}
            </div>

            <div className="phase-form">
              <AgentChat
                key={role}
                questions={[{
                  id: 'challenge',
                  question: config.challengePrompt,
                  hint: config.challengeHint,
                  placeholder: 'Describe it in your own words — the more specific, the better.',
                  field: 'challenges',
                  required: true,
                }]}
                agentName="Insight Mining Agent"
                agentAvatar="◈"
                apiBase={apiBase}
                onComplete={(answers) => setChallenges(answers.challenges || '')}
              />

              {/* Summary of selections */}
              <div className="summary-card">
                <p className="summary-title">Your selections</p>
                <div className="summary-chips">
                  {objectives.map(id => {
                    const o = allObjectives.find(x => x.id === id)
                    if (!o) return null
                    return (
                      <span key={id} className={`chip${o.custom ? ' chip-custom' : ''}`}>
                        {o.icon} {o.label}
                        {o.custom && <span style={{ fontSize: 9, marginLeft: 4, opacity: 0.7 }}>custom</span>}
                      </span>
                    )
                  })}
                </div>
                <div className="summary-chips" style={{ marginTop: 8 }}>
                  {growthAreas.map(g => {
                    const isCustom = customGrowths.includes(g)
                    return (
                      <span key={g} className={`chip chip-green${isCustom ? ' chip-custom' : ''}`}>
                        {g}
                        {isCustom && <span style={{ fontSize: 9, marginLeft: 4, opacity: 0.7 }}>custom</span>}
                      </span>
                    )
                  })}
                </div>
              </div>

              {error && <div className="error-banner">⚠ {error}</div>}
            </div>
          </div>
        )}

        {/* ── STEP 4: AI Insights ── */}
        {step === 'insights' && insights && (
          <div className="fade-up">
            <div className="phase-title-block">
              <p className="badge badge-accent">Objective Map</p>
              <h2 className="phase-title">Your strategic context<br />has been captured</h2>
              <p className="phase-desc">
                The AI has built your business objective map using your {role} perspective.
                This will shape the AI use cases generated later in the session.
              </p>
            </div>

            <div className="insight-clusters">
              {insights.clusters?.map((cluster, i) => (
                <div key={i} className="insight-cluster">
                  <div className="cluster-header">
                    <span className="cluster-icon">{cluster.icon || '◈'}</span>
                    <span className="cluster-theme">{cluster.theme}</span>
                    <span className="badge badge-accent">{cluster.signals} signal{cluster.signals !== 1 ? 's' : ''}</span>
                  </div>
                  <p className="cluster-summary">{cluster.summary}</p>
                  {cluster.ai_potential && (
                    <div className="cluster-potential">
                      <span className="potential-label">AI Opportunity →</span>
                      <span className="potential-text">{cluster.ai_potential}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {insights.dominant_theme && (
              <div className="dominant-theme-box">
                <span className="dominant-label">Dominant Theme</span>
                <span className="dominant-value">{insights.dominant_theme}</span>
              </div>
            )}
          </div>
        )}

        {/* Loading while AI processes */}
        {step === 'insights' && !insights && (
          <div className="ai-thinking fade-up">
            <div className="thinking-dots">
              <span className="thinking-dot" style={{ animationDelay: '0s' }} />
              <span className="thinking-dot" style={{ animationDelay: '0.2s' }} />
              <span className="thinking-dot" style={{ animationDelay: '0.4s' }} />
            </div>
            <p className="thinking-label">Insight Mining Agent is processing your {role} perspective...</p>
            <p className="thinking-sub">Clustering objectives · Detecting patterns · Building objective map</p>
          </div>
        )}

      </div>

      {/* Footer */}
      <div className="phase-footer">
        {step !== 'objectives' && step !== 'insights' && (
          <button className="btn btn-ghost" onClick={() => setStep(steps[stepIdx - 1])}>
            ← Back
          </button>
        )}
        {step === 'objectives' && (
          <>
            <div />
            <button
              className="btn btn-primary"
              disabled={objectives.length === 0}
              onClick={() => setStep('growth')}
            >
              Continue →
            </button>
          </>
        )}
        {step === 'growth' && (
          <button
            className="btn btn-primary"
            disabled={growthAreas.length === 0}
            onClick={() => setStep('challenges')}
          >
            Continue →
          </button>
        )}
        {step === 'challenges' && (
          <button
            className="btn btn-primary"
            disabled={!canSubmit || submitting}
            onClick={handleSubmit}
          >
            {submitting
              ? <><span className="spinner spinner-blue" /> Analysing...</>
              : 'Generate Objective Map →'}
          </button>
        )}
        {step === 'insights' && insights && (
          <>
            <div />
            <button className="btn btn-primary" onClick={onComplete}>
              Proceed to Problem Discovery →
            </button>
          </>
        )}
      </div>
    </div>
  )
}
