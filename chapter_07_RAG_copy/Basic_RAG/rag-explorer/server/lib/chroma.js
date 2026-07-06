import { ChromaClient } from 'chromadb'
import { embedTexts, embedQuery } from './embed.js'

const CHROMA_URL = process.env.CHROMA_URL || 'http://localhost:8000'
const COLLECTION = process.env.CHROMA_COLLECTION || 'vwo_prd'

const client = new ChromaClient({ path: CHROMA_URL })

// We generate vectors ourselves (via Ollama) and hand them to Chroma, so the
// collection's own embedding function is never called. This custom EF just
// satisfies the client API and would use the same Nomic model if invoked.
const ollamaEF = {
  generate: async (texts) => embedTexts(texts),
}

export async function getCollection() {
  return client.getOrCreateCollection({
    name: COLLECTION,
    metadata: { 'hnsw:space': 'cosine', source: 'rag-explorer' },
    embeddingFunction: ollamaEF,
  })
}

export async function resetCollection() {
  try {
    await client.deleteCollection({ name: COLLECTION })
  } catch {
    // collection may not exist yet — fine
  }
  return getCollection()
}

// Stores pre-embedded chunks. ids/documents/embeddings/metadatas are parallel arrays.
export async function storeChunks(collection, { ids, documents, embeddings, metadatas }) {
  // Chroma caps batch size; 200 is comfortably safe for local.
  const BATCH = 200
  for (let i = 0; i < ids.length; i += BATCH) {
    await collection.add({
      ids: ids.slice(i, i + BATCH),
      documents: documents.slice(i, i + BATCH),
      embeddings: embeddings.slice(i, i + BATCH),
      metadatas: metadatas.slice(i, i + BATCH),
    })
  }
}

// Embeds the query, retrieves top-k, returns normalized results + the query vector.
export async function retrieve(collection, queryText, k = 4) {
  const queryEmbedding = await embedQuery(queryText)
  const res = await collection.query({
    queryEmbeddings: [queryEmbedding],
    nResults: k,
    include: ['documents', 'metadatas', 'distances'],
  })
  const docs = res.documents?.[0] || []
  const metas = res.metadatas?.[0] || []
  const dists = res.distances?.[0] || []
  const ids = res.ids?.[0] || []

  const results = docs.map((text, i) => {
    const distance = dists[i]
    return {
      id: ids[i],
      text,
      metadata: metas[i] || {},
      distance,
      // cosine distance -> similarity in [0,1] for display
      similarity: typeof distance === 'number' ? Math.max(0, 1 - distance) : null,
    }
  })
  return { results, queryEmbedding }
}

export async function countChunks(collection) {
  try {
    return await collection.count()
  } catch {
    return 0
  }
}

export async function pingChroma() {
  try {
    await client.heartbeat()
    return true
  } catch {
    return false
  }
}
