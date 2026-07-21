"""OpenAI-compatible LLM client. Default: Groq hosting openai/gpt-oss-120b.

Swap providers with two env vars (LLM_BASE_URL, LLM_MODEL); works with Groq,
OpenRouter, OpenAI, or a local Ollama (http://localhost:11434/v1).
"""
import json

import requests

from . import config as C


def _headers():
    if not C.LLM_API_KEY:
        raise RuntimeError("No LLM API key. Set GROQ_API_KEY (or LLM_API_KEY) in .env.")
    return {"Authorization": f"Bearer {C.LLM_API_KEY}", "Content-Type": "application/json"}


def chat(messages, temperature=None, max_tokens=None):
    r = requests.post(
        f"{C.LLM_BASE_URL}/chat/completions",
        headers=_headers(),
        json={"model": C.LLM_MODEL, "messages": messages,
              "temperature": C.cfg("llm.temperature", 0.2) if temperature is None else temperature,
              "max_tokens": max_tokens or C.cfg("llm.max_tokens", 1400)},
        timeout=90,
    )
    if not r.ok:
        raise RuntimeError(f"LLM {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"].strip()


def chat_stream(messages, temperature=None, max_tokens=None):
    """Yield content deltas as they stream from the provider."""
    r = requests.post(
        f"{C.LLM_BASE_URL}/chat/completions",
        headers=_headers(),
        json={"model": C.LLM_MODEL, "messages": messages, "stream": True,
              "temperature": C.cfg("llm.temperature", 0.2) if temperature is None else temperature,
              "max_tokens": max_tokens or C.cfg("llm.max_tokens", 1400)},
        timeout=120, stream=True,
    )
    if not r.ok:
        raise RuntimeError(f"LLM {r.status_code}: {r.text[:300]}")
    for raw in r.iter_lines():
        # decode utf-8 ourselves: requests falls back to latin-1 when the SSE
        # content-type carries no charset, mangling quotes/dashes
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            delta = json.loads(data)["choices"][0]["delta"].get("content")
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
        if delta:
            yield delta
