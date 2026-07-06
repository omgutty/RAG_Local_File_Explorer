// The always-visible RAG flow. Each stage lights up as it becomes active/done.
const STAGES = [
  { key: 'pdf', label: 'PDF', sub: 'load document' },
  { key: 'chunk', label: 'Chunk', sub: 'split text' },
  { key: 'embed', label: 'Embed', sub: 'Nomic vectors' },
  { key: 'store', label: 'Store', sub: 'ChromaDB' },
  { key: 'retrieve', label: 'Retrieve', sub: 'top-4' },
  { key: 'answer', label: 'Answer', sub: 'Groq LLM' },
]

// stageState: map of key -> 'idle' | 'active' | 'done'
export default function Pipeline({ stageState = {} }) {
  return (
    <div className="pipeline">
      {STAGES.map((s, i) => (
        <div className="pipeline-item" key={s.key}>
          <div className={`stage stage-${stageState[s.key] || 'idle'}`}>
            <span className="stage-num">{i + 1}</span>
            <div className="stage-text">
              <strong>{s.label}</strong>
              <span>{s.sub}</span>
            </div>
          </div>
          {i < STAGES.length - 1 && <div className={`arrow arrow-${stageState[s.key] === 'done' ? 'lit' : 'dim'}`}>→</div>}
        </div>
      ))}
    </div>
  )
}
