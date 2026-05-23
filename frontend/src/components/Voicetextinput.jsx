import { useState, useRef, useEffect } from 'react'

/**
 * VoiceTextInput
 * A textarea with an optional mic button alongside it.
 * Participant can type freely OR speak — transcript lands in the same field.
 *
 * Props:
 *   value          string   — controlled value
 *   onChange       fn       — called with new string value
 *   placeholder    string
 *   rows           number   — textarea rows (default 4)
 *   label          string   — field label shown above
 *   hint           string   — small hint below field
 *   aiQuestion     string   — if set, plays via ElevenLabs on mount
 *   onAudioEnd     fn       — called when AI audio finishes playing
 *   onRecordingStop fn      — called with the final text when the mic stops
 *   cleanWithAI    bool     — whether to clean messy transcripts via Gemini
 *   apiBase        string   — backend URL for /ai/speak and /ai/clean
 *   disabled       bool
 *   minLength      number   — minimum chars for validation
 *   style          object
 */

const MIC_STATES = { idle: 'idle', recording: 'recording', processing: 'processing' }

export default function VoiceTextInput({
  value = '',
  onChange,
  onKeyDown,
  placeholder = 'Type your answer, or tap the mic to speak...',
  rows = 4,
  label,
  hint,
  aiQuestion,
  onAudioEnd,
  onRecordingStop,
  cleanWithAI = true,
  apiBase = '',
  disabled = false,
  minLength = 0,
  style = {},
}) {
  const [micState,       setMicState]       = useState(MIC_STATES.idle)
  const [isCleaned,      setIsCleaned]      = useState(false)
  const [isPlayingAI,    setIsPlayingAI]    = useState(false)
  const [micError,       setMicError]       = useState(null)
  const [liveTranscript, setLiveTranscript] = useState('') // shown while recording

  const recognitionRef = useRef(null)
  const audioRef       = useRef(null)
  const audioUrlRef    = useRef(null)
  const textareaRef    = useRef(null)

  const valueRef = useRef(value)
  const onChangeRef = useRef(onChange)

  useEffect(() => {
    valueRef.current = value
    onChangeRef.current = onChange
  }, [value, onChange])

  const lastPlayedRef = useRef('')

  // ── Play AI question via ElevenLabs on mount ─────────────────────────────
  useEffect(() => {
    if (!aiQuestion || !apiBase) return
    // Prevent double-playing if component re-renders or mounts twice in StrictMode
    if (lastPlayedRef.current === aiQuestion) return
    
    lastPlayedRef.current = aiQuestion
    playAIQuestion(aiQuestion)
    return () => stopAudio()
  }, [aiQuestion, apiBase])

  const playAIQuestion = async (text) => {
    if (!text) return
    setIsPlayingAI(true)
    try {
      const res = await fetch(`${apiBase}/ai/speak`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
        },
        body: JSON.stringify({ text }),
      })
      if (!res.ok) throw new Error('speak failed')
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      audioUrlRef.current = url
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => {
        setIsPlayingAI(false)
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current)
          audioUrlRef.current = null
        }
        if (onAudioEnd) onAudioEnd()
      }
      audio.onerror = () => setIsPlayingAI(false)
      audio.play()
    } catch {
      // ElevenLabs not configured — silently skip, form still works
      setIsPlayingAI(false)
      if (onAudioEnd) onAudioEnd()
    }
  }

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }
    setIsPlayingAI(false)
  }

  // ── Speech recognition ───────────────────────────────────────────────────
  const startRecording = () => {
    setMicError(null)
    console.log('[VoiceTextInput] startRecording called')

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      const errMsg = 'Speech recognition not supported in this browser. Please use Chrome or Edge.'
      console.warn('[VoiceTextInput]', errMsg)
      setMicError(errMsg)
      return
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.continuous     = true
      recognition.interimResults = true
      recognition.lang           = 'en-US'
      recognitionRef.current = recognition

      recognition.onstart = () => {
        console.log('[VoiceTextInput] Recording started')
        setMicState(MIC_STATES.recording)
      }

      recognition.onresult = (e) => {
        let interim = ''
        let final   = ''
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) final   += e.results[i][0].transcript
          else                       interim += e.results[i][0].transcript
        }
        setLiveTranscript(interim)
        if (final) {
          console.log('[VoiceTextInput] Final transcript:', final)
          const separator = valueRef.current.trim().length > 0 ? ' ' : ''
          onChangeRef.current(valueRef.current + separator + final)
          setLiveTranscript('')
        }
      }

      recognition.onerror = (e) => {
        if (e.error === 'aborted') {
          // Normal — happens when recognition is stopped programmatically, not a real error
          setMicState(MIC_STATES.idle)
          setLiveTranscript('')
          return
        }

        console.error('[VoiceTextInput] Recognition error:', e.error)
        if (e.error === 'not-allowed') {
          setMicError('Microphone access denied. Please allow mic access in your browser settings.')
        } else if (e.error === 'no-speech') {
          setMicError('No speech detected. Please try again and speak clearly.')
        } else if (e.error === 'network') {
          setMicError('Network error during speech recognition. Check your connection.')
        } else {
          setMicError(`Mic error: ${e.error}. Please try again.`)
        }
        setMicState(MIC_STATES.idle)
        setLiveTranscript('')
      }

      recognition.onend = () => {
        console.log('[VoiceTextInput] Recording ended')
        setLiveTranscript('')
        setMicState(prev => prev === MIC_STATES.recording ? MIC_STATES.idle : prev)
      }

      recognition.start()
    } catch (err) {
      console.error('[VoiceTextInput] Failed to start recognition:', err)
      setMicError('Failed to start microphone. Please check browser permissions.')
      setMicState(MIC_STATES.idle)
    }
  }

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setMicState(MIC_STATES.processing)

    // Optional: clean transcript with Gemini
    const currentValue = valueRef.current || value;
    if (onRecordingStop) {
      onRecordingStop(currentValue.trim())
    }
    if (cleanWithAI && currentValue.trim().length > 40 && apiBase) {
      cleanTranscript(currentValue)
    } else {
      setLiveTranscript('')
      setMicState(MIC_STATES.idle)
    }
  }

  const cleanTranscript = async (text) => {
    try {
      const res = await fetch(`${apiBase}/ai/clean-transcript`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
        },
        body: JSON.stringify({ text }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.cleaned && data.cleaned !== text) {
          onChange(data.cleaned)
          setIsCleaned(true)
        }
      }
    } catch {}
    setMicState(MIC_STATES.idle)
  }

  const toggleMic = () => {
    if (disabled) return
    if (micState === MIC_STATES.recording) stopRecording()
    else startRecording()
  }

  const charCount  = value.length
  const isValid    = minLength === 0 || charCount >= minLength
  const showCleaned = isCleaned && micState === MIC_STATES.idle

  return (
    <div className="vti-wrapper" style={style}>

      {/* Label row */}
      {label && (
        <div className="vti-label-row">
          <label className="input-label">{label}</label>
          {minLength > 0 && (
            <span style={{ fontSize: 10, color: isValid ? 'var(--green)' : 'var(--text-3)' }}>
              {charCount}/{minLength} min
            </span>
          )}
        </div>
      )}

      {/* AI speaking indicator */}
      {isPlayingAI && (
        <div className="vti-ai-speaking">
          <div className="vti-wave">
            <span /><span /><span /><span /><span />
          </div>
          <span className="vti-speaking-label">AI is asking the question...</span>
          <button
            className="btn btn-ghost btn-sm"
            onClick={stopAudio}
            type="button"
            style={{ padding: '4px 10px', fontSize: 11 }}
          >
            Skip
          </button>
        </div>
      )}

      {/* Textarea + mic button */}
      <div className="vti-input-row">
        <div className="vti-textarea-wrap">
          <textarea
            ref={textareaRef}
            className={`input vti-textarea ${micState === MIC_STATES.recording ? 'vti-listening' : ''}`}
            rows={rows}
            placeholder={placeholder}
            value={micState === MIC_STATES.recording && liveTranscript
              ? value + (value.trim() ? ' ' : '') + liveTranscript
              : value}
            onChange={e => {
              setIsCleaned(false)
              onChange(e.target.value)
            }}
            onKeyDown={onKeyDown}
            disabled={disabled}
            style={{ resize: 'vertical' }}
          />

          {/* Live transcript overlay indicator */}
          {micState === MIC_STATES.recording && (
            <div className="vti-recording-badge">
              <span className="vti-rec-dot" />
              Listening...
            </div>
          )}
        </div>

        {/* Mic button */}
        <button
          className={`vti-mic-btn vti-mic-${micState}`}
          onClick={toggleMic}
          type="button"
          disabled={disabled || micState === MIC_STATES.processing || isPlayingAI}
          title={micState === MIC_STATES.recording ? 'Stop recording' : 'Speak your answer'}
        >
          {micState === MIC_STATES.idle && (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          )}
          {micState === MIC_STATES.recording && (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2"/>
            </svg>
          )}
          {micState === MIC_STATES.processing && (
            <span className="spinner spinner-blue" style={{ width: 16, height: 16 }} />
          )}
        </button>
      </div>

      {/* Footer hints */}
      <div className="vti-footer">
        <div>
          {micError && <p className="inp-err-msg">{micError}</p>}
          {showCleaned && (
            <p style={{ fontSize: 11, color: 'var(--accent)', marginTop: 3 }}>
              ◈ AI tidied this up — edit freely
            </p>
          )}
          {hint && !micError && !showCleaned && (
            <p className="input-hint">{hint}</p>
          )}
        </div>
        {value.trim().length > 0 && (
          <span style={{ fontSize: 11, color: 'var(--text-3)', flexShrink: 0 }}>
            {charCount} chars
          </span>
        )}
      </div>
    </div>
  )
}
