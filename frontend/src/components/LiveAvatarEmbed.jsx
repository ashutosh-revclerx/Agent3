import { useEffect, useMemo, useState } from 'react'

export default function LiveAvatarEmbed({ api, sessionCode, participantName, participantRole, participantLinkedinUrl }) {
  const [embedUrl, setEmbedUrl] = useState('')
  const [openingText, setOpeningText] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const ready = useMemo(() => {
    return Boolean(sessionCode?.trim() && participantRole?.trim() && participantLinkedinUrl?.trim())
  }, [sessionCode, participantRole, participantLinkedinUrl])

  useEffect(() => {
    if (!ready) {
      setEmbedUrl('')
      setOpeningText('')
      setStatus('idle')
      setError('')
      return
    }

    let cancelled = false
    const loadEmbed = async () => {
      setStatus('loading')
      setError('')
      try {
        const data = await api('/liveavatar/embed', {
          method: 'POST',
          body: JSON.stringify({
            session_code: sessionCode,
            participant_name: participantName,
            participant_role: participantRole,
            linkedin_url: participantLinkedinUrl,
          }),
        })
        if (!cancelled) {
          setEmbedUrl(data.embed_url)
          setOpeningText(data.opening_text || '')
          setStatus('ready')
        }
      } catch (err) {
        if (!cancelled) {
          setStatus('error')
          setOpeningText('')
          setError(err.message || 'Could not start the live avatar session.')
        }
      }
    }

    loadEmbed()
    return () => {
      cancelled = true
    }
  }, [api, ready, sessionCode, participantName, participantRole, participantLinkedinUrl])

  return (
    <div className="live-avatar-panel fade-up">
      <div className="live-avatar-header">
        <div>
          <div className="live-avatar-kicker">Live Avatar</div>
          <h3 className="live-avatar-title">HeyGen session</h3>
        </div>
        <div className={`live-avatar-pill ${status}`}>
          {status === 'loading' ? 'Starting...' : status === 'ready' ? 'Live' : status === 'error' ? 'Unavailable' : 'Waiting'}
        </div>
      </div>

      {status === 'loading' && (
        <div className="live-avatar-state">
          <div className="spinner" />
          <span>Creating your greeting session...</span>
        </div>
      )}

      {openingText && (
        <div className="live-avatar-help" style={{ marginBottom: 12 }}>
          <strong>Avatar opening line:</strong> {openingText}
        </div>
      )}

      {status === 'error' && (
        <div className="live-avatar-error">
          {error}
        </div>
      )}

      {status === 'ready' && embedUrl && (
        <div className="live-avatar-frame-wrap">
          <iframe
            title="HeyGen Live Avatar"
            src={embedUrl}
            className="live-avatar-frame"
            allow="camera; microphone; autoplay; clipboard-write; fullscreen"
          />
        </div>
      )}

      {status !== 'ready' && status !== 'error' && !participantLinkedinUrl?.trim() && (
        <p className="live-avatar-help">
          Add your LinkedIn URL to unlock the avatar step.
        </p>
      )}

      {status !== 'ready' && status !== 'error' && participantLinkedinUrl?.trim() && (
        <p className="live-avatar-help">
          The avatar is preparing your greeting now.
        </p>
      )}
    </div>
  )
}
