# QABuddy.ai: Phase 1 Plan

> On approval, step 0 copies this file to `chapter_08_QABuddyAI/Plan.md` (final version, as requested).

## Context

Chapter 08 capstone. Self-hosted, multi-source hybrid RAG for the QA team: one question -> one cited answer, grounded in the Selenium framework, Playwright framework, ~5,000 test cases, JIRA history, PRDs/company docs, meeting transcripts, Lucid exports, and Jenkins logs. Runs 24x7 on a DigitalOcean droplet, token-efficient, open-source embedding model + vector DB.

Key fact from recon: `chapter_07_RAG/Advance_RAG/` already proved the exact core stack on one CSV source (BGE-M3 dense+sparse, Qdrant named vectors, RRF fusion, bge-reranker-v2-m3, Groq `openai/gpt-oss-120b`). QABuddy is that stack productionized: 10 sources, per-source chunking, citations, server deploy, eval, backup. Team already knows the stack -> lower risk, direct code reuse.

## How I thought about it

1. QA queries mix exact identifiers (`VWO-123`, `NoSuchElementException`, `doLogin()`) with fuzzy intent ("why is login flaky"). Dense-only misses identifiers, keyword-only misses intent. So: hybrid (dense + lexical sparse), RRF fusion, then cross-encoder rerank.
2. Token efficiency lever = reranking. Answer is built from top 5-6 chunks only: ~2.5-3k prompt tokens per query, ~500 out.
3. `data/` folders = source of truth. Qdrant = disposable derived index. Stable chunk IDs (content hash) -> idempotent upserts -> Phase 2 hourly sync is just a cron job, no redesign.
4. One collection + payload filters, not 10 collections. One question can pull a test case + PRD section + JIRA bug together; filters still allow scoping ("search only Playwright repo").
5. Trust first: every chunk carries a breadcrumb + metadata for exact citations. If best rerank score < threshold -> "not found in KB", never invented answers.
6. Maximum reuse of ch07 code (same models, same fusion, same reranker workaround, same env var names).

## Decision 1: Embedding model -> `BAAI/bge-m3` (one model, dense + sparse)

| Aspect | Detail |
|---|---|
| Model | `BAAI/bge-m3` via FlagEmbedding, MIT license, runs local CPU |
| Outputs | 1024-dim dense AND learned lexical sparse weights in ONE `encode()` pass |
| Context | 8,192 tokens: long JIRA tickets / test rows never truncate |
| Why hybrid-native | Sparse side does lexical matching (SPLADE-style) -> catches exact IDs, exception names, method names without a separate BM25 index |
| Reranker | `BAAI/bge-reranker-v2-m3` cross-encoder, top-12 -> keep top-6. Biggest answer-quality + token-saving lever. Loaded via raw `transformers` (existing workaround: `learnings/2026-07-12-flagembedding-reranker-bypass.md`) |

Rejected:
- Code-specialized dual model (jina-code): two embedding spaces + routing complexity; sparse lexical + reranker already catch identifier queries.
- `nomic-embed-text` (used in ch07 Basic_RAG): dense-only, needs separate BM25 for hybrid; weaker retrieval quality.
- OpenAI/Cohere embeddings: violates open-source + self-host constraint.

## Decision 2: Vector DB -> Qdrant (server mode, Docker)

- Native hybrid: named `dense` + `sparse` vectors in one point, server-side fusion. ch07 collection schema carries over almost unchanged.
- Rust, low RAM (~300MB + vectors), int8 quantization available. Estimated corpus 20-60k chunks -> under 500MB. Fits an 8GB droplet with headroom.
- Payload indexes -> per-source filters; built-in snapshots -> nightly backup.
- Change vs ch07: ch07 used embedded mode (`QdrantClient(path=...)`), single process only. QABuddy runs the Qdrant Docker container (`QDRANT_URL`) so ingest cron + web app + backups access it concurrently, 24x7. `rag_core.py` already supports `QDRANT_URL` env, so this is config, not code.

Rejected: Weaviate (2-3x RAM), Milvus (infra overkill under 1M vectors), Chroma (no true hybrid ranking; fine for ch07 Basic_RAG learning, not production), pgvector (manual fusion glue, no Postgres in stack today), OpenSearch (JVM 2-4GB floor).

## Decision 3: Chunk size + overlap, per source

Repos confirmed via GitHub API: Selenium = Java (small repo), Playwright = TypeScript (+HTML reports to exclude).

| # | Source | Strategy | Target size | Overlap |
|---|---|---|---|---|
| 1 | Selenium repo (Java) | Structure-aware: 1 method/class per chunk (tree-sitter), file breadcrumb header | 300-500 tok | 0 (50 tok only when splitting an oversized method) |
| 2 | Playwright repo (TS) | Same; also spec files kept whole per `test()` block | 300-500 tok | same |
| 3 | Test cases CSV/XLSX | 1 row = 1 chunk, serialized as `Field: value` lines | row (~100-300 tok) | 0 |
| 4 | JIRA tickets | 1 ticket = 1 chunk (summary + description + key comments); long threads spill to linked extra chunks | up to 1,200 tok | 0 |
| 5 | Company docs (PDF/MD) | Heading-aware recursive split, tables -> markdown | 512 tok | 76 tok (15%) |
| 6 | Figma | Phase 2 placeholder folder only | - | - |
| 7 | Transcripts | Speaker-turn aware windows | 800-1,000 tok | 120 tok |
| 8 | Lucid exports (text) | Same as docs | 512 tok | 76 tok |
| 9 | PRD/SRS/BRD/FRD (PDF) | Same as docs, page numbers kept for citation | 512 tok | 76 tok |
| 10 | Jenkins logs | Failure-block extraction: stack trace + surrounding test context = 1 unit, plus 1 summary chunk per build | 300-600 tok | 0 |

Why: code, rows, tickets, and failure blocks are atomic units; overlap would bleed unrelated content into citations. Prose needs ~15% overlap to survive boundary cuts. Transcripts are diffuse -> bigger windows, more overlap. Logs: only failures + summaries indexed; full console spam is noise + token waste (retention window default 90 days). All numbers live in `config.yaml`, tunable per source without code changes.

(ch07's `chunk_text(size=1000 chars, overlap=150)` in `rag_core.py` is reused as the prose splitter core, extended to heading/speaker awareness.)

## Decision 4: Preprocessing / normalization

Universal: UTF-8 normalize, strip ANSI/control chars, collapse whitespace, dedupe by content hash, stable chunk ID = sha256(source + path + content) -> idempotent re-ingest.

Per source:
- Code: skip vendored/generated (`node_modules/`, `target/`, `test-results/`, `playwright-report/`, `*.html` reports); keep comments (intent lives there); prepend breadcrumb line, e.g. `[selenium-framework] src/main/java/.../LoginPage.java > LoginPage.doLogin()`.
- CSV/XLSX: pandas, header normalization, drop empty rows; module/suite -> metadata and text.
- PDF: PyMuPDF, drop repeating headers/footers, tables -> markdown, keep page numbers.
- JIRA: ADF -> plain text, strip quoted-reply noise; status/priority/labels/components -> metadata.
- Jenkins: strip timestamps + ANSI; failed test name + exception class -> metadata.
- Transcripts: keep speaker + timestamp markers.

Terminology: `glossary.yaml` (company/VWO terms, abbreviations) injected into the system prompt, NOT into embeddings. camelCase/snake_case identifiers get split copies for lexical matching, originals kept too.

Metadata payload on every chunk: `source_type, path/url, repo, language, heading_trail, line_start, line_end, ticket_key, ticket_status, tc_id, module, build_id, date, hash`. Powers both filters and citations.

## Decision 5: Architecture

```
data/01..10  +  JIRA (MCP/REST, JQL)  +  git clones (repos 1-2)
        |
   INGEST (Python CLI: qabuddy ingest [--source N])
   load -> clean -> chunk (per-source) -> BGE-M3 encode (dense+sparse) -> Qdrant upsert (stable IDs)
        |
   QDRANT (Docker, named vectors dense+sparse, payload indexes, snapshots)
        |
   ASK PIPELINE (Flask API, reuses ch07 flow)
   query -> [optional LLM query-rewrite, 3 variants] -> dense + sparse search per variant
         -> RRF fuse (k=60) -> rerank top-12 -> top-6 (threshold else "not in KB")
         -> prompt with numbered chunks -> LLM -> answer + [n] citations
        |
   CHAT UI (SSE streaming, source filter chips, citation cards: file:lines / VWO-123 / doc p.X)
```

- Stack: Python 3.11+, Flask (ch07 pattern: `app.py`, `static/`, `templates/`), FlagEmbedding, qdrant-client, tree-sitter, PyMuPDF, pandas. Same env vars as ch07 (`LLM_BASE_URL`, `LLM_MODEL`, `GROQ_API_KEY`, `QDRANT_URL`).
- Generation LLM (CONFIRMED by you): Groq + `openai/gpt-oss-120b` via `.env` (`GROQ_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`), same as ch07. Open-weight model (Apache-2.0), hosted for speed, near-zero cost. Swap = 2 env vars (any OpenAI-compatible API or local Ollama for airgap).
- Modes: extends ch07 `detect_mode`: answer / generate-test-cases / review / RCA prompt templates, auto-detected + UI override chip.
- Deploy: `docker-compose.yml` = qdrant + app (gunicorn) + caddy (TLS + basic-auth). DO cloud firewall, internal use only. `restart: unless-stopped`, healthchecks.
- Backups: nightly cron: Qdrant snapshot + `data/` manifest, optional push to DO Spaces. Recovery = restore snapshot OR re-ingest from `data/`.
- Sizing: 8GB / 4 vCPU droplet (~$48-56/mo) = qdrant + both models (~5GB resident) + app. 16GB comfortable / required for local-LLM profile. Latency budget per answer: embed ~0.1s + search ~0.05s + rerank ~1-1.5s + LLM 1-2s -> ~3-4s.
- Privacy: `data/` payloads + `qdrant_data` gitignored (company docs and tickets never hit GitHub); only READMEs + tiny fixtures committed.

## Folder structure

```
chapter_08_QABuddyAI/
  Plan.md                      # this plan (step 0)
  prompt.md                    # existing spec
  data/
    01_selenium_framework/     # git clone (scripts/fetch_repos.sh), gitignored
    02_playwright_framework/   # git clone, gitignored
    03_test_cases/             # testdata.csv / .xlsx  (fixture: ch07 vwo_5000_test_cases.csv)
    04_jira_tickets/           # JSON dumps from MCP/REST pulls
    05_company_docs/           # PDF, MD           (fixture: ch07 PRD_VWO.pdf)
    06_figma_designs/          # Phase 2 placeholder + README
    07_meeting_notes/          # .txt/.md/.vtt transcripts
    08_lucid_charts/           # exported text
    09_prd_srs_brd_frd/        # PDF
    10_jenkins_logs/           # .log/.txt, console output, JUnit XML
    (each folder: README.md stating accepted formats)
  app/
    core/                      # rag_core.py evolved: embed, store, rrf, rerank
    ingestion/                 # loaders + chunkers per source, pipeline.py, cli.py
    server/                    # app.py (Flask), prompts/, static/, templates/
    llm.py                     # OpenAI-compatible client (Groq default / Ollama)
  config.yaml                  # chunk sizes, models, thresholds, retention
  glossary.yaml
  eval/golden_questions.yaml   # ~20 QA questions + expected source hits
  scripts/                     # fetch_repos.sh, ingest.sh, backup.sh, eval.py
  docker-compose.yml  Dockerfile  Caddyfile  .env.example  .gitignore
  docs/                        # architecture.md, deploy-droplet.md, phase2.md
```

## Reuse from ch07 (explicit)

- `chapter_07_RAG/Advance_RAG/rag_core.py`: `embed()` (BGE-M3 dense+sparse), `Store` (Qdrant collection with named vectors, upsert/search), `rrf_fuse(k=60)`, `rerank()` (transformers workaround), `chunk_text()` -> becomes `app/core/`.
- `chapter_07_RAG/Advance_RAG/ingest.py`: CSV/XLSX -> chunk -> embed -> upsert pattern -> source 3 loader.
- `chapter_07_RAG/Advance_RAG/app.py`: Flask + SSE streaming + pipeline orchestration (`rewrite_query -> search -> fuse -> rerank -> generate`) -> `app/server/`.
- Fixtures: `testcase/vwo_5000_test_cases.csv`, `Basic_RAG/data/Product Requirements Document_(PRD)_VWO.com.pdf`.

## JIRA via MCP

Phase 1: you share MCP connection + JQL -> I pull tickets through MCP -> normalized JSON dumps in `data/04_jira_tickets/` -> pipeline ingests. The connector also speaks plain Jira REST (read-only token, same JQL, same JSON schema) because Phase 2 hourly sync must run headless on the droplet; MCP = interactive pulls, REST = cron.

## Phase 1 build order (after approval): LOCAL-FIRST (your call), droplet deploy last

0. Copy this plan to `chapter_08_QABuddyAI/Plan.md`.
1. Scaffold: ALL 10 `data/` folders + per-folder READMEs (you drop data in), `config.yaml`, `.gitignore`, `.env` from ch07 Groq key (`openai/gpt-oss-120b`), fixtures wired.
2. Core: port + refactor ch07 `rag_core.py` into `app/core/`. Qdrant embedded mode locally (zero setup, like ch07); `QDRANT_URL` env switches to server mode on droplet, no code change.
3. Ingestion: loaders + chunkers per source, `qabuddy ingest [--source N]`, idempotent upserts. Verify: fixture ingest, chunk counts per source printed.
4. Retrieval: hybrid + rerank + threshold + citation mapping. Verify: `scripts/eval.py` hit-rate on golden questions.
5. Backend + UI, running locally: Flask API (`/chat` SSE, `/search`, `/ingest`, `/health`, `/stats`), chat UI with filter chips + citation cards. Verify: localhost end-to-end question with citations. <- local version milestone
6. JIRA connector: MCP pull -> JSON -> ingest (REST-ready for Phase 2).
7. Droplet deploy (when you say go): docker-compose (qdrant server + app + Caddy), `docs/deploy-droplet.md` runbook, backup cron.

Each step verified before the next.

## Phase 2 (planned only, NOT built now)

- Hourly sync cron: `git pull` repos + hash-diff re-index (upsert changed, delete removed; stable IDs make this cheap), folder watcher manifest, JIRA JQL `updated >= -1h`, Jenkins API pull. Design doc: `docs/phase2.md`.
- Figma: REST export -> vision-model description of ER diagrams/wireframes -> ingest as docs.
- Optional: QABuddy MCP server (thin wrapper exposing `qa_search` tool) so Copilot/Claude Code in the IDE query the same KB. This is the "Copilot + RAG = 70-80% coverage" row in your table.

## Need from you (with / after approval)

1. JIRA MCP connection + JQL (+ read-only REST token for Phase 2 cron).
2. Real data dropped into `data/` folders (testdata.csv, docs, PRDs, transcripts, Lucid exports, Jenkins logs).
3. ~~LLM~~ CONFIRMED: Groq `openai/gpt-oss-120b` via `.env`.
4. Droplet confirm at deploy step: 8GB/4vCPU default.
5. Your rough architecture diagram (I reconcile plan against it).
6. Optional: 10-20 term glossary for `glossary.yaml`.
