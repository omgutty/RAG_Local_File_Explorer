# Droplet deploy runbook (DigitalOcean, 24x7)

Target: 8GB RAM / 4 vCPU droplet (Ubuntu 24.04). 16GB if you later run a local
LLM via Ollama. Everything ships in `docker-compose.yml`: qdrant + app + caddy.

## 1. Provision

```bash
# on the droplet
apt update && apt install -y docker.io docker-compose-v2 git
adduser qabuddy && usermod -aG docker qabuddy && su - qabuddy
git clone <your-repo> && cd AITesterBlueprint3x/chapter_08_QABuddyAI
```

DO cloud firewall: allow 22, 80, 443 only (the app port 5080 stays internal).

## 2. Configure

```bash
cp .env.example .env       # set GROQ_API_KEY; QDRANT_URL is injected by compose
vi Caddyfile               # your domain + basic_auth hash:
docker run --rm caddy caddy hash-password --plaintext 'strong-pass'
```

## 3. Data + first index

```bash
./scripts/fetch_repos.sh
# copy your CSVs / PDFs / logs into data/NN_*/ (scp or rsync)
docker compose up -d --build
docker compose exec app python -m app.ingestion.cli ingest --all
docker compose exec app python scripts/eval.py
```

## 4. Verify

```bash
curl -s localhost:80 -H "Host: yourdomain" | head    # via caddy
docker compose exec app curl -s localhost:5080/api/health
docker compose exec app python -m app.ingestion.cli stats
```

Open https://yourdomain, log in with the basic-auth user, ask a golden question.

## 5. Operate

- Logs: `docker compose logs -f app`
- Backup (cron `0 3 * * *`): `docker compose exec app bash scripts/backup.sh`
  (or snapshot the qdrant volume)
- Update code: `git pull && docker compose up -d --build`
- Re-ingest after dropping new data: `docker compose exec app python -m app.ingestion.cli ingest --all`
  (manifest diff means unchanged files are skipped)

## Sizing notes

bge-m3 + reranker ~5GB resident in the app container. Qdrant a few hundred MB
at this corpus size (20-60k chunks). Answer latency ~3-4s (rerank ~1-1.5s CPU +
Groq 1-2s).
