// Character-based splitter with overlap. Tries to break on paragraph/sentence
// boundaries so chunks stay readable instead of cutting mid-word.
export function chunkText(text, { size = 1200, overlap = 200 } = {}) {
  const clean = text.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
  const chunks = []
  let start = 0

  while (start < clean.length) {
    let end = Math.min(start + size, clean.length)

    // If we're not at the very end, try to end on a nice boundary within the
    // last 30% of the window (paragraph break > sentence end > space).
    if (end < clean.length) {
      const window = clean.slice(start, end)
      const floor = Math.floor(size * 0.7)
      const para = window.lastIndexOf('\n\n')
      const sentence = Math.max(window.lastIndexOf('. '), window.lastIndexOf('.\n'))
      const space = window.lastIndexOf(' ')
      const cut = para > floor ? para : sentence > floor ? sentence + 1 : space > floor ? space : -1
      if (cut > 0) end = start + cut
    }

    const piece = clean.slice(start, end).trim()
    if (piece) {
      chunks.push({
        index: chunks.length,
        text: piece,
        charStart: start,
        charEnd: end,
        length: piece.length,
      })
    }

    if (end >= clean.length) break
    start = Math.max(end - overlap, start + 1)
  }

  return chunks
}
