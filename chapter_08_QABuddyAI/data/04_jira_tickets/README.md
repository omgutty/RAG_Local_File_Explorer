# Source 04: JIRA tickets

JSON dumps land here, pulled via JIRA MCP (interactive) or
`scripts/jira_fetch.py` (REST + JQL, used by the Phase 2 hourly cron).

Format: `{"tickets": [{key, type, summary, description, status, priority,
labels[], components[], created, updated, url, comments[{author, created, body}]}]}`
See `sample_tickets.json`. Chunking: 1 ticket = 1 chunk (long comment threads
spill into linked chunks). The ticket key is the citation.
