// Groq chat completion. "OpenGPT 120B" => openai/gpt-oss-120b, OpenAI-compatible API.
const GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
const GROQ_MODEL = process.env.GROQ_MODEL || 'openai/gpt-oss-120b'

const SYSTEM_PROMPT =
  'You are a precise assistant answering questions about a Product Requirements Document (PRD). ' +
  'Answer ONLY from the provided context chunks. If the answer is not in the context, say so plainly ' +
  '("The document does not cover that."). Be concise, cite which chunk numbers you used, and never invent facts.'

// Builds the augmented prompt from retrieved chunks. Returned so the UI can show it.
export function buildPrompt(question, chunks) {
  const context = chunks
    .map((c, i) => `[Chunk ${i + 1}]\n${c.text}`)
    .join('\n\n---\n\n')
  return `Context from the PRD:\n\n${context}\n\n---\n\nQuestion: ${question}\n\nAnswer using only the context above.`
}

export async function generateAnswer(question, chunks) {
  const apiKey = process.env.GROQ_API_KEY
  if (!apiKey) throw new Error('GROQ_API_KEY is not set. Add it to .env (see .env.example).')

  const userPrompt = buildPrompt(question, chunks)
  const res = await fetch(GROQ_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      temperature: 0.2,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userPrompt },
      ],
    }),
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`Groq request failed (${res.status}): ${detail || res.statusText}`)
  }

  const data = await res.json()
  const answer = data.choices?.[0]?.message?.content?.trim() || '(no answer returned)'
  return {
    answer,
    prompt: userPrompt,
    model: GROQ_MODEL,
    usage: data.usage || null,
  }
}

export const groqInfo = { model: GROQ_MODEL, provider: 'groq' }
