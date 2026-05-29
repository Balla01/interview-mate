import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

export default function SuggestionsPanel({ suggestion, done }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [suggestion])

  return (
    <section className="panel suggestions-panel">
      <h2 className="panel-title">
        AI Suggestions
        {!done && suggestion && <span className="streaming-dot" />}
      </h2>

      <div className="suggestions-body">
        {!suggestion && (
          <p className="empty-hint">
            Suggestions will stream here when the interviewer asks a question…
          </p>
        )}

        {suggestion && (
          <div className="suggestion-content">
            <ReactMarkdown>{suggestion}</ReactMarkdown>
            {!done && <span className="cursor">▌</span>}
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </section>
  )
}
