import { useState } from 'react'
import Controls from './components/Controls'
import TranscriptPanel from './components/TranscriptPanel'
import SuggestionsPanel from './components/SuggestionsPanel'
import { useWebSocket } from './hooks/useWebSocket'
import { useAudio } from './hooks/useAudio'

export default function App() {
  const [mode, setMode] = useState('one_way')

  const {
    wsState, sessionStatus,
    transcript, partials,
    suggestion, suggestionDone,
    startSession, stopSession, sendBinary,
  } = useWebSocket()

  const {
    micActive, sysActive, error,
    startMic, startSystemAudio, stopAll,
  } = useAudio(sendBinary)

  const handleStart = async () => {
    await startSession(mode)
    await startMic()
  }

  const handleStop = () => {
    stopSession()
    stopAll()
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-icon">🎧</span>
          <h1 className="brand-name">InterviewMate</h1>
        </div>
        <Controls
          mode={mode}
          onModeChange={setMode}
          sessionStatus={sessionStatus}
          wsState={wsState}
          micActive={micActive}
          sysActive={sysActive}
          onStart={handleStart}
          onStop={handleStop}
          onSystemAudio={startSystemAudio}
        />
      </header>

      {error && <div className="warning-banner">⚠ {error}</div>}

      <main className="app-main">
        <TranscriptPanel transcript={transcript} partials={partials} />
        <SuggestionsPanel suggestion={suggestion} done={suggestionDone} />
      </main>
    </div>
  )
}
