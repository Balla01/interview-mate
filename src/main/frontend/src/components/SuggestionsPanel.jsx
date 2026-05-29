import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

export default function SuggestionsPanel({ suggestion, done }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [suggestion])

  const isEmpty = !suggestion

  return (
    <section className="flex flex-col flex-1 overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center gap-2 px-5 py-3 border-b border-zinc-800 flex-shrink-0">
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-zinc-500">
          AI Suggestions
        </h2>
        {!done && suggestion && (
          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulseDot ml-1" />
        )}
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <div className="text-4xl opacity-20">💡</div>
            <p className="text-sm text-zinc-600 italic max-w-xs">
              AI suggestions will stream here when the interviewer asks a question…
            </p>
          </div>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none
            prose-p:text-zinc-300 prose-p:leading-relaxed
            prose-strong:text-indigo-300 prose-strong:font-semibold
            prose-ul:text-zinc-400 prose-li:marker:text-indigo-500
            prose-headings:text-zinc-200">
            <ReactMarkdown>{suggestion}</ReactMarkdown>
            {!done && <span className="inline-block w-0.5 h-4 bg-indigo-400 align-middle animate-blink ml-0.5" />}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  )
}
