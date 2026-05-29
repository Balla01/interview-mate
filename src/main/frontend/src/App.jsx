import Header from './components/Header'
import TranscriptPanel from './components/TranscriptPanel'
import SuggestionsPanel from './components/SuggestionsPanel'
import { useWebSocket } from './hooks/useWebSocket'
import { useAudio } from './hooks/useAudio'
import { useState } from 'react'

export default function App() {
  const [mode, setMode] = useState('one_way')

  const {
    wsState, sessionStatus,
    transcript, partials,
    suggestion, suggestionDone,
    activeSpeaker,
    startSession, stopSession, switchSpeaker, sendBinary,
  } = useWebSocket()

  const { micActive, sysActive, audioError, startMic, startSystemAudio, stopAll } = useAudio(sendBinary)

  const handleStart = async () => {
    await startSession(mode)
    await startMic()
  }

  const handleStop = () => {
    stopSession()
    stopAll()
  }

  return (
    <div className="flex flex-col h-screen bg-zinc-950 select-none">
      <Header
        mode={mode}
        onModeChange={setMode}
        wsState={wsState}
        sessionStatus={sessionStatus}
        micActive={micActive}
        sysActive={sysActive}
        activeSpeaker={activeSpeaker}
        onStart={handleStart}
        onStop={handleStop}
        onSystemAudio={startSystemAudio}
        onSwitchSpeaker={switchSpeaker}
      />

      {/* Two-way hint */}
      {sessionStatus === 'running' && mode === 'two_way' && (
        <div className="bg-indigo-950/50 border-b border-indigo-900/50 px-5 py-1.5 text-xs text-indigo-300 flex-shrink-0">
          💡 Click <strong>Now: …</strong> in the header to switch who is speaking before each turn.
        </div>
      )}

      {/* Audio error */}
      {audioError && (
        <div className="bg-amber-950/60 border-b border-amber-900/50 px-5 py-1.5 text-xs text-amber-300 flex-shrink-0">
          ⚠ {audioError}
        </div>
      )}

      {/* Main panels */}
      <main className="flex flex-1 overflow-hidden">
        <TranscriptPanel transcript={transcript} partials={partials} />
        <SuggestionsPanel suggestion={suggestion} done={suggestionDone} />
      </main>
    </div>
  )
}
