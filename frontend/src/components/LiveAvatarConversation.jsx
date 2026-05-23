import { useEffect, useMemo, useRef, useState } from 'react'
import { DataPacket_Kind, Room, RoomEvent } from 'livekit-client'
import VoiceTextInput from './Voicetextinput'

const encoder = new TextEncoder()
const decoder = new TextDecoder()

function buildMeetUrl(livekitUrl, token) {
  if (!livekitUrl || !token) return ''
  return `https://meet.livekit.io/custom?liveKitUrl=${encodeURIComponent(livekitUrl)}&token=${encodeURIComponent(token)}`
}

export default function LiveAvatarConversation({
  api,
  sessionCode,
  name,
  role,
  linkedinUrl,
}) {
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [sessionInfo, setSessionInfo] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const roomRef = useRef(null)
  const cancelledRef = useRef(false)

  const ready = useMemo(() => {
    return Boolean(sessionCode?.trim() && role?.trim() && linkedinUrl?.trim())
  }, [sessionCode, role, linkedinUrl])

  const speakOnAvatar = async (text, infoOverride = null) => {
    const room = roomRef.current
    const info = infoOverride || sessionInfo
    if (!room || !info?.session_id || !text?.trim()) return

    const payload = {
      event_type: 'avatar.speak_text',
      session_id: info.session_id,
      text: text.trim(),
    }

    await room.localParticipant.publishData(
      encoder.encode(JSON.stringify(payload)),
      { reliable: true, topic: 'agent-control' },
    )
  }

  useEffect(() => {
    cancelledRef.current = false
    return () => {
      cancelledRef.current = true
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!ready) {
      setSessionInfo(null)
      setMessages([])
      setDraft('')
      setStatus('idle')
      setError('')
      return
    }

    let disposed = false

    const startSession = async () => {
      setStatus('loading')
      setError('')
      try {
        const data = await api('/liveavatar/embed', {
          method: 'POST',
          body: JSON.stringify({
            session_code: sessionCode,
            participant_name: name,
            participant_role: role,
            linkedin_url: linkedinUrl,
          }),
        })

        if (disposed || cancelledRef.current) return

        const info = {
          session_id: data.session_id,
          session_token: data.session_token,
          livekit_url: data.livekit_url,
          livekit_token: data.livekit_token,
          opening_text: data.opening_text || '',
          meet_url: data.embed_url || buildMeetUrl(data.livekit_url, data.livekit_token),
        }
        setSessionInfo(info)
        setMessages(info.opening_text ? [{ type: 'assistant', text: info.opening_text }] : [])
        setStatus('connecting')

        const room = new Room({
          adaptiveStream: true,
          dynacast: true,
        })
        roomRef.current = room

        room.on(RoomEvent.DataReceived, (payload, participant, kind, topic) => {
          try {
            const decoded = decoder.decode(payload)
            const dataPacket = JSON.parse(decoded)
            if (dataPacket?.event_type === 'avatar.transcription' && dataPacket.text) {
              setMessages(prev => [...prev, { type: 'assistant', text: dataPacket.text }])
            }
            if (dataPacket?.event_type === 'avatar.speak_started') {
              setStatus('speaking')
            }
            if (dataPacket?.event_type === 'avatar.speak_ended') {
              setStatus('ready')
            }
          } catch {
            if (topic === 'agent-response' && kind === DataPacket_Kind.RELIABLE) {
              const text = decoded.trim()
              if (text) setMessages(prev => [...prev, { type: 'assistant', text }])
            }
          }
        })

        room.on(RoomEvent.Disconnected, () => {
          if (!cancelledRef.current) setStatus('idle')
        })

        await room.connect(data.livekit_url, data.livekit_token, {
          autoSubscribe: true,
        })

        if (disposed || cancelledRef.current) return

        setStatus('ready')
        if (info.opening_text) {
          await speakOnAvatar(info.opening_text, info)
        }
      } catch (err) {
        if (!disposed && !cancelledRef.current) {
          setStatus('error')
          setError(err.message || 'Could not start the LiveAvatar session.')
        }
      }
    }

    startSession()

    return () => {
      disposed = true
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [api, ready, sessionCode, name, role, linkedinUrl])

  const handleTranscriptStop = async (text) => {
    const cleanText = (text || '').trim()
    if (!cleanText || submitting || !sessionInfo) return

    setSubmitting(true)
    setStatus('thinking')
    setError('')

    const nextMessages = [...messages, { type: 'user', text: cleanText }]
    setMessages(prev => [...prev, { type: 'user', text: cleanText }])

    try {
      const response = await api('/ai/onboarding-chat', {
        method: 'POST',
        body: JSON.stringify({
          messages: nextMessages,
          name,
          role,
          department: role,
        }),
      })

      const nextText = response?.closing_message || response?.next_question || 'Thanks, that helps.'
      setMessages(prev => [...prev, { type: 'assistant', text: nextText }])
      await speakOnAvatar(nextText)
      setDraft('')
      setStatus(response?.done ? 'complete' : 'ready')
    } catch (err) {
      setStatus('error')
      setError(err.message || 'Could not generate the next avatar response.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="avatar-guide fade-up">
      <div className="live-avatar-panel">
        <div className="live-avatar-header">
          <div>
            <div className="live-avatar-kicker">Live Avatar</div>
            <h3 className="live-avatar-title">Live voice session</h3>
          </div>
          <div className={`live-avatar-pill ${status}`}>
            {status === 'loading' ? 'Starting...' : status === 'connecting' ? 'Connecting...' : status === 'speaking' ? 'Speaking' : status === 'thinking' ? 'Thinking' : status === 'complete' ? 'Done' : status === 'error' ? 'Unavailable' : 'Ready'}
          </div>
        </div>

        {error && <div className="live-avatar-error">{error}</div>}

        {(sessionInfo?.meet_url) && (
          <div className="live-avatar-frame-wrap" style={{ marginBottom: 12 }}>
            <iframe
              title="LiveAvatar LiveKit room"
              src={sessionInfo.meet_url}
              className="live-avatar-frame"
              allow="camera; microphone; autoplay; clipboard-write; fullscreen"
            />
          </div>
        )}

        {sessionInfo?.opening_text && (
          <div className="live-avatar-help" style={{ marginBottom: 12 }}>
            <strong>Avatar opening:</strong> {sessionInfo.opening_text}
          </div>
        )}

        <VoiceTextInput
          value={draft}
          onChange={setDraft}
          onRecordingStop={handleTranscriptStop}
          placeholder="Speak to the avatar..."
          rows={4}
          hint="Tap the mic, answer the avatar, and we will route the transcript through the backend orchestrator."
          cleanWithAI={false}
          apiBase=""
          disabled={!sessionInfo || submitting || status === 'loading' || status === 'connecting'}
          minLength={0}
        />

        {messages.length > 0 && (
          <div style={{ marginTop: 14, display: 'grid', gap: 8 }}>
            {messages.slice(-4).map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`live-avatar-help`}
                style={{
                  background: (message.type || message.role) === 'user' ? 'var(--bg-subtle)' : 'var(--accent-light)',
                  borderColor: 'var(--border)',
                }}
              >
                <strong style={{ textTransform: 'capitalize' }}>{message.type || message.role}:</strong> {message.text}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
