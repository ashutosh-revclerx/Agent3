import { useEffect, useMemo, useState } from 'react'

export default function LiveAvatarEmbed({ api, sessionCode, participantName, participantRole }) {
  const [embedUrl, setEmbedUrl] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const ready = useMemo(() => {
    return Boolean(sessionCode?.trim() && participantRole?.trim())
  }, [sessionCode, participantRole])

  useEffect(() => {
    if (!ready) {
      setEmbedUrl('')
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
          }),
        })
        if (!cancelled) {
          setEmbedUrl(data.embed_url)
          setStatus('ready')
        }
      } catch (err) {
        if (!cancelled) {
          setStatus('error')
          setError(err.message || 'Could not start the live avatar session.')
        }
      }
    }

    loadEmbed()
    return () => {
      cancelled = true
    }
  }, [api, ready, sessionCode, participantName, participantRole])

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
          <span>Creating a live avatar session...</span>
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

      {status !== 'ready' && status !== 'error' && (
        <p className="live-avatar-help">
          The live avatar will appear once the participant role is ready.
        </p>
      )}
    </div>
  )
}
