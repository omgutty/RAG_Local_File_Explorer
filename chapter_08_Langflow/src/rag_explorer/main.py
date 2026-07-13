"""FastAPI backend for the RAG Explorer — bridges the UI to Langflow."""

import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .langflow_client import (
    FLOW_ID,
    LANGFLOW_API_KEY,
    LANGFLOW_BASE_URL,
    health_check,
    query_flow,
)

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path)


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    flow_id: str | None = None
    session_id: str | None = None


app = FastAPI(title="RAG Explorer — QA Test Case Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    ok = await health_check()
    return {
        "status": "ok",
        "langflow_connected": ok,
        "langflow_url": LANGFLOW_BASE_URL,
    }


@app.get("/api/debug")
async def debug():
    ok = await health_check()
    return {
        "langflow_url": LANGFLOW_BASE_URL,
        "flow_id": FLOW_ID,
        "api_key_set": bool(LANGFLOW_API_KEY),
        "langflow_connected": ok,
        "env_file": _env_path,
        "env_file_exists": os.path.isfile(_env_path),
    }


@app.post("/api/query", response_model=QueryResponse)
async def query(body: QueryRequest):
    try:
        result = await query_flow(question=body.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        detail = (
            f"Langflow returned HTTP {exc.response.status_code} "
            f"at {LANGFLOW_BASE_URL}. Response: {exc.response.text[:300]}"
        )
        raise HTTPException(status_code=502, detail=detail)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return QueryResponse(
        answer=result.get("answer", ""),
        flow_id=result.get("flow_id"),
        session_id=result.get("session_id"),
    )


# Serve SPA
static_dir = os.path.join(os.path.dirname(__file__), "ui")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")
