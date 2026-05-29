import { useEffect, useRef } from 'react'

const SPEAKER_LABELS = {
  interviewer: 'Interviewer',
  interviewee: 'You',
  speaker_0: 'Speaker A',
  speaker_1: 'Speaker B',
  unknown: 'Speaker',
}

function label(speaker) {
  return SPEAKER_LABELS[speaker] ?? speaker
}

export default function TranscriptPanel({ transcript, partials }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript, partials])

  const activeSpeakers = Object.keys(partials).filter(s => partials[s])

  return (
    <section className="panel transcript-panel">
      <h2 className="panel-title">Live Transcript</h2>

      <div className="transcript-body">
        {transcript.length === 0 && activeSpeakers.length === 0 && (
          <p className="empty-hint">Transcript will appear here once listening starts…</p>
        )}

        {transcript.map(turn => (
          <div key={turn.id} className={`turn turn-${turn.speaker}`}>
            <span className="turn-label">{label(turn.speaker)}</span>
            <p className="turn-text">{turn.text}</p>
          </div>
        ))}

        {activeSpeakers.map(speaker => (
          <div key={`partial-${speaker}`} className={`turn turn-${speaker} partial`}>
            <span className="turn-label">{label(speaker)}</span>
            <p className="turn-text">{partials[speaker]}</p>
          </div>
        ))}

        <div ref={bottomRef} />
      </div>
    </section>
  )
}
