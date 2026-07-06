// Thin client for the RAG Explorer backend. All calls are same-origin /api and
// get proxied to Express by Vite (see vite.config.js).

async function jsonOrThrow(res) {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || `${res.status} ${res.statusText}`)
  return data
}

export const getStatus = () => fetch('/api/status').then(jsonOrThrow)

export const ingest = () =>
  fetch('/api/ingest', { method: 'POST' }).then(jsonOrThrow)

export const query = (question) =>
  fetch('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  }).then(jsonOrThrow)

export const reset = () =>
  fetch('/api/reset', { method: 'POST' }).then(jsonOrThrow)
