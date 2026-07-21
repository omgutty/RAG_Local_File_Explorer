"""Query rewriting — generates alternate phrasings via Openrouter."""

import logging
import json

import config

logger = logging.getLogger(__name__)


def rewrite_query(user_query: str) -> list[str]:
    """Generate 3 alternative phrasings of the user query.

    Returns a list of up to 3 rewritten strings.
    If the API call fails, returns an empty list (original query alone is used).
    """
    if not config.REWRITE_ENABLED:
        return []

    from openai import OpenAI

    client = OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE,
    )

    try:
        response = client.chat.completions.create(
            model=config.REWRITE_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a search query rewriter for a test-case knowledge base. "
                        "Given a user's question about VWO A/B test cases, generate "
                        "3 concise alternative phrasings that capture the same intent "
                        "but vary vocabulary and structure. "
                        "Return each on its own line. Do NOT number them. "
                        "Do NOT add explanations."
                    ),
                },
                {"role": "user", "content": user_query},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        content = response.choices[0].message.content.strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        rewrites = [line for line in lines if not line[0].isdigit()][:3]
        logger.info("Query rewrites: %s", rewrites)
        return rewrites
    except Exception as e:
        logger.warning("Query rewriting failed: %s", e)
        return []
