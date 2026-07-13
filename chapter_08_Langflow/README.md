# Chapter 08 — Langflow

## Overview

This project contains my local Langflow setup for the AI 3x Blueprint course, including a **RAG-powered QA Knowledge Assistant** that answers questions about eCommerce test cases using a chat UI.

The environment is isolated using a Python Virtual Environment (venv) with Python 3.12.13.

---

# Project Structure

```text
chapter_08_Langflow/
│
├── .venv/                       # Python Virtual Environment
│
├── .vscode/
│   └── settings.json            # VS Code interpreter settings
│
├── src/
│   ├── workflow/                # Exported Langflow JSON workflows
│   │   └── AI Test Case Assistant – RAG-Powered QA Knowledge.json
│   │
│   ├── rag_explorer/            # RAG Explorer backend
│   │   ├── .env                 # Config (Langflow URL, flow ID, API key)
│   │   ├── langflow_client.py   # Langflow API client
│   │   ├── main.py              # FastAPI server
│   │   └── ui/
│   │       └── index.html       # Chat UI
│   │
│   └── testdata/
│       └── ecommerce_testcases.csv
│
├── RAG-QA-TestCase-Pipeline/
│   └── prompt/
│       └── prompt.md
│
├── chroma_db/                   # Vector store (auto-generated)
│
├── langflow.env                 # Langflow auth bypass config
├── run_rag_explorer.py          # Entry point for RAG Explorer
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Software Used

| Software | Version |
|----------|----------|
| Python | 3.12.13 |
| Langflow | 1.10.2 |
| FastAPI | 0.139.0 |
| Uvicorn | 0.51.0 |
| httpx | 0.28.1 |
| VS Code | Latest |
| Windows | 11 |

---

# Initial Project Setup

## Step 1

Open VS Code.

Open the project folder.

```
chapter_08_Langflow
```

---

## Step 2

Create Virtual Environment

```powershell
uv venv --python 3.12 .venv
```

---

## Step 3

Activate Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

Verify

```powershell
python --version
```

Expected

```
Python 3.12.13
```

---

## Step 4

Install Langflow

```powershell
python -m pip install langflow
```

---

## Step 5

Verify Installation

```powershell
python -m langflow --version
```

Expected

```
langflow 1.10.2
```

---

# Daily Workflow

Whenever working on this project, follow these steps.

## 1. Open Project

Open `chapter_08_Langflow` inside VS Code.

---

## 2. Open Terminal

Terminal → New Terminal

---

## 3. Activate Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

Expected prompt:

```text
(.venv) PS D:\AI 3x Blueprint\Practice_2\chapter_08_Langflow>
```

---

## 4. Start Langflow

```powershell
python -m langflow run
```

Open `http://127.0.0.1:7860` to see the Langflow UI.

---

## 5. Start RAG Explorer (in a second terminal)

```powershell
.\.venv\Scripts\Activate.ps1
python run_rag_explorer.py
```

Open `http://127.0.0.1:8001` to use the QA chat interface.

---

# RAG Explorer — QA Test Case Assistant

A FastAPI-powered chat UI that connects to your Langflow RAG pipeline and lets you ask questions about your eCommerce test cases using natural language.

**How it works:**

- The Langflow workflow (`AI Test Case Assistant – RAG-Powered QA Knowledge.json`) ingests `ecommerce_testcases.csv` into a Chroma DB vector store using Mistral AI embeddings
- When you ask a question, the RAG pipeline retrieves relevant chunks from Chroma DB, feeds them as context to a Groq LLM, and returns an answer with test case IDs, modules, and priorities
- The RAG Explorer backend bridges the browser UI to Langflow's API

**UI features:**

- Dark glassmorphism chat interface with markdown rendering (tables, bold, lists, code)
- Sidebar with 6 pre-built query suggestions (Login, Payment, Duplicates, Automated, etc.)
- Context panel showing retrieved knowledge chunks
- Real-time Langflow connection status indicator

**API endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the chat UI |
| `/api/health` | GET | Langflow connection status |
| `/api/debug` | GET | Active config (URL, flow ID, API key status) |
| `/api/query` | POST | Send a question to the RAG pipeline |

---

# Stopping Services

Press `CTRL + C` in each terminal window.

---

# Exporting a Flow

Inside Langflow

Flows

↓

Open Flow

↓

Export

↓

Save JSON inside

```
flows/
```

Example

```
flows/
    customer-support-agent.json
    qa-agent.json
    rag-pipeline.json
```

---

# Folder Usage

| Folder | Purpose |
|--------|---------|
| `src/workflow/` | Exported Langflow JSON workflows |
| `src/rag_explorer/` | RAG Explorer backend (FastAPI + UI) |
| `src/testdata/` | CSV, PDF, JSON files used by workflows |
| `RAG-QA-TestCase-Pipeline/prompt/` | Prompt templates for the RAG pipeline |
| `chroma_db/` | Local Chroma vector store files (auto-generated, gitignored) |

---

# Updating Dependencies

To update Langflow

```powershell
python -m pip install --upgrade langflow
```

---

# Generating requirements.txt

Whenever new packages are installed

```powershell
python -m pip freeze > requirements.txt
```

---

# Installing Dependencies on Another Machine

Create Virtual Environment

```powershell
python -m venv .venv
```

Activate

```powershell
.\.venv\Scripts\Activate.ps1
```

Install packages

```powershell
python -m pip install -r requirements.txt
```

---

# Useful Commands

Activate Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

Deactivate Virtual Environment

```powershell
deactivate
```

Check Python Version

```powershell
python --version
```

Check Pip Version

```powershell
python -m pip --version
```

Check Installed Packages

```powershell
python -m pip list
```

Check Langflow Version

```powershell
python -m langflow --version
```

Run Langflow

```powershell
python -m langflow run
```

Generate requirements.txt

```powershell
python -m pip freeze > requirements.txt
```

---

# Notes

- Always use Python 3.12 for Langflow.
- Always activate the virtual environment before running Langflow.
- Keep exported flows inside `src/workflow/`.
- Use `requirements.txt` to recreate the environment on another machine.
- Do not commit `.venv/`, `chroma_db/`, or `.env` files to Git.

------------------------------------------------------------------
# Understanding requirements.txt

## What is requirements.txt?

`requirements.txt` is a file that stores all the Python packages and their exact versions used by this project.

Instead of manually installing each package one by one, Python can recreate the entire environment using this file.

For example:

```txt
langflow==1.10.2
fastapi==0.116.1
langchain==0.3.27
uvicorn==0.35.0
...
```

---

## Why is it important?

Imagine the following situations:

- You buy a new laptop.
- You reinstall Windows.
- You clone this project from GitHub.
- A teammate wants to run this project.

Instead of installing packages manually, simply run:

```powershell
python -m pip install -r requirements.txt
```

Python will automatically install every required package with the correct versions.

---

## How to Generate requirements.txt

Whenever you install a new package or update project dependencies, regenerate the file using:

```powershell
python -m pip freeze > requirements.txt
```

This command scans the current virtual environment and saves every installed package and its version into `requirements.txt`.

---

## When Should I Run This?

Run this command whenever:

- A new package is installed.
- Existing packages are upgraded.
- Before pushing the project to GitHub.
- Before sharing the project with others.

Keeping `requirements.txt` updated ensures anyone can recreate the same development environment.

---

## Installing Packages from requirements.txt

After cloning the project:

Create a virtual environment.

Activate it.

Then run:

```powershell
python -m pip install -r requirements.txt
```

This recreates the complete Python environment automatically.