import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Pipeline from './components/Pipeline.jsx'
import ChunkList from './components/ChunkList.jsx'
import * as api from './lib/api.js'

const SAMPLE_QUESTIONS = [
  'What is the goal of this PRD?',
  'Who are the target users?',
  'What are the key features described?',
  'What are the success metrics?',
]

export default function App() {
  const [status, setStatus] = useState(null)
  const [stageState, setStageState] = useState({})
  const [ingesting, setIngesting] = useState(false)
  const [ingest, setIngest] = useState(null)
  const [question, setQuestion] = useState('')
  const [querying, setQuerying] = useState(false)
  const [result, setResult] = useState(null)
  const [showPrompt, setShowPrompt] = useState(false)
  const [error, setError] = useState('')

  const refreshStatus = () => api.getStatus().then(setStatus).catch((e) => setError(e.message))

  useEffect(() => { refreshStatus() }, [])

  // reflect ingested state in the pipeline lights on load
  useEffect(() => {
    if (status?.chroma?.stored) {
      setStageState((s) => ({ ...s, pdf: 'done', chunk: 'done', embed: 'done', store: 'done' }))
      if (status.lastIngest) setIngest(status.lastIngest)
    }
  }, [status])

  async function handleIngest() {
    setError(''); setIngesting(true); setResult(null)
    setStageState({ pdf: 'active' })
    try {
      // visual staging — the backend does it all in one call, we animate the steps
      await sleep(250); setStageState({ pdf: 'done', chunk: 'active' })
      await sleep(250); setStageState({ pdf: 'done', chunk: 'done', embed: 'active' })
      const data = await api.ingest()
      setStageState({ pdf: 'done', chunk: 'done', embed: 'done', store: 'active' })
      await sleep(300)
      setStageState({ pdf: 'done', chunk: 'done', embed: 'done', store: 'done' })
      setIngest(data)
      await refreshStatus()
    } catch (e) {
      setError(e.message); setStageState({})
    } finally {
      setIngesting(false)
    }
  }

  async function handleQuery(q) {
    const ask = (q ?? question).trim()
    if (!ask) return
    setError(''); setQuerying(true); setResult(null)
    setStageState((s) => ({ ...s, retrieve: 'active', answer: 'idle' }))
    try {
      const data = await api.query(ask)
      setStageState((s) => ({ ...s, retrieve: 'done', answer: 'active' }))
      await sleep(200)
      setResult(data)
      setStageState((s) => ({ ...s, retrieve: 'done', answer: 'done' }))
    } catch (e) {
      setError(e.message); setStageState((s) => ({ ...s, retrieve: 'idle', answer: 'idle' }))
    } finally {
      setQuerying(false)
    }
  }

  async function handleReset() {
    await api.reset().catch(() => {})
    setIngest(null); setResult(null); setStageState({}); refreshStatus()
  }

  const ready = status?.chroma?.stored > 0 || ingest
  const chromaDown = status && !status.chroma?.up
  const groqMissing = status && !status.groqKeySet

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>RAG Explorer</h1>
          <p className="tagline">PDF → chunk → Nomic embed → ChromaDB → retrieve top-4 → Groq answer</p>
        </div>
        <div className="badges">
          <Badge ok={status?.chroma?.up} label="ChromaDB" />
          <Badge ok={status?.embed} label={status?.embed?.model || 'embed'} note="ollama" />
          <Badge ok={status?.groqKeySet} label={status?.llm?.model || 'groq'} note="groq" />
        </div>
      </header>

      <Pipeline stageState={stageState} />

      {(chromaDown || groqMissing || error) && (
        <div className="alerts">
          {chromaDown && <div className="alert warn">ChromaDB not reachable at {status?.chroma?.url}. Run <code>npm run chroma</code>.</div>}
          {groqMissing && <div className="alert warn">GROQ_API_KEY missing — add it to <code>.env</code> to generate answers.</div>}
          {error && <div className="alert err">{error}</div>}
        </div>
      )}

      <div className="grid">
        {/* -------- Ingestion -------- */}
        <section className="panel">
          <div className="panel-head">
            <h2>1 · Ingestion</h2>
            <div className="panel-actions">
              <button className="btn primary" onClick={handleIngest} disabled={ingesting}>
                {ingesting ? 'Ingesting…' : 'Ingest PDF'}
              </button>
              {ready && <button className="btn ghost" onClick={handleReset} disabled={ingesting}>Reset</button>}
            </div>
          </div>

          <div className="source">
            <span className="muted">Source folder:</span> <code>{status?.dataDir || 'data/'}</code>
            <ul className="file-list">
              {(status?.pdfs || []).map((f) => <li key={f}>📄 {f}</li>)}
              {!status?.pdfs?.length && <li className="muted">no PDFs found</li>}
            </ul>
          </div>

          {ingest && (
            <div className="stats">
              <Stat label="Pages" value={sum(ingest.files, 'numPages')} />
              <Stat label="Chunks" value={ingest.totalChunks} />
              <Stat label="Embed dims" value={ingest.embedDims} />
              <Stat label="Stored" value={status?.chroma?.stored ?? ingest.totalChunks} />
            </div>
          )}

          {ingest?.sampleVector && (
            <div className="vector">
              <span className="muted">Sample embedding (first 8 of {ingest.embedDims}):</span>
              <code className="vec">[{ingest.sampleVector.map((n) => n.toFixed(4)).join(', ')}, …]</code>
            </div>
          )}

          {ingest?.sampleChunks?.length > 0 && (
            <div className="samples">
              <span className="muted">Chunk preview:</span>
              {ingest.sampleChunks.map((c) => (
                <div className="sample-chunk" key={c.index}>
                  <span className="chunk-rank">chunk {c.index}</span>
                  <span className="chunk-meta">{c.length} chars</span>
                  <p>{c.preview}…</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* -------- Query -------- */}
        <section className="panel">
          <div className="panel-head"><h2>2 · Ask the document</h2></div>

          <div className="ask">
            <textarea
              rows={3}
              placeholder={ready ? 'Ask something about the PRD…' : 'Ingest the PDF first, then ask a question.'}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleQuery() }}
              disabled={!ready}
            />
            <button className="btn primary" onClick={() => handleQuery()} disabled={!ready || querying}>
              {querying ? 'Thinking…' : 'Ask'}
            </button>
          </div>

          <div className="suggestions">
            {SAMPLE_QUESTIONS.map((q) => (
              <button key={q} className="chip" disabled={!ready || querying}
                onClick={() => { setQuestion(q); handleQuery(q) }}>{q}</button>
            ))}
          </div>

          {result && (
            <div className="result">
              <div className="answer">
                <div className="answer-head">
                  <h3>Answer</h3>
                  <span className="muted small">{result.model}{result.usage ? ` · ${result.usage.total_tokens} tok` : ''}</span>
                </div>
                <div className="markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>
                </div>
                <button className="link" onClick={() => setShowPrompt((v) => !v)}>
                  {showPrompt ? 'Hide' : 'Show'} the augmented prompt sent to Groq
                </button>
                {showPrompt && <pre className="prompt">{result.prompt}</pre>}
              </div>

              <div className="retrieved">
                <h3>Retrieved context · top {result.topK}</h3>
                <ChunkList chunks={result.retrieved} />
              </div>
            </div>
          )}
        </section>
      </div>

      <footer className="foot">
        Chapter 07 · Basic RAG — local vector DB (ChromaDB) + Nomic Embed + Groq. Built for The Testing Academy.
      </footer>
    </div>
  )
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const sum = (arr, key) => (arr || []).reduce((a, x) => a + (x[key] || 0), 0)

function Badge({ ok, label, note }) {
  return (
    <span className={`badge ${ok ? 'on' : 'off'}`} title={note || ''}>
      <span className="dot" /> {label}
    </span>
  )
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span className="stat-value">{value ?? '—'}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}
