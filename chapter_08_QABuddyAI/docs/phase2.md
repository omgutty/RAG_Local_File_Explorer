# Phase 2 plan (approved design, not built yet)

## 1. Hourly auto-ingestion

Everything is already idempotent (stable uuid5 chunk ids + per-file manifest
diff), so Phase 2 is scheduling, not redesign:

```
# crontab on the droplet
0 * * * *  cd /path/chapter_08_QABuddyAI && ./scripts/fetch_repos.sh \
           && docker compose exec -T app python scripts/jira_fetch.py \
           && docker compose exec -T app python -m app.ingestion.cli ingest --all
```

- Repos: `git pull` then ingest; only files whose chunk signature changed are
  re-embedded, removed files are deleted from Qdrant.
- Test cases / docs / logs: drop-folder watcher = the same manifest diff.
- JIRA: `scripts/jira_fetch.py` with `JIRA_JQL='updated >= "-1h"'` (REST token).
- Jenkins: extend `jira_fetch.py` pattern with a small `jenkins_fetch.py`
  hitting `/job/<name>/lastBuild/consoleText` + JUnit XML API per job.
- Add `ingest --source NN --quiet` output to a log; alert on error stage.

## 2. Figma ingestion (source 06)

- Pull: Figma REST `GET /v1/files/:key` (+ `/images` for PNG exports) with a
  read-only token; walk pages/frames.
- Describe: run each exported frame through a vision model (Claude) with a
  "describe this wireframe/ER diagram for a QA engineer" prompt; keep node
  names, flows, field labels.
- Ingest: resulting markdown goes to `data/06_figma_designs/` and indexes with
  the docs loader (`source_type=figma_designs` already wired in the pipeline).

## 3. QABuddy MCP server (the Copilot multiplier)

Thin MCP wrapper exposing `qa_search(question, sources?) -> cited chunks` over
`/api/search`, so Copilot / Claude Code / Cursor inside the IDE query the same
KB. This is the "Copilot + RAG + JIRA = 70-80% coverage" row in the spec table.

## 4. Quality loop

- Grow `eval/golden_questions.yaml` with real team questions weekly.
- Track hit-rate per source; a dropping source usually means chunking config
  needs tuning in `config.yaml` (no code change).
