"""Answer generation via Openrouter — Answer mode or Generate mode."""

import logging
from typing import Any

from qdrant_client.models import ScoredPoint

import config

logger = logging.getLogger(__name__)


def detect_mode(user_query: str) -> str:
    """Auto-detect if this is an Answer or Generate request."""
    gen_keywords = [
        "create", "generate", "write", "new test case", "draft",
        "jira", "vwo-", "make a test", "test case for", "compose",
        "build a test", "create test case",
    ]
    q = user_query.lower()
    for kw in gen_keywords:
        if kw in q:
            return "generate"
    return "answer"


def _build_system_prompt(mode: str) -> str:
    if mode == "generate":
        return (
            "You are a senior QA engineer creating structured test cases for VWO "
            "(Visual Website Optimizer) A/B testing experiments.\n\n"
            "Using the retrieved similar test cases as templates, generate a new "
            "test case in this format:\n"
            "---\n"
            "**Title:** <descriptive title>\n"
            "**Preconditions:** <what must be true before testing>\n"
            "**Steps:**\n"
            "1. <step 1>\n"
            "2. <step 2>\n"
            "**Expected Results:** <what should happen>\n"
            "**Priority:** <P0/P1/P2/P3>\n"
            "**Tags:** <relevant tags>\n"
            "---\n\n"
            "Base your response on the retrieved test case patterns. "
            "Cite similar cases as [Chunk N] where applicable."
        )
    return (
        "You are a QA knowledge expert specializing in VWO (Visual Website Optimizer) "
        "A/B testing experiments.\n\n"
        "Answer the question based strictly on the provided test case contexts. "
        "If the contexts don't contain enough information, say so clearly.\n\n"
        "Cite your sources using [Chunk N] notation matching the chunk IDs provided.\n"
        "Be concise but thorough."
    )


def generate(user_query: str,
             reranked: list[ScoredPoint],
             mode: str = None,
             history: list[dict] = None) -> dict[str, Any]:
    """Generate a grounded answer or structured test case.

    Args:
        user_query: The user's question / request.
        reranked: Top re-ranked chunks.
        mode: 'answer' or 'generate'. Auto-detected if None.
        history: Previous chat messages [{"role": "...", "content": "..."}].

    Returns dict::
        {"role": "assistant", "content": "...", "citations": [chunk_ids]}
    """
    mode = mode or detect_mode(user_query)
    history = history or []

    # Build context from reranked chunks
    context_parts = []
    citations = []
    for i, point in enumerate(reranked):
        text = point.payload.get("text", "")
        chunk_label = point.payload.get("_chunk_id", f"Chunk {i}")
        context_parts.append(f"[{chunk_label}] {text}")
        citations.append(chunk_label)
    context_str = "\n\n".join(context_parts)

    if not context_str.strip():
        context_str = "(No relevant test cases found in the knowledge base.)"

    system_prompt = _build_system_prompt(mode)

    # Prepare messages
    messages = list(history)
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {
            "role": "system",
            "content": f"{system_prompt}\n\nRelevant context:\n{context_str}",
        })

    messages.append({"role": "user", "content": user_query})

    from openai import OpenAI

    client = OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE,
    )

    try:
        response = client.chat.completions.create(
            model=config.GENERATE_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        content = response.choices[0].message.content.strip()
        logger.info("Generated %s response (%d chars)", mode, len(content))

        return {
            "role": "assistant",
            "content": content,
            "citations": citations,
            "mode": mode,
        }

    except Exception as e:
        logger.error("Generation failed: %s", e)
        return {
            "role": "assistant",
            "content": f"Sorry, I couldn't generate a response due to an error: {e}",
            "citations": citations,
            "mode": mode,
        }
