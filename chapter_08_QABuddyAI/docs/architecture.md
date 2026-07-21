# QABuddy.ai architecture

```
data/01..10   +   JIRA (MCP / REST + JQL)   +   git clones (repos 01, 02)
      |
      v
INGEST  (python -m app.ingestion.cli / UI panel)
  load (per-source loader) -> normalize -> chunk (per-source strategy)
  -> BGE-M3 encode (dense 1024d + lexical sparse, ONE pass)
  -> Qdrant upsert (stable uuid5 ids; manifest diff = only changed files re-embed)
      |
      v
QDRANT  (one collection `qabuddy_kb`, named vectors dense+sparse,
         payload indexes: source_type, repo, path, ticket_key, tc_id, ...)
      |
      v
ASK  (app/retrieval.py)
  condense follow-up (history) -> [optional] LLM query rewrite (3 variants)
  -> dense + sparse search per variant (payload-filtered by selected sources)
  -> RRF fuse (k=60) -> bge-reranker-v2-m3 top-12 -> keep top-6
  -> threshold gate (below 0.22 -> "not in KB", no invented answers)
  -> mode prompt (answer | generate | review | rca) + glossary
  -> Groq openai/gpt-oss-120b (stream) -> answer with [n] citations
      |
      v
UI  (Flask + SSE): chat stream, source filter chips, citation cards
    (file:line / VWO-123 / doc p.X / build #N), ingest panel, KB stats
```

## Why these pieces

- **BGE-M3**: one open (MIT) model gives dense semantics AND lexical sparse
  weights, so exact ids (`VWO-123`, `NoSuchElementException`, `doLogin`) and
  fuzzy intent both retrieve. 8k context; runs CPU. Proven in ch07.
- **Qdrant**: named dense+sparse vectors in one point, filters, snapshots,
  tiny RAM (Rust). Embedded mode locally, server container on the droplet,
  switched by `QDRANT_URL` only.
- **Reranker**: cross-encoder is the answer-quality and token-efficiency lever;
  only the top-6 chunks (~2.5-3k tokens) reach the LLM.
- **gpt-oss-120b on Groq**: open-weight brain, hosted for speed, swappable to
  local Ollama by changing `LLM_BASE_URL`/`LLM_MODEL`.

## Chunking summary (config.yaml)

| Source | Unit | Overlap |
|---|---|---|
| Code repos | 1 method/class (brace-aware, breadcrumb + line numbers) | 0 |
| Test cases | 1 row | 0 |
| JIRA | 1 ticket (comments spill) | 0 |
| Docs / PRD / Lucid | ~512 tok heading-aware | 15% |
| Transcripts | speaker-turn windows ~900 tok | ~13% |
| Jenkins | failure block + build summary | 0 |

## Trust chain

Every chunk payload carries `source_type, path, repo, line_start/end,
ticket_key, tc_id, page, build_id`, so citations are exact and clickable. If
the best rerank score is below the threshold, QABuddy says the KB does not
contain the answer instead of hallucinating.
