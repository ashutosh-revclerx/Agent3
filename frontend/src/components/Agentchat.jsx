import { useEffect, useRef, useState } from 'react'
import VoiceTextInput from './Voicetextinput'

let msgId = 0
const nextId = () => ++msgId

export default function AgentChat({
  questions = [],
  onComplete,
  agentName = 'AI Facilitator',
  agentAvatar = 'â—ˆ',
  apiBase = '',
  accentColor,
}) {
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState({})
  const [inputVal, setInputVal] = useState('')
  const [messages, setMessages] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const bottomRef = useRef(null)
  const seededQuestionRef = useRef(null)

  const currentQ = questions[currentIdx]

  useEffect(() => {
    if (questions.length === 0) return
    const firstQuestion = questions[0].question
    if (seededQuestionRef.current === firstQuestion) return
    seededQuestionRef.current = firstQuestion

    const timeoutId = setTimeout(() => {
      setMessages([{
        type: 'agent',
        text: firstQuestion,
        hint: questions[0].hint,
        id: nextId(),
      }])
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

  const pushAgentAck = (nextQuestion, hint) => {
    const acks = [
      'Got it.',
      'Thanks for sharing that.',
      'Noted.',
      'That\'s helpful context.',
      'Understood.',
    ]
    const ack = acks[Math.floor(Math.random() * acks.length)]
    setMessages(prev => [...prev, {
      type: 'agent',
      text: nextQuestion ? `${ack} ${nextQuestion}` : ack,
      hint,
      id: nextId(),
    }])
  }

  const handleSubmit = () => {
    const val = inputVal.trim()
    if (!val && currentQ?.required !== false) return

    const newAnswers = { ...answers, [currentQ.field]: val }
    setAnswers(newAnswers)
    pushUser(val)
    setInputVal('')

    const nextIdx = currentIdx + 1

    if (nextIdx < questions.length) {
      setSubmitting(true)
      setTimeout(() => {
        setCurrentIdx(nextIdx)
        pushAgentAck(questions[nextIdx].question, questions[nextIdx].hint)
        setSubmitting(false)
      }, 600)
    } else {
      setSubmitting(true)
      setTimeout(() => {
        setMessages(prev => [...prev, {
          type: 'agent',
          text: 'Perfect ” I have everything I need. Thanks for sharing all of that.',
          id: nextId(),
        }])
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
            <span className="agent-chat-progress">
              {currentIdx + 1} of {questions.length}
            </span>
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={!inputVal.trim() && currentQ.required !== false}
              type="button"
            >
              {currentIdx === questions.length - 1 ? 'Submit â†’' : 'Next â†’'}
            </button>
          </div>
        </div>
      )}

      {done && (
        <div className="agent-chat-done">
          <span className="agent-chat-done-icon">âœ“</span>
          <span className="agent-chat-done-text">All responses captured</span>
        </div>
      )}
    </div>
  )
}
