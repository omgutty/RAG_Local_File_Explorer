# QABuddy.ai data sources

Drop Phase 1 data into these folders; `qabuddy ingest` picks everything up.
Folder contents are gitignored (except READMEs and `sample_*` demo files), so
company data never reaches GitHub.

| # | Folder | Put here | Chunking |
|---|--------|----------|----------|
| 01 | `01_selenium_framework/` | auto: `scripts/fetch_repos.sh` clones the repo | 1 method/class per chunk + line numbers |
| 02 | `02_playwright_framework/` | auto: `scripts/fetch_repos.sh` | same, per function/test block |
| 03 | `03_test_cases/` | `.csv` / `.xlsx` test cases | 1 row = 1 chunk, id cited |
| 04 | `04_jira_tickets/` | JSON dumps (MCP pull or `scripts/jira_fetch.py`) | 1 ticket = 1 chunk, key cited |
| 05 | `05_company_docs/` | `.pdf` / `.md` | heading-aware, ~512 tok, 15% overlap |
| 06 | `06_figma_designs/` | Phase 2 (exports) | not ingested yet |
| 07 | `07_meeting_notes/` | `.txt` / `.md` / `.vtt` transcripts | speaker-turn windows |
| 08 | `08_lucid_charts/` | text exports | as docs |
| 09 | `09_prd_srs_brd_frd/` | `.pdf` | as docs, page cited |
| 10 | `10_jenkins_logs/` | `.log` / console text / JUnit `.xml` | failure blocks + build summary |
