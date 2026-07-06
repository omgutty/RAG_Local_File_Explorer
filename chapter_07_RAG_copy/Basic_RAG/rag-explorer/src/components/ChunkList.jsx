// Renders the retrieved top-k chunks with a similarity bar + metadata.
export default function ChunkList({ chunks = [] }) {
  if (!chunks.length) return null
  return (
    <div className="chunks">
      {chunks.map((c, i) => {
        const pct = c.similarity != null ? Math.round(c.similarity * 100) : null
        return (
          <div className="chunk-card" key={c.id || i}>
            <div className="chunk-head">
              <span className="chunk-rank">#{i + 1}</span>
              <span className="chunk-meta">
                {c.metadata?.file ? `${c.metadata.file} · ` : ''}chunk {c.metadata?.index ?? '?'}
              </span>
              {pct != null && (
                <span className="chunk-score" title={`cosine distance ${c.distance?.toFixed(4)}`}>
                  {pct}% match
                </span>
              )}
            </div>
            {pct != null && (
              <div className="score-bar">
                <div className="score-fill" style={{ width: `${pct}%` }} />
              </div>
            )}
            <p className="chunk-text">{c.text}</p>
          </div>
        )
      })}
    </div>
  )
}
