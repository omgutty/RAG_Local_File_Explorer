# Deploy QABuddy.ai to a VPS (step by step)

Works on any Ubuntu VPS: DigitalOcean droplet, Hetzner, Linode, AWS Lightsail.
Target size: **8GB RAM / 4 vCPU** (16GB if you later run a local LLM).
Everything runs in Docker via `docker-compose.yml`: Qdrant (vector DB) + QABuddy app + Caddy (HTTPS + password).

---

## Step 1: Create the VPS

1. Create an Ubuntu 24.04 server, 8GB RAM / 4 vCPU (~$48/mo on DigitalOcean).
2. Add your SSH key during creation.
3. Note the public IP (call it `YOUR_IP`).

## Step 2: (Optional but recommended) Point a domain

1. In your DNS, add an `A` record: `qabuddy.yourcompany.com -> YOUR_IP`.
2. No domain? You can use `http://YOUR_IP` (skip TLS, see Step 6 note).

## Step 3: Basic server setup

```bash
ssh root@YOUR_IP
apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2 git ufw

# firewall: SSH + web only (app port 5080 stays internal)
ufw allow 22 && ufw allow 80 && ufw allow 443
ufw --force enable

# non-root user
adduser qabuddy
usermod -aG docker qabuddy
su - qabuddy
```

## Step 4: Get the code

```bash
git clone https://github.com/<your-account>/AITesterBlueprint3x.git
cd AITesterBlueprint3x/chapter_08_QABuddyAI
```

## Step 5: Configure secrets

```bash
cp .env.example .env
nano .env
```

Set at minimum:

```
GROQ_API_KEY=gsk_...          # the LLM brain (openai/gpt-oss-120b)
# JIRA_* vars if you want REST ticket pulls on the server
```

Do NOT set `QDRANT_URL` in `.env`; docker-compose injects `http://qdrant:6333` automatically.

## Step 6: Set the domain + password (Caddy)

```bash
# generate a password hash
docker run --rm caddy caddy hash-password --plaintext 'your-strong-pass'
nano Caddyfile
```

- Replace `qabuddy.example.com` with your domain.
- Replace the hash after `qa` with the generated one (login user is `qa`).
- **IP-only (no domain):** change the first line of `Caddyfile` to `:80 {` and keep the rest. No TLS, use only inside a trusted network/VPN.

## Step 7: Upload your data

From your laptop:

```bash
rsync -av chapter_08_QABuddyAI/data/ qabuddy@YOUR_IP:~/AITesterBlueprint3x/chapter_08_QABuddyAI/data/
```

Or drop files per source later into `data/01..10_*/` on the server.
The two framework repos can be cloned on the server directly:

```bash
./scripts/fetch_repos.sh
```

## Step 8: Build and start (24x7)

```bash
docker compose up -d --build
docker compose ps        # all three services: qdrant, app, caddy -> healthy
```

All services restart automatically on crash and on server reboot
(`restart: unless-stopped`).

## Step 9: First index

```bash
docker compose exec app python -m app.ingestion.cli ingest --all
docker compose exec app python -m app.ingestion.cli stats
docker compose exec app python scripts/eval.py     # retrieval hit-rate check
```

First run downloads bge-m3 + reranker (~4.6GB) into the `hf_cache` volume; later runs reuse it. Re-ingest only re-embeds changed files.

## Step 10: Verify

```bash
docker compose exec app curl -s localhost:5080/api/health
```

Open `https://qabuddy.yourcompany.com` (or `http://YOUR_IP`), log in with `qa` + your password, ask:
"Why is the checkout coupon test flaky?" -> expect a cited answer.

## Step 11: Nightly backups

```bash
crontab -e
# add:
0 3 * * * cd ~/AITesterBlueprint3x/chapter_08_QABuddyAI && docker compose exec -T app bash scripts/backup.sh >> backups/cron.log 2>&1
```

Recovery = restore the Qdrant volume/snapshot, or simply re-ingest from `data/` (the folders are the source of truth).

## Step 12: Updates

```bash
git pull
docker compose up -d --build              # new code
docker compose exec app python -m app.ingestion.cli ingest --all   # new data
```

## (Phase 2 preview) Hourly auto-ingest

```bash
0 * * * * cd ~/AITesterBlueprint3x/chapter_08_QABuddyAI && ./scripts/fetch_repos.sh && docker compose exec -T app python scripts/jira_fetch.py && docker compose exec -T app python -m app.ingestion.cli ingest --all
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `docker compose ps` shows app unhealthy | `docker compose logs app`; usually missing `GROQ_API_KEY` |
| Answers say "LLM 401/403" | wrong/expired Groq key in `.env`, then `docker compose up -d` |
| A source shows 0 chunks in stats | files not in the right `data/NN_*/` folder, or wrong extension (see each folder's README) |
| Browser cannot reach the site | DNS not propagated yet, or ufw blocked 80/443 |
| Slow first answer (~15-20s) | one-time model warm-up after a restart; later answers ~3-5s |
| Need to wipe and re-index | `docker compose exec app python -m app.ingestion.cli reset --yes && ... ingest --all` |
