import { useRef, useState, useCallback, useEffect } from 'react'

const WS_URL = 'ws://localhost:8000/ws'

export function useWebSocket() {
  const wsRef = useRef(null)
  const [wsState, setWsState] = useState('disconnected')

  const [transcript, setTranscript] = useState([])
  const [partials, setPartials] = useState({})
  const [suggestion, setSuggestion] = useState('')
  const [suggestionDone, setSuggestionDone] = useState(true)
  const [sessionStatus, setSessionStatus] = useState('idle')

  const idRef = useRef(0)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return Promise.resolve()

    return new Promise((resolve) => {
      setWsState('connecting')
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => { setWsState('connected'); resolve() }
      ws.onerror = () => setWsState('error')
      ws.onclose = () => setWsState('disconnected')

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        switch (msg.type) {
          case 'session_started':
            setSessionStatus('running')
            setTranscript([])
            setPartials({})
            setSuggestion('')
            setSuggestionDone(true)
            break

          case 'session_stopped':
            setSessionStatus('idle')
            break

          case 'transcript_update': {
            const { speaker, text, is_final } = msg
            if (is_final) {
              setPartials(p => { const n = { ...p }; delete n[speaker]; return n })
              setTranscript(p => [...p, { id: idRef.current++, speaker, text, ts: Date.now() }])
            } else {
              setPartials(p => ({ ...p, [speaker]: text }))
            }
            break
          }

          case 'llm_suggestion_update': {
            const { text, done, reset } = msg
            if (reset)      { setSuggestion(''); setSuggestionDone(false) }
            else if (done)  { setSuggestionDone(true) }
            else            { setSuggestion(p => p + text) }
            break
          }

          default: break
        }
      }
    })
  }, [])

  const sendJSON = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  // Called by useAudio with an ArrayBuffer of PCM data
  const sendBinary = useCallback((buffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(buffer)
    }
  }, [])

  const startSession = useCallback(async (mode) => {
    await connect()
    sendJSON({ type: 'start_session', mode })
  }, [connect, sendJSON])

  const stopSession = useCallback(() => {
    sendJSON({ type: 'stop_session' })
  }, [sendJSON])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  return {
    wsState,
    sessionStatus,
    transcript,
    partials,
    suggestion,
    suggestionDone,
    startSession,
    stopSession,
    sendBinary,
  }
}
