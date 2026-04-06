import React, { useMemo, useState } from 'react'
import LiveAvatarEmbed from './LiveAvatarEmbed'

const DEPARTMENT_OPTIONS = {
  'CEO / Founder': ['Executive', 'Strategy', 'Operations', 'Revenue'],
  'CTO / Technology Leader': ['Engineering', 'Platform', 'Data', 'IT'],
  'COO / Operations': ['Operations', 'Delivery', 'Customer Success', 'Process Excellence'],
  'Product Manager': ['Product', 'Growth', 'Customer Experience', 'Delivery'],
  'Data / AI Engineer': ['Data', 'AI / ML', 'Engineering', 'Analytics'],
  'Business Analyst': ['Analytics', 'Operations', 'Finance', 'Strategy'],
  'Department Head': ['Operations', 'Sales', 'Marketing', 'Customer Success'],
  'Consultant': ['Consulting', 'Advisory', 'Transformation', 'Client Services'],
  'Lead Generation': ['Sales', 'Marketing', 'Revenue Operations', 'Growth'],
  Other: ['Operations', 'Sales', 'Marketing', 'Strategy'],
}

const CHALLENGE_OPTIONS = {
  'CEO / Founder': [
    'Scaling decisions are too slow',
    'Teams are working in silos',
    'Growth forecasting is unreliable',
    'Too much time is spent in manual reviews',
  ],
  'CTO / Technology Leader': [
    'Legacy systems slow delivery',
    'Data quality is inconsistent',
    'Too many manual engineering tasks',
    'AI projects do not reach production',
  ],
  'COO / Operations': [
    'Workflow bottlenecks slow execution',
    'Reporting is too manual',
    'Teams rely on spreadsheets',
    'Service delivery is inconsistent',
  ],
  'Product Manager': [
    'Roadmap prioritization is unclear',
    'Research and analysis take too long',
    'Teams cannot ship fast enough',
    'Customer feedback is hard to synthesize',
  ],
  'Data / AI Engineer': [
    'Data pipelines are unreliable',
    'Model deployment is slow',
    'Tooling is fragmented',
    'Business teams cannot self-serve insights',
  ],
  'Business Analyst': [
    'Reporting is repetitive and manual',
    'Data is spread across too many tools',
    'Insights take too long to generate',
    'Stakeholders ask for ad-hoc analysis constantly',
  ],
  'Department Head': [
    'The team spends too much time on admin work',
    'Process handoffs cause delays',
    'Quality is hard to maintain consistently',
    'Visibility across the team is limited',
  ],
  'Consultant': [
    'Client research is too manual',
    'Proposal and report creation takes too long',
    'Knowledge is hard to reuse across projects',
    'Client delivery depends too much on individual effort',
  ],
  'Lead Generation': [
    'Lead qualification is manual',
    'Follow-up is inconsistent',
    'Lead data is incomplete',
    'Conversion tracking is unclear',
  ],
  Other: [
    'Too much manual work',
    'Information is scattered across tools',
    'Approvals and handoffs are slow',
    'Reporting takes too long',
  ],
}

export default function AvatarGuidedOnboarding({
  api,
  sessionCode,
  name,
  role,
  department,
  topChallenge,
  onDepartmentChange,
  onChallengeChange,
  onConversationChange,
}) {
  const [manualNotes, setManualNotes] = useState('')

  const roleKey = role && CHALLENGE_OPTIONS[role] ? role : 'Other'
  const departmentOptions = DEPARTMENT_OPTIONS[roleKey] || DEPARTMENT_OPTIONS.Other
  const challengeOptions = CHALLENGE_OPTIONS[roleKey] || CHALLENGE_OPTIONS.Other

  const promptName = name?.trim() ? name.trim().split(' ')[0] : 'there'
  const isComplete = Boolean(department?.trim() && topChallenge?.trim())

  const statusText = useMemo(() => {
    if (!department?.trim()) return 'Choose the department you work closest to.'
    if (!topChallenge?.trim()) return 'Pick the challenge that feels closest to your day-to-day reality.'
    return 'Perfect. You can add a little more detail manually, or continue into the workshop.'
  }, [department, topChallenge])

  const syncConversation = (nextDepartment, nextChallenge, nextNotes) => {
    const lines = [
      { type: 'agent', text: `Hi ${promptName}, I will guide this onboarding.` },
      { type: 'agent', text: 'Select the department you work closest to.' },
      nextDepartment ? { type: 'user', text: `Department: ${nextDepartment}` } : null,
      { type: 'agent', text: 'Select the challenge that best matches your current situation.' },
      nextChallenge ? { type: 'user', text: `Challenge: ${nextChallenge}` } : null,
      nextNotes?.trim() ? { type: 'user', text: `Extra detail: ${nextNotes.trim()}` } : null,
    ].filter(Boolean)
    onConversationChange?.(lines)
  }

  const handleDepartment = (value) => {
    onDepartmentChange(value)
    syncConversation(value, topChallenge, manualNotes)
  }

  const handleChallenge = (value) => {
    onChallengeChange(value)
    syncConversation(department, value, manualNotes)
  }

  const handleManualNotes = (value) => {
    setManualNotes(value)
    const combinedChallenge = value.trim()
      ? `${topChallenge || 'Custom challenge'}${topChallenge ? ' - ' : ''}${value.trim()}`
      : topChallenge
    onChallengeChange(combinedChallenge)
    syncConversation(department, combinedChallenge, value)
  }

  return (
    <div className="avatar-guide fade-up">
      <LiveAvatarEmbed
        api={api}
        sessionCode={sessionCode}
        participantName={name}
        participantRole={role}
      />

      <div className="avatar-guide-shell">
        <div className="avatar-guide-avatar-wrap">
          <div className="avatar-guide-orb">
            <div className="avatar-guide-orb-core">AI</div>
          </div>
          <div>
            <div className="avatar-guide-kicker">HeyGen Guide</div>
            <h3 className="avatar-guide-title">Avatar-led onboarding</h3>
            <p className="avatar-guide-copy">
              Hey {promptName}, I&apos;ll guide the rest of this setup through quick selections so we can keep the flow structured.
            </p>
          </div>
        </div>

        <div className="avatar-guide-status">
          <span className={`avatar-guide-status-dot${isComplete ? ' ready' : ''}`} />
          <span>{statusText}</span>
        </div>
      </div>

      <div className="avatar-guide-block">
        <div className="avatar-guide-label">1. Choose your department</div>
        <div className="avatar-guide-options">
          {departmentOptions.map((option) => (
            <button
              key={option}
              type="button"
              className={`avatar-guide-chip${department === option ? ' active' : ''}`}
              onClick={() => handleDepartment(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      <div className="avatar-guide-block">
        <div className="avatar-guide-label">2. Choose the challenge that fits best</div>
        <div className="avatar-guide-cards">
          {challengeOptions.map((option) => {
            const selected = topChallenge === option || topChallenge?.startsWith(`${option} - `)
            return (
              <button
                key={option}
                type="button"
                className={`avatar-guide-card${selected ? ' active' : ''}`}
                onClick={() => handleChallenge(option)}
              >
                {option}
              </button>
            )
          })}
        </div>
      </div>

      <div className="avatar-guide-block">
        <div className="avatar-guide-label">3. Add manual detail if you want</div>
        <textarea
          className="input avatar-guide-notes"
          rows={3}
          placeholder="Optional: add a little more context in your own words..."
          value={manualNotes}
          onChange={(e) => handleManualNotes(e.target.value)}
        />
      </div>
    </div>
  )
}
