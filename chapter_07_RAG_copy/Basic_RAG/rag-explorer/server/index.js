import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { listPdfs, extractPdf } from './lib/pdf.js'
import { chunkText } from './lib/chunk.js'
import { embedTexts, embedInfo } from './lib/embed.js'
import { getCollection, resetCollection, storeChunks, retrieve, countChunks, pingChroma } from './lib/chroma.js'
import { generateAnswer, groqInfo } from './lib/groq.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.resolve(__dirname, '..', process.env.DATA_DIR || '../data')
const CHUNK_SIZE = Number(process.env.CHUNK_SIZE || 1200)
const CHUNK_OVERLAP = Number(process.env.CHUNK_OVERLAP || 200)
const TOP_K = Number(process.env.TOP_K || 4)
const PORT = Number(process.env.PORT || 8787)

const app = express()
app.use(cors())
app.use(express.json({ limit: '2mb' }))

// Remembers the last ingestion so the UI can render the pipeline state.
let lastIngest = null

const wrap = (fn) => (req, res) => fn(req, res).catch((err) => {
  console.error(err)
  res.status(500).json({ error: err.message || String(err) })
})

// --- Status: what's wired up, what's ingested -------------------------------
app.get('/api/status', wrap(async (req, res) => {
  const chromaUp = await pingChroma()
  let stored = 0
  if (chromaUp) {
    const col = await getCollection()
    stored = await countChunks(col)
  }
  res.json({
    dataDir: DATA_DIR,
    pdfs: listPdfs(DATA_DIR).map((p) => p.file),
    embed: embedInfo,
    llm: groqInfo,
    groqKeySet: Boolean(process.env.GROQ_API_KEY),
    chroma: { url: process.env.CHROMA_URL || 'http://localhost:8000', up: chromaUp, stored },
    config: { chunkSize: CHUNK_SIZE, chunkOverlap: CHUNK_OVERLAP, topK: TOP_K },
    lastIngest,
  })
}))

// --- Ingest: PDF -> chunk -> embed -> store ---------------------------------
app.post('/api/ingest', wrap(async (req, res) => {
  const pdfs = listPdfs(DATA_DIR)
  if (!pdfs.length) return res.status(400).json({ error: `No PDFs found in ${DATA_DIR}` })

  const collection = await resetCollection() // fresh store each ingest
  const files = []
  let allChunks = []

  for (const pdf of pdfs) {
    const { text, numPages } = await extractPdf(pdf.path)
    const chunks = chunkText(text, { size: CHUNK_SIZE, overlap: CHUNK_OVERLAP })
    chunks.forEach((c) => { c.file = pdf.file })
    files.push({ file: pdf.file, numPages, chars: text.length, numChunks: chunks.length })
    allChunks = allChunks.concat(chunks)
  }

  const embeddings = await embedTexts(allChunks.map((c) => c.text))
  const dims = embeddings[0]?.length || 0

  await storeChunks(collection, {
    ids: allChunks.map((c, i) => `chunk_${i}`),
    documents: allChunks.map((c) => c.text),
    embeddings,
    metadatas: allChunks.map((c) => ({
      file: c.file, index: c.index, charStart: c.charStart, charEnd: c.charEnd, length: c.length,
    })),
  })

  lastIngest = {
    at: null, // timestamps set client-side to keep server deterministic
    files,
    totalChunks: allChunks.length,
    embedDims: dims,
    embedModel: embedInfo.model,
    // small preview so the UI can show real chunk text
    sampleChunks: allChunks.slice(0, 3).map((c) => ({
      index: c.index, file: c.file, length: c.length, preview: c.text.slice(0, 320),
    })),
    sampleVector: (embeddings[0] || []).slice(0, 8),
  }

  res.json(lastIngest)
}))

// --- Query: embed -> retrieve top-k -> Groq answer --------------------------
app.post('/api/query', wrap(async (req, res) => {
  const question = (req.body?.question || '').trim()
  if (!question) return res.status(400).json({ error: 'question is required' })

  const collection = await getCollection()
  const stored = await countChunks(collection)
  if (!stored) return res.status(400).json({ error: 'Nothing ingested yet. Click "Ingest PDF" first.' })

  const { results, queryEmbedding } = await retrieve(collection, question, TOP_K)
  const { answer, prompt, model, usage } = await generateAnswer(question, results)

  res.json({
    question,
    retrieved: results,
    answer,
    prompt,
    model,
    usage,
    queryVectorPreview: queryEmbedding.slice(0, 8),
    topK: TOP_K,
  })
}))

// --- Reset the vector store -------------------------------------------------
app.post('/api/reset', wrap(async (req, res) => {
  await resetCollection()
  lastIngest = null
  res.json({ ok: true })
}))

app.listen(PORT, () => {
  console.log(`RAG Explorer API on http://localhost:${PORT}`)
  console.log(`  data dir : ${DATA_DIR}`)
  console.log(`  embed    : ${embedInfo.model} (ollama)`)
  console.log(`  llm      : ${groqInfo.model} (groq)  key ${process.env.GROQ_API_KEY ? 'set' : 'MISSING'}`)
})
