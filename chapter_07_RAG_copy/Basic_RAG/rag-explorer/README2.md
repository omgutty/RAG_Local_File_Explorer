# 🚀 RAG Explorer

A hands-on demonstration of a **Retrieval-Augmented Generation (RAG)** pipeline built using **React, Express, Ollama, ChromaDB, and Groq**.

The application allows you to ingest PDF documents, generate embeddings using a local embedding model, store vectors in ChromaDB, retrieve the most relevant chunks, and generate grounded answers using Groq.

---

# 📖 RAG Pipeline

```
                 PDF
                  │
                  ▼
          Extract Text
                  │
                  ▼
          Split into Chunks
                  │
                  ▼
    Generate Embeddings (Ollama)
                  │
                  ▼
     Store Vectors (ChromaDB)
                  │
                  ▼
        User asks a Question
                  │
                  ▼
      Embed User Question
                  │
                  ▼
     Semantic Search (Top-K)
                  │
                  ▼
        Send Context to Groq
                  │
                  ▼
          Grounded Answer
```

---

# ✨ Features

- 📄 PDF document ingestion
- ✂️ Intelligent text chunking
- 🧠 Local embeddings using Ollama (`nomic-embed-text`)
- 🗂️ Local vector database using ChromaDB
- 🔍 Semantic similarity search
- 🤖 Answer generation using Groq (`openai/gpt-oss-120b`)
- 📊 Displays:
  - Number of pages
  - Number of chunks
  - Embedding dimensions
  - Sample embedding vector
  - Retrieved chunks
  - Similarity scores
  - Final prompt sent to the LLM

---

# 🏗️ Architecture

```
Browser (React + Vite :5175)
        │
        │  /api/*
        ▼
Express Backend (:8787)
        │
        ├──────── PDF Parser
        │
        ├──────── Chunk Generator
        │
        ├──────── Ollama
        │           │
        │           ▼
        │     nomic-embed-text
        │
        ├──────── ChromaDB
        │
        └──────── Groq API
```

---

# 📦 Prerequisites

Install the following before running the project.

## 1. Node.js

Download:

https://nodejs.org/

Verify:

```bash
node -v
npm -v
```

---

## 2. Python 3.10+

Download:

https://www.python.org/downloads/

Verify:

```bash
python --version
```

---

## 3. Ollama

Download:

https://ollama.com/download

Verify:

```bash
ollama --version
```

---

## 4. Groq API Key

Create a free account and obtain an API Key.

https://console.groq.com/keys

---

# ⚙️ First-Time Setup

## Step 1 — Clone the Repository

```bash
git clone <repository-url>
```

Navigate to the project:

```bash
cd Basic_RAG/rag-explorer
```

---

## Step 2 — Install Node Packages

```bash
npm install
```

---

## Step 3 — Create a Python Virtual Environment

Windows:

```powershell
python -m venv .venv
```

---

## Step 4 — Activate the Virtual Environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate
```

Your terminal should look like:

```text
(.venv) PS D:\...\rag-explorer>
```

---

## Step 5 — Install ChromaDB

Inside the activated virtual environment:

```powershell
python -m pip install chromadb
```

Verify:

```powershell
chroma --help
```

If `chroma` is not recognized, add your Python Scripts folder to the Windows PATH.

---

## Step 6 — Install Ollama Embedding Model

Pull the embedding model:

```powershell
ollama pull nomic-embed-text
```

Verify:

```powershell
ollama list
```

Expected:

```
nomic-embed-text
```

---

## Step 7 — Configure Environment Variables

Copy:

```bash
cp .env.example .env
```

Update:

```env
GROQ_API_KEY=your_groq_api_key
```

The remaining values can be left as default.

Example:

```env
GROQ_MODEL=openai/gpt-oss-120b

OLLAMA_URL=http://localhost:11434
EMBED_MODEL=nomic-embed-text

CHROMA_URL=http://localhost:8000
CHROMA_COLLECTION=rag_basic

DATA_DIR=../data

CHUNK_SIZE=1200
CHUNK_OVERLAP=200

TOP_K=3

PORT=8787
```

---

## Step 8 — Add PDF Documents

Place your PDFs inside:

```
Basic_RAG/
│
├── data/
│      ProductRequirementsDocument.pdf
```

or update `DATA_DIR` inside `.env`.

---

# ▶️ Running the Application

## Every Time You Start the Project

### 1. Open PowerShell

Navigate to the project.

```powershell
cd Basic_RAG/rag-explorer
```

---

### 2. Activate the Virtual Environment

```powershell
.\.venv\Scripts\Activate
```

---

### 3. Start the Application

```powershell
npm run dev
```

This command starts:

- ChromaDB
- Express Backend
- React UI

---

### 4. Open the UI

```
http://localhost:5175
```

---

### 5. Click **Ingest PDF**

The application will

- Read every PDF
- Extract text
- Split into chunks
- Generate embeddings
- Store vectors in ChromaDB

---

### 6. Ask Questions

Example:

- What is the goal of this PRD?
- Who are the target users?
- What are the success metrics?
- Summarize the document.

---

# 🔄 Daily Workflow

After the initial setup, you only need these commands:

```powershell
cd Basic_RAG/rag-explorer
```

```powershell
.\.venv\Scripts\Activate
```

```powershell
npm run dev
```

Open

```
http://localhost:5175
```

That's it.

---

# 📁 Project Structure

```
Basic_RAG
│
├── data
│      *.pdf
│
├── rag-explorer
│      │
│      ├── server
│      │      chunk.js
│      │      chroma.js
│      │      embed.js
│      │      groq.js
│      │
│      ├── src
│      │
│      ├── .env
│      ├── package.json
│      └── README.md
```

---

# ⚙️ Configuration

| Variable | Description |
|-----------|-------------|
| GROQ_API_KEY | Groq API Key |
| GROQ_MODEL | LLM Model |
| OLLAMA_URL | Ollama URL |
| EMBED_MODEL | Embedding Model |
| CHROMA_URL | Chroma Server URL |
| CHROMA_COLLECTION | Collection Name |
| DATA_DIR | PDF Folder |
| CHUNK_SIZE | Chunk Size |
| CHUNK_OVERLAP | Chunk Overlap |
| TOP_K | Number of Retrieved Chunks |
| PORT | Backend Port |

---

# 🛠 Troubleshooting

## `'chroma' is not recognized`

Install ChromaDB:

```powershell
python -m pip install chromadb
```

If still not recognized, add Python's **Scripts** folder to your Windows PATH.

---

## `'ollama' is not recognized`

Install Ollama:

https://ollama.com/download

Restart your terminal.

---

## ChromaDB Not Reachable

Verify Chroma starts:

```powershell
chroma run --path ./chroma-data --port 8000
```

or simply:

```powershell
npm run dev
```

---

## Port Already in Use

Terminate Node processes:

```powershell
taskkill /F /IM node.exe
```

Restart:

```powershell
npm run dev
```

---

## Embedding Model Missing

```powershell
ollama pull nomic-embed-text
```

---

## No PDFs Found

Ensure PDFs are placed inside:

```
Basic_RAG/data
```

or update:

```env
DATA_DIR=../data
```

---

## Invalid Groq API Key

Update:

```env
GROQ_API_KEY=your_api_key
```

Restart:

```powershell
npm run dev
```

---

# 🧠 Tech Stack

- React
- Vite
- Express.js
- Node.js
- Ollama
- ChromaDB
- Groq
- PDF-Parse

---

# 📚 Learning Objectives

This project demonstrates:

- Retrieval-Augmented Generation (RAG)
- Document ingestion
- Text chunking
- Embedding generation
- Vector databases
- Semantic search
- Prompt augmentation
- Grounded LLM responses
- Local AI infrastructure with Ollama

---

# 🎉 Result

After completing the setup, you'll have a fully local RAG pipeline capable of:

- Ingesting PDFs
- Creating vector embeddings
- Storing embeddings in ChromaDB
- Performing semantic search
- Generating context-aware answers using Groq

All through a simple React web interface.