import { useEffect, useRef, useState } from 'react'
import VoiceTextInput from './Voicetextinput'

let msgId = 0
const nextId = () => ++msgId

export default function AgentChat({
  questions = [],
  onComplete,
  agentName = 'AI Facilitator',
  agentAvatar = '◇',
  apiBase = '',
  accentColor,
  dynamicEndpoint = null,
  context = {},
}) {
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState({})
  const [inputVal, setInputVal] = useState('')
  const [messages, setMessages] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false)
  const bottomRef = useRef(null)
  const audioRef = useRef(null)
  const audioUrlRef = useRef(null)
  const lastSpokenTextRef = useRef(null)

  const currentQ = questions[currentIdx]

  // ── TTS: Speak text via ElevenLabs (managed here, not in VoiceTextInput) ──
  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }
    setIsAgentSpeaking(false)
  }

  const speakText = async (text) => {
    if (!text || !apiBase) return
    // Skip if we already spoke this exact text
    if (lastSpokenTextRef.current === text) return
    lastSpokenTextRef.current = text

    // Stop any currently playing audio first
    stopAudio()
    setIsAgentSpeaking(true)

    try {
      const res = await fetch(`${apiBase}/ai/speak`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
        },
        body: JSON.stringify({ text: text.slice(0, 500) }),
      })
      if (!res.ok) throw new Error('speak failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      audioUrlRef.current = url
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => {
        setIsAgentSpeaking(false)
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current)
          audioUrlRef.current = null
        }
      }
      audio.onerror = () => setIsAgentSpeaking(false)
      audio.play()
    } catch {
      setIsAgentSpeaking(false)
    }
  }

  // Cleanup on unmount
  useEffect(() => () => stopAudio(), [])

  // ── Seed the first question exactly ONCE ──────────────────────────────────
  const hasSeededRef = useRef(false)

  useEffect(() => {
    if (questions.length === 0 || hasSeededRef.current) return
    hasSeededRef.current = true
    
    const firstQuestion = questions[0].question

    const timeoutId = setTimeout(() => {
      setMessages([{
        type: 'agent',
        text: firstQuestion,
        hint: questions[0].hint,
        id: nextId(),
      }])
      // Speak the first question
      speakText(firstQuestion)
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [questions])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const pushUser = (text) => {
    setMessages(prev => [...prev, {
      type: 'user',
      text,
      id: nextId(),
    }])
  }

  const pushAgentMessage = (text, hint, shouldSpeak = false) => {
    setMessages(prev => [...prev, {
      type: 'agent',
      text,
      hint,
      id: nextId(),
    }])
    if (shouldSpeak && text) {
      speakText(text)
    }
  }

  const STOP_WORDS = ['done', 'skip', 'next', 'move on', 'that\'s all', 'nothing else']

  const handleSubmit = async () => {
    const val = inputVal.trim()
    if (!val && !dynamicEndpoint && currentQ?.required !== false) return
    if (!val && dynamicEndpoint) return

    const newAnswers = { ...answers, [currentQ?.field]: val }
    setAnswers(newAnswers)
    pushUser(val)
    setInputVal('')
    setSubmitting(true)

    // Stop any currently playing audio when user submits
    stopAudio()

    // Check for stopword — immediately end the chat
    const lower = val.toLowerCase().trim()
    if (STOP_WORDS.some(sw => lower === sw || lower.startsWith(sw + ' ') || lower.endsWith(' ' + sw))) {
      setTimeout(() => {
        pushAgentMessage('Got it — let\'s move on to the next step!', null, true)
        setTimeout(() => {
          setDone(true)
          setSubmitting(false)
          // Collect whatever we have so far from the conversation
          const agentMsgs = messages.filter(m => m.type === 'agent').map(m => m.text).join(' ')
          const userMsgs = messages.filter(m => m.type === 'user').map(m => m.text).join(' ')
          onComplete({ daily_work: userMsgs, top_challenge: '' })
        }, 800)
      }, 400)
      return
    }

    if (dynamicEndpoint) {
      try {
        const payload = {
          messages: [...messages, { type: 'user', text: val }].map(m => ({ type: m.type, text: m.text })),
          ...context
        }
        const res = await fetch(`${apiBase}${dynamicEndpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        const data = await res.json()
        if (data.done) {
          const closingMsg = data.closing_message || 'Perfect — I have everything I need.'
          setTimeout(() => {
            pushAgentMessage(closingMsg, null, true)
            setTimeout(() => {
              setDone(true)
              onComplete(data.extracted_data || newAnswers)
            }, 1000)
          }, 600)
        } else {
          setTimeout(() => {
            pushAgentMessage(data.next_question, null, true)
          }, 600)
        }
      } catch (err) {
        console.error(err)
        setTimeout(() => pushAgentMessage('Sorry, I had trouble connecting. Could you try again?'), 600)
      } finally {
        setTimeout(() => setSubmitting(false), 600)
      }
      return
    }

    const nextIdx = currentIdx + 1

    if (nextIdx < questions.length) {
      setTimeout(() => {
        setCurrentIdx(nextIdx)
        const acks = ['Got it.', 'Thanks for sharing that.', 'Noted.', "That's helpful context.", 'Understood.']
        const ack = acks[Math.floor(Math.random() * acks.length)]
        const fullText = `${ack} ${questions[nextIdx].question}`
        pushAgentMessage(fullText, questions[nextIdx].hint, true)
        setSubmitting(false)
      }, 600)
    } else {
      setTimeout(() => {
        pushAgentMessage('Perfect — I have everything I need. Thanks for sharing all of that.', null, true)
        setDone(true)
        setSubmitting(false)
        onComplete(newAnswers)
      }, 600)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="agent-chat">
      <div className="agent-chat-thread">
        {messages.map(msg => (
          <div key={msg.id} className={`chat-msg chat-msg-${msg.type}`}>
            {msg.type === 'agent' && (
              <div
                className="chat-agent-avatar"
                style={accentColor ? { background: accentColor, borderColor: accentColor } : {}}
                aria-label={agentName}
              >
                {agentAvatar}
              </div>
            )}
            <div
              className={`chat-bubble chat-bubble-${msg.type}`}
              style={msg.type === 'agent' && accentColor ? { borderLeftColor: accentColor } : {}}
            >
              <p className="chat-text">{msg.text}</p>
              {msg.hint && <p className="chat-hint">{msg.hint}</p>}
            </div>
          </div>
        ))}

        {submitting && (
          <div className="chat-msg chat-msg-agent">
            <div className="chat-agent-avatar">{agentAvatar}</div>
            <div className="chat-bubble chat-bubble-agent chat-typing">
              <span /><span /><span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Agent speaking indicator */}
      {isAgentSpeaking && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px',
          background: 'var(--accent-light)', borderRadius: 'var(--r-md)',
          fontSize: 11, color: 'var(--accent)', margin: '0 0 6px',
        }}>
          <span style={{ display: 'flex', gap: 2 }}>
            {[0, 1, 2, 3, 4].map(i => (
              <span key={i} style={{
                width: 3, height: 12, background: 'var(--accent)', borderRadius: 1,
                animation: `vti-wave 0.6s ease-in-out ${i * 0.1}s infinite alternate`,
              }} />
            ))}
          </span>
          <span>Agent is speaking...</span>
          <button
            className="btn btn-ghost btn-sm"
            onClick={stopAudio}
            type="button"
            style={{ padding: '2px 8px', fontSize: 10 }}
          >
            Skip
          </button>
        </div>
      )}

      {!done && currentQ && !submitting && (
        <div className="agent-chat-input">
          <VoiceTextInput
            value={inputVal}
            onChange={setInputVal}
            rows={3}
            placeholder={currentQ.placeholder || 'Type your answer, or tap the mic to speak...'}
            cleanWithAI={true}
            apiBase={apiBase}
            onKeyDown={handleKeyDown}
          />
          <div className="agent-chat-footer">
            {!dynamicEndpoint && (
              <span className="agent-chat-progress">
                {currentIdx + 1} of {questions.length}
              </span>
            )}
            {dynamicEndpoint && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span className="agent-chat-progress" style={{ color: 'var(--accent)' }}>
                  ✨ Interactive Mode
                </span>
                <span style={{ fontSize: 10, color: 'var(--text-3)' }}>
                  Say or type <strong>"done"</strong> to skip ahead
                </span>
              </div>
            )}
            <div style={{ display: 'flex', gap: 6 }}>
              {dynamicEndpoint && (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    setInputVal('done')
                    setTimeout(() => handleSubmit(), 50)
                  }}
                  type="button"
                  style={{ fontSize: 11, padding: '6px 10px' }}
                >
                  Skip Chat →
                </button>
              )}
              <button
                className="btn btn-primary"
                onClick={handleSubmit}
                disabled={!inputVal.trim() && !dynamicEndpoint && currentQ?.required !== false}
                type="button"
              >
                {dynamicEndpoint ? 'Send →' : (currentIdx === questions.length - 1 ? 'Submit →' : 'Next →')}
              </button>
            </div>
          </div>
        </div>
      )}

      {done && (
        <div className="agent-chat-done">
          <span className="agent-chat-done-icon">✓</span>
          <span className="agent-chat-done-text">All responses captured</span>
        </div>
      )}
    </div>
  )
}
