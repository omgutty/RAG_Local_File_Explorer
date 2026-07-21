# JIRA ingestion: MCP pull or REST

Both paths write the SAME JSON schema into `data/04_jira_tickets/`, and
`ingest --source 04` picks it up. Ticket key becomes the citation.

## Path A: MCP (interactive, Phase 1)

Share the JIRA MCP connection + JQL in a Claude Code session and ask:

> Pull all tickets for JQL `<your JQL>` via the JIRA MCP and save them to
> `chapter_08_QABuddyAI/data/04_jira_tickets/jira_export.json` in the QABuddy
> schema (see below), then run `python -m app.ingestion.cli ingest --source 04`.

## Path B: REST (headless, used by the Phase 2 hourly cron)

```bash
# .env
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=...            # read-only scope is enough
JIRA_JQL=project = VWO ORDER BY updated DESC

.venv/bin/python scripts/jira_fetch.py
.venv/bin/python -m app.ingestion.cli ingest --source 04
```

## Schema

```json
{"tickets": [{
  "key": "VWO-2001", "type": "Bug", "summary": "...", "description": "...",
  "status": "Open", "priority": "P1", "labels": [], "components": [],
  "created": "2026-06-30", "updated": "2026-07-02",
  "url": "https://.../browse/VWO-2001",
  "comments": [{"author": "Priya", "created": "2026-07-01", "body": "..."}]
}]}
```

Chunking: 1 ticket = 1 chunk; long comment threads spill into linked chunks
(`ticket_key` payload keeps them joined). `sample_tickets.json` demos the shape.
