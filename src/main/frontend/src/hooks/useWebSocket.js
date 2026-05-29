import { useRef, useState, useCallback, useEffect } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

export function useWebSocket({ onDomainExtracted } = {}) {
  const wsRef              = useRef(null)
  const onDomainExtractedRef = useRef(onDomainExtracted)
  onDomainExtractedRef.current = onDomainExtracted   // always latest, no dep needed

  const [wsState, setWsState]       = useState('disconnected')
  const [sessionStatus, setSession] = useState('idle')
  const [transcript, setTranscript] = useState([])
  const [partials, setPartials]     = useState({})
  const [suggestion, setSuggestion] = useState('')
  const [suggestionDone, setSugDone]= useState(true)
  const [activeSpeaker, setActive]  = useState('interviewer')
  const idRef = useRef(0)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return Promise.resolve()
    return new Promise((resolve, reject) => {
      setWsState('connecting')
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen  = () => { setWsState('connected'); resolve() }
      ws.onerror = () => { setWsState('error'); reject(new Error('Cannot connect to backend at ' + WS_URL)) }
      ws.onclose = () => setWsState('disconnected')
      ws.onmessage = ({ data }) => {
        const msg = JSON.parse(data)
        switch (msg.type) {
          case 'domain_extracted':
            onDomainExtractedRef.current?.(msg.context)
            break
          case 'session_started':
            setSession('running')
            setTranscript([]); setPartials({})
            setSuggestion(''); setSugDone(true)
            setActive('interviewer')
            break
          case 'session_stopped':
            setSession('idle')
            break
          case 'transcript_update': {
            const { speaker, text, is_final } = msg
            if (is_final) {
              setPartials(p => { const n={...p}; delete n[speaker]; return n })
              setTranscript(p => [...p, { id: idRef.current++, speaker, text }])
            } else {
              setPartials(p => ({ ...p, [speaker]: text }))
            }
            break
          }
          case 'llm_suggestion_update':
            if (msg.reset)     { setSuggestion(''); setSugDone(false) }
            else if (msg.done) { setSugDone(true) }
            else               { setSuggestion(p => p + msg.text) }
            break
          case 'speaker_switched':
            setActive(msg.active)
            break
          default: break
        }
      }
    })
  }, [])

  const sendJSON    = useCallback(obj => wsRef.current?.readyState === 1 && wsRef.current.send(JSON.stringify(obj)), [])
  const sendBinary  = useCallback(buf => wsRef.current?.readyState === 1 && wsRef.current.send(buf), [])

  const startSession = useCallback(async (mode, domain = '') => {
    await connect()
    sendJSON({ type: 'start_session', mode, domain })
  }, [connect, sendJSON])

  const stopSession   = useCallback(() => sendJSON({ type: 'stop_session' }), [sendJSON])
  const switchSpeaker = useCallback(() => {
    sendJSON({ type: 'switch_speaker' })
    setActive(p => p === 'interviewer' ? 'interviewee' : 'interviewer')
  }, [sendJSON])

  useEffect(() => { connect(); return () => wsRef.current?.close() }, [connect])

  return {
    wsState, sessionStatus,
    transcript, partials,
    suggestion, suggestionDone,
    activeSpeaker,
    startSession, stopSession, switchSpeaker, sendBinary,
  }
}
