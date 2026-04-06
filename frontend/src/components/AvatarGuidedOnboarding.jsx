import React, { useMemo } from 'react'
import LiveAvatarConversation from './LiveAvatarConversation'

export default function AvatarGuidedOnboarding({
  api,
  sessionCode,
  name,
  role,
  linkedinUrl,
}) {
  const promptName = name?.trim() ? name.trim().split(' ')[0] : 'there'

  const statusText = useMemo(() => {
    return 'Your avatar will open here once the session is ready.'
  }, [])

  return (
    <div className="avatar-guide fade-up">
      <LiveAvatarConversation
        api={api}
        sessionCode={sessionCode}
        name={name}
        role={role}
        linkedinUrl={linkedinUrl}
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
              Hey {promptName}, I&apos;ll guide the rest of this setup through the live avatar once it loads.
            </p>
          </div>
        </div>

        <div className="avatar-guide-status">
          <span className="avatar-guide-status-dot ready" />
          <span>{statusText}</span>
        </div>
      </div>
    </div>
  )
}
