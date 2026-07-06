// Nomic Embed via local Ollama. No API key, runs fully offline.
// `ollama pull nomic-embed-text` must have been run once.
const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434'
const EMBED_MODEL = process.env.EMBED_MODEL || 'nomic-embed-text'

async function embedOne(text) {
  const res = await fetch(`${OLLAMA_URL}/api/embeddings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: EMBED_MODEL, prompt: text }),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`Ollama embed failed (${res.status}): ${detail || res.statusText}. Is Ollama running and "${EMBED_MODEL}" pulled?`)
  }
  const data = await res.json()
  if (!Array.isArray(data.embedding)) throw new Error('Ollama returned no embedding vector')
  return data.embedding
}

// Embeds many texts sequentially (nomic is fast locally; keeps memory flat).
export async function embedTexts(texts, onProgress) {
  const out = []
  for (let i = 0; i < texts.length; i++) {
    out.push(await embedOne(texts[i]))
    if (onProgress) onProgress(i + 1, texts.length)
  }
  return out
}

export async function embedQuery(text) {
  return embedOne(text)
}

export const embedInfo = { model: EMBED_MODEL, provider: 'ollama (local)' }
