import { useEffect, useRef } from 'react'

const SPEAKER_NAMES = {
  interviewer: 'Interviewer',
  interviewee: 'You',
}

export default function TranscriptPanel({ transcript, partials }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript, partials])

  const isEmpty = transcript.length === 0 && Object.keys(partials).length === 0

  return (
    <section className="flex flex-col w-[42%] min-w-[280px] overflow-hidden border-r border-zinc-800">
      {/* Panel header */}
      <div className="flex items-center gap-2 px-5 py-3 border-b border-zinc-800 flex-shrink-0">
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-zinc-500">
          Live Transcript
        </h2>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <div className="text-4xl opacity-20">🎙</div>
            <p className="text-sm text-zinc-600 italic">
              Transcript will appear here once listening starts…
            </p>
          </div>
        ) : (
          <>
            {transcript.map(turn => (
              <TurnCard key={turn.id} speaker={turn.speaker} text={turn.text} />
            ))}

            {Object.entries(partials).map(([speaker, text]) => (
              <TurnCard key={`p-${speaker}`} speaker={speaker} text={text} partial />
            ))}
          </>
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  )
}

function TurnCard({ speaker, text, partial = false }) {
  return (
    <div className={`turn-card ${speaker} ${partial ? 'partial' : ''}`}>
      <span className="speaker-label">
        {SPEAKER_NAMES[speaker] ?? speaker}
        {partial && <span className="ml-2 font-normal normal-case tracking-normal text-zinc-500">typing…</span>}
      </span>
      <p className="text-sm text-zinc-200 leading-relaxed">{text}</p>
    </div>
  )
}
