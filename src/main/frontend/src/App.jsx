import Header from './components/Header'
import SkillBar from './components/SkillBar'
import TranscriptPanel from './components/TranscriptPanel'
import SuggestionsPanel from './components/SuggestionsPanel'
import { useWebSocket } from './hooks/useWebSocket'
import { useAudio } from './hooks/useAudio'
import { useState } from 'react'

export default function App() {
  const [mode, setMode] = useState('one_way')
  const [domain, setDomain] = useState('')
  const [domainExtracted, setDomainExtracted] = useState('')

  const {
    wsState, sessionStatus,
    transcript, partials,
    suggestion, suggestionDone,
    activeSpeaker,
    startSession, stopSession, switchSpeaker, sendBinary,
  } = useWebSocket({
    onDomainExtracted: (ctx) => setDomainExtracted(ctx),
  })

  const { micActive, sysActive, audioError, startMic, startSystemAudio, stopAll } = useAudio(sendBinary)

  const handleStart = async () => {
    setDomainExtracted('')
    await startSession(mode, domain)
    await startMic()
  }

  const handleStop = () => {
    stopSession()
    stopAll()
  }

  const isRunning = sessionStatus === 'running'

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

      {/* Skill / Domain input — always visible, disabled while session is running */}
      <SkillBar value={domain} onChange={setDomain} disabled={isRunning} />

      {/* Domain extracted confirmation */}
      {domainExtracted && isRunning && (
        <div className="bg-teal-950/60 border-b border-teal-800/50 px-5 py-1.5 text-xs text-teal-300 flex-shrink-0">
          ✅ Domain context active — {domainExtracted.split('\n')[0]}
        </div>
      )}

      {/* Two-way hint */}
      {isRunning && mode === 'two_way' && (
        <div className="bg-indigo-950/50 border-b border-indigo-900/50 px-5 py-1.5 text-xs text-indigo-300 flex-shrink-0">
          💡 <strong>In-Person Call:</strong> Click <strong>Now: …</strong> in the header to switch who is speaking before each turn.
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
