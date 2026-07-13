"""Langflow API client — direct HTTP calls for maximum reliability."""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path)

LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://127.0.0.1:7861")
LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY", None)
FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "f9e91933-6612-49e0-bd09-96023a3ba2f5")


async def health_check() -> bool:
    """Check if Langflow is reachable."""
    paths = ["/health", "/api/v1/health", "/docs"]
    import asyncio

    async def _try(path: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2, verify=False) as c:
                r = await c.get(f"{LANGFLOW_BASE_URL}{path}")
                return r.status_code < 500
        except Exception:
            return False

    results = await asyncio.gather(*[_try(p) for p in paths])
    return any(results)


async def query_flow(
    question: str,
    flow_id: str | None = None,
) -> dict[str, Any]:
    """Send a question to Langflow and return parsed result."""
    fid = flow_id or FLOW_ID
    url = f"{LANGFLOW_BASE_URL}/api/v1/run/{fid}"

    headers = {"Content-Type": "application/json"}
    if LANGFLOW_API_KEY:
        headers["x-api-key"] = LANGFLOW_API_KEY

    payload = {
        "input_value": question,
        "input_type": "chat",
        "output_type": "chat",
    }

    async with httpx.AsyncClient(timeout=180, verify=False) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code == 403:
        raise RuntimeError(
            f"Langflow returned 403 (Forbidden) at {LANGFLOW_BASE_URL}. "
            f"You need to either:\n"
            f"  1. Set LANGFLOW_API_KEY in src/rag_explorer/.env with your Langflow API key\n"
            f"  2. Or restart Langflow with LANGFLOW_SKIP_AUTH_AUTO_LOGIN=True and LANGFLOW_AUTO_LOGIN=True"
        )
    resp.raise_for_status()

    data = resp.json()

    # Extract the answer text from the nested response structure
    try:
        outputs = data["outputs"][0]["outputs"][0]
        answer = outputs["results"]["message"]["text"]
    except (KeyError, IndexError, TypeError):
        # Try messages array as fallback
        try:
            msg = data["outputs"][0]["outputs"][0]["messages"][0]
            answer = msg.get("message", str(data))
        except (KeyError, IndexError, TypeError):
            answer = str(data)

    return {
        "answer": answer,
        "flow_id": fid,
        "session_id": data.get("session_id"),
    }
