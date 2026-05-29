const STATUS_COLOR = {
  connected:    'bg-emerald-400',
  connecting:   'bg-amber-400 animate-pulse',
  disconnected: 'bg-zinc-500',
  error:        'bg-red-400',
}

const STATUS_LABEL = {
  connected:    'Connected',
  connecting:   'Connecting…',
  disconnected: 'Offline',
  error:        'Error',
}

export default function Header({
  mode, onModeChange,
  wsState, sessionStatus,
  micActive, sysActive, activeSpeaker,
  onStart, onStop, onSystemAudio, onSwitchSpeaker,
}) {
  const isRunning   = sessionStatus === 'running'
  const isConnected = wsState === 'connected'

  return (
    <header className="flex items-center justify-between gap-3 px-5 h-14 bg-zinc-900 border-b border-zinc-800 flex-shrink-0">

      {/* Brand */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className="text-xl">🎧</span>
        <span className="font-bold text-base tracking-tight text-zinc-100">InterviewMate</span>
      </div>

      {/* Center controls */}
      <div className="flex items-center gap-2">
        {/* Mode selector */}
        <div className="flex rounded-lg overflow-hidden border border-zinc-700 text-xs font-medium">
          {['one_way', 'two_way'].map(m => (
            <button
              key={m}
              disabled={isRunning}
              onClick={() => onModeChange(m)}
              className={`px-3 py-1.5 transition-colors ${
                mode === m
                  ? 'bg-indigo-600 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 disabled:cursor-not-allowed disabled:opacity-40'
              }`}
            >
              {m === 'one_way' ? 'Online Call' : 'In-Person Call'}
            </button>
          ))}
        </div>

        {/* Two-way speaker toggle */}
        {isRunning && mode === 'two_way' && (
          <button
            onClick={onSwitchSpeaker}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-all ${
              activeSpeaker === 'interviewer'
                ? 'bg-indigo-950 border-indigo-400 text-indigo-300 hover:bg-indigo-900'
                : 'bg-emerald-950 border-emerald-400 text-emerald-300 hover:bg-emerald-900'
            }`}
          >
            <span>🎙</span>
            <span>Now: <strong>{activeSpeaker === 'interviewer' ? 'Interviewer' : 'You'}</strong></span>
            <span className="text-[10px] opacity-60">— click to switch</span>
          </button>
        )}

        {/* One-way system audio */}
        {isRunning && mode === 'one_way' && (
          <button
            onClick={onSystemAudio}
            disabled={sysActive}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              sysActive
                ? 'bg-emerald-950 border-emerald-500 text-emerald-400 cursor-default'
                : 'bg-zinc-800 border-zinc-600 text-zinc-300 hover:bg-zinc-700 disabled:opacity-50'
            }`}
          >
            🔊 {sysActive ? 'System On' : 'Add System Audio'}
          </button>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Mic indicator */}
        {micActive && (
          <span className="flex items-center gap-1.5 text-xs text-red-400">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulseDot" />
            live
          </span>
        )}

        {/* Connection status */}
        <div className="flex items-center gap-1.5 text-xs text-zinc-400">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_COLOR[wsState] ?? 'bg-zinc-500'}`} />
          <span>{STATUS_LABEL[wsState] ?? wsState}</span>
        </div>

        {/* Start / Stop */}
        {isRunning ? (
          <button
            onClick={onStop}
            className="px-4 py-1.5 rounded-lg bg-red-950 border border-red-800 text-red-400 text-sm font-semibold hover:bg-red-900 transition-colors"
          >
            ■ Stop
          </button>
        ) : (
          <button
            onClick={onStart}
            disabled={!isConnected}
            className="px-4 py-1.5 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ● Start Listening
          </button>
        )}
      </div>
    </header>
  )
}
