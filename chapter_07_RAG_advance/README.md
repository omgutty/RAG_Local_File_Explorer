# Advanced RAG Explorer

https://rag-local-file-explorer-q8q4.vercel.app/

A full-stack **Retrieval-Augmented Generation** system built with Flask, featuring hybrid search, cross-encoder re-ranking, query rewriting, and real-time SSE streaming — no Docker required.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     INGEST PIPELINE                           │
│  CSV/XLSX → Read → Build Docs → Chunk → Embed → Qdrant      │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                     CHAT PIPELINE                             │
│  Query → Rewrite → Embed → Hybrid Search → Rerank → LLM     │
└──────────────────────────────────────────────────────────────┘
```

### Core Modules

| Module | File | Purpose |
|---|---|---|
| **Orchestrator** | `pipeline/orchestrator.py` | SSE-driven pipeline runners (ingest + chat) |
| **Chunker** | `pipeline/chunker.py` | Recursive text splitting (1000 chars, 150 overlap) |
| **Embedder** | `pipeline/embedder.py` | bge-m3: dense (1024-dim) + sparse vectors |
| **Indexer** | `pipeline/indexer.py` | Qdrant embedded client (RocksDB, no Docker) |
| **Retriever** | `pipeline/retriever.py` | Hybrid search + RRF fusion |
| **Reranker** | `pipeline/reranker.py` | bge-reranker-v2-m3 cross-encoder |
| **Rewriter** | `pipeline/rewriter.py` | Query rewriting via GPT-4o-mini (3 variants) |
| **Generator** | `pipeline/generator.py` | LLM answer generation via DeepSeek |
| **Model Loader** | `models/loader.py` | Lazy-loaded model singletons |

### Data Flow

**Ingest:** Upload CSV/XLSX → concat selected text columns per row → recursive chunk → bge-m3 dense + sparse vectors → upsert to Qdrant.

**Chat:** User query → generate 3 rewrites (GPT-4o-mini) → embed all 4 queries (bge-m3) → hybrid dense+sparse search per query → RRF fuse → cross-encoder rerank (bge-reranker) → DeepSeek generates answer with citations.

### Tech Stack

- **Language:** Python 3.12
- **Web:** Flask 3.x + Jinja2 + vanilla JS
- **Embedding:** BAAI/bge-m3 (FlagEmbedding)
- **Reranking:** BAAI/bge-reranker-v2-m3
- **Vector DB:** Qdrant embedded (RocksDB, no Docker)
- **LLM:** Openrouter API (DeepSeek + GPT-4o-mini)
- **Real-time:** Server-Sent Events (SSE)
- **Frontend:** Claude-inspired theme (cream + coral)

## Getting Started

### 1. Prerequisites

- Python 3.12+
- An [Openrouter API key](https://openrouter.ai/)

### 2. Setup

```bash
# Navigate to the project
cd "D:\AI 3x Blueprint\Practice_2\chapter_07_RAG_advance"

# Create virtual environment
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Key

Create a `.env` file in the project root (or ensure it exists):

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 4. Generate Test Data (optional)

5000 VWO test cases are pre-generated in `testcase/vwo_test_cases_5000.csv`. To regenerate:

```bash
python testcase/generate_test_cases.py
```

### 5. Start the App

```bash
python app.py
```

The server starts on **http://localhost:5050**

### 6. Usage

1. Open **http://localhost:5050** in your browser
2. Upload a CSV or XLSX file, select text columns + metadata columns
3. Click **Ingest** — watch real-time SSE progress
4. Navigate to **Chat** — ask questions, get grounded answers with chunk citations
5. Browse **Chunks** — paginated view of all indexed chunks

## Configuration

All tunables in `config.py`:

| Parameter | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | 1000 | Chars per chunk |
| `CHUNK_OVERLAP` | 150 | Overlap between chunks |
| `TOP_N_HYBRID` | 20 | Candidates per dense/sparse search |
| `TOP_K_RERANK` | 4 | Final chunks to LLM |
| `RRF_K` | 60 | RRF smoothing constant |
| `REWRITE_ENABLED` | True | Query rewriting toggle |
| `INGEST_BATCH` | 16 | Embedding batch size |
| `PORT` | 5050 | Flask server port |

## Project Structure

```
chapter_07_RAG_advance/
├── app.py                      # Flask entry point
├── config.py                   # Configuration
├── requirements.txt            # Dependencies
├── .env                        # API keys
├── pipeline/                   # Core RAG pipeline modules
├── models/                     # Lazy model loaders
├── templates/                  # Jinja2 HTML templates
├── static/                     # CSS + JS
├── data/                       # Uploads + Qdrant storage
├── testcase/                   # Test case generation
├── explainer/                  # Animated RAG explainer page
└── test_rag_explorer.py        # Playwright E2E test
```
