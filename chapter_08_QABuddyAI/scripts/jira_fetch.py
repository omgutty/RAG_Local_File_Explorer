#!/usr/bin/env python3
"""Pull JIRA tickets via REST + JQL into data/04_jira_tickets/jira_export.json.

Phase 1: run manually (or let Claude pull via the JIRA MCP into the same JSON
schema). Phase 2: the hourly cron runs this with JIRA_JQL='updated >= "-1h"'.

Env (.env): JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_JQL
    .venv/bin/python scripts/jira_fetch.py [--jql '...'] [--max 2000]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import config as C  # noqa: E402  (loads .env)


def adf_to_text(node):
    """Flatten Atlassian Document Format to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(n) for n in node)
    if isinstance(node, dict):
        t = node.get("type")
        text = node.get("text", "")
        inner = adf_to_text(node.get("content", []))
        if t in ("paragraph", "heading", "listItem", "codeBlock", "blockquote"):
            return inner + "\n"
        return text + inner
    return ""


def normalize(issue):
    f = issue.get("fields", {})
    desc = f.get("description")
    comments = []
    for c in (f.get("comment") or {}).get("comments", []):
        comments.append({
            "author": ((c.get("author") or {}).get("displayName")),
            "created": (c.get("created") or "")[:10],
            "body": adf_to_text(c.get("body")).strip(),
        })
    return {
        "key": issue.get("key"),
        "type": (f.get("issuetype") or {}).get("name"),
        "summary": f.get("summary"),
        "description": adf_to_text(desc).strip() if not isinstance(desc, str) else desc,
        "status": (f.get("status") or {}).get("name"),
        "priority": (f.get("priority") or {}).get("name"),
        "labels": f.get("labels") or [],
        "components": [c.get("name") for c in f.get("components") or []],
        "created": (f.get("created") or "")[:10],
        "updated": (f.get("updated") or "")[:10],
        "url": f"{os.getenv('JIRA_BASE_URL', '').rstrip('/')}/browse/{issue.get('key')}",
        "comments": comments,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jql", default=os.getenv("JIRA_JQL", ""))
    ap.add_argument("--max", type=int, default=5000)
    ap.add_argument("--out", default=str(C.DATA_DIR / "04_jira_tickets" / "jira_export.json"))
    args = ap.parse_args()

    base = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    if not (base and email and token and args.jql):
        print("Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_JQL in .env (or pass --jql).")
        return 1

    fields = "summary,description,status,priority,labels,components,created,updated,comment,issuetype"
    tickets, token_next, fetched = [], None, 0
    while fetched < args.max:
        params = {"jql": args.jql, "maxResults": min(100, args.max - fetched), "fields": fields}
        if token_next:
            params["nextPageToken"] = token_next
        r = requests.get(f"{base}/rest/api/3/search/jql", params=params,
                         auth=(email, token), timeout=60)
        if r.status_code == 404:  # older API fallback
            params.pop("nextPageToken", None)
            params["startAt"] = fetched
            r = requests.get(f"{base}/rest/api/3/search", params=params,
                             auth=(email, token), timeout=60)
        r.raise_for_status()
        data = r.json()
        issues = data.get("issues", [])
        if not issues:
            break
        tickets.extend(normalize(i) for i in issues)
        fetched += len(issues)
        token_next = data.get("nextPageToken")
        print(f"fetched {fetched}...", end="\r")
        if not token_next and data.get("total") is not None and fetched >= data["total"]:
            break
        if not token_next and "nextPageToken" not in data and len(issues) < 100:
            break

    out = Path(args.out)
    out.write_text(json.dumps({"tickets": tickets}, indent=1, ensure_ascii=False))
    print(f"\nwrote {len(tickets)} tickets -> {out}")
    print("now run: .venv/bin/python -m app.ingestion.cli ingest --source 04")
    return 0


if __name__ == "__main__":
    sys.exit(main())
