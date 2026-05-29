export default function SkillBar({ value, onChange, disabled }) {
  return (
    <div className="flex items-start gap-3 px-5 py-2.5 bg-zinc-900 border-b border-zinc-800 flex-shrink-0">
      <span className="text-xs font-semibold text-indigo-400 whitespace-nowrap pt-1.5 select-none">
        🎯 Skill / Domain
      </span>
      <textarea
        className={`flex-1 bg-zinc-800 border rounded-lg text-xs text-zinc-200
                   font-sans px-3 py-1.5 resize-none outline-none leading-relaxed
                   placeholder-zinc-600 transition-opacity
                   ${disabled
                     ? 'border-zinc-800 opacity-40 cursor-not-allowed'
                     : 'border-zinc-700 focus:border-indigo-500'}`}
        rows={2}
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
        placeholder={
          "Optional: your domain, tech stack, or interview focus.\n" +
          "e.g. Backend engineer · Python, FastAPI, PostgreSQL · System design focus"
        }
      />
    </div>
  )
}
