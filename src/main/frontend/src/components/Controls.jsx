export default function Controls({
  mode, onModeChange,
  sessionStatus, wsState,
  micActive, sysActive,
  onStart, onStop, onSystemAudio,
}) {
  const isRunning = sessionStatus === 'running'
  const isConnected = wsState === 'connected'

  return (
    <div className="controls">
      <div className="mode-selector">
        <button
          className={`mode-btn ${mode === 'one_way' ? 'active' : ''}`}
          onClick={() => !isRunning && onModeChange('one_way')}
          disabled={isRunning}
          title="Mic + system audio (online interview)"
        >
          One-way
        </button>
        <button
          className={`mode-btn ${mode === 'two_way' ? 'active' : ''}`}
          onClick={() => !isRunning && onModeChange('two_way')}
          disabled={isRunning}
          title="Single mic with speaker diarization (in-person)"
        >
          Two-way
        </button>
      </div>

      {/* System audio button — one-way mode only, while session is running */}
      {isRunning && mode === 'one_way' && (
        <button
          className={`action-btn sys-btn ${sysActive ? 'active' : ''}`}
          onClick={onSystemAudio}
          disabled={sysActive}
          title="Capture interviewer's voice from Zoom/Meet/Teams"
        >
          {sysActive ? '🔊 System On' : '🔊 Add System Audio'}
        </button>
      )}

      <div className="connection-status" data-state={wsState}>
        <span className="status-dot" />
        <span className="status-label">{wsState}</span>
      </div>

      {isRunning ? (
        <div className="running-controls">
          {micActive && <span className="mic-indicator">🎙 live</span>}
          <button className="action-btn stop-btn" onClick={onStop}>
            ■ Stop
          </button>
        </div>
      ) : (
        <button
          className="action-btn start-btn"
          onClick={onStart}
          disabled={!isConnected}
        >
          ● Start Listening
        </button>
      )}
    </div>
  )
}
