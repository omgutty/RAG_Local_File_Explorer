"""Prompt templates per mode + glossary injection + citation labeling."""
from . import config as C

BASE_RULES = (
    "You are QABuddy.ai, the internal assistant for the QA team. You answer using ONLY the "
    "retrieved context chunks below. Every claim must cite its chunk as [n] (e.g. [1], [2]). "
    "Use exact identifiers from the context (file paths, line numbers, ticket keys, test case ids). "
    "If the context does not contain the answer, say what is missing instead of guessing."
)

MODE_SYS = {
    "answer": "Answer concisely and practically, like a senior QA engineer helping a teammate.",
    "generate": (
        "You are a senior SDET. Using the retrieved test cases, requirements and code as "
        "templates, produce well-structured NEW test case(s) for the request. Format each with "
        "exactly these headers: Title, Preconditions, Steps (numbered), Expected Result, "
        "Priority, Tags. Ground every design choice in the retrieved chunks and cite them [n]."),
    "review": (
        "You are reviewing test coverage. Compare the retrieved test cases against the retrieved "
        "requirements/PRD sections and code. List: covered areas, GAPS (missing test cases with "
        "a one-line suggested case each), and risky assumptions. Cite evidence [n] for every gap."),
    "rca": (
        "You are doing root cause analysis of a test failure. From the retrieved logs, tickets, "
        "code and test cases: state the most probable root cause, the evidence chain (cite [n] "
        "for each step), whether it looks like a product bug / test bug / flaky infra, and the "
        "concrete next fix. If evidence is thin, say what log or data is missing."),
}


def _glossary_block():
    if not C.GLOSSARY:
        return ""
    lines = "\n".join(f"- {k}: {v}" for k, v in C.GLOSSARY.items())
    return f"\n\nCompany terminology:\n{lines}"


def chunk_label(payload):
    """Short human ref used inside the prompt so the model cites naturally."""
    st = payload.get("source_type", "")
    if st in ("selenium_framework", "playwright_framework"):
        loc = f"{payload.get('repo', '')}/{payload.get('path', '')}"
        if payload.get("line_start"):
            loc += f":{payload['line_start']}-{payload['line_end']}"
        return loc
    if st == "test_cases":
        return f"test case {payload.get('tc_id', '?')}"
    if st == "jira_tickets":
        return f"JIRA {payload.get('ticket_key', '?')}"
    if st == "jenkins_logs":
        b = payload.get("build_id")
        return f"Jenkins build #{b}" if b else f"Jenkins {payload.get('path', '')}"
    if st == "meeting_notes":
        return f"meeting {payload.get('title', payload.get('path', ''))}"
    if st in ("company_docs", "prd_docs", "lucid_charts"):
        ref = payload.get("title") or payload.get("path", "")
        if payload.get("page"):
            ref += f" p.{payload['page']}"
        return ref
    return payload.get("path", st)


def build_messages(mode, question, chunks, history=None):
    context = "\n\n---\n\n".join(
        f"[{i + 1}] ({chunk_label(c['payload'])})\n{c['payload'].get('text', '')}"
        for i, c in enumerate(chunks))
    system = BASE_RULES + "\n\n" + MODE_SYS.get(mode, MODE_SYS["answer"]) + _glossary_block()
    messages = [{"role": "system", "content": system}]
    for h in (history or [])[-2 * C.cfg("retrieval.history_turns", 3):]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:600]})
    messages.append({"role": "user",
                     "content": f"Context:\n{context}\n\n---\n\nRequest: {question}"})
    return messages
