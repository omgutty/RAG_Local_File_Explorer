#!/usr/bin/env bash
# Nightly backup: Qdrant snapshot (server mode) or a tar of qdrant_data (embedded),
# plus the ingest manifest. Add to cron:  0 3 * * *  /path/to/scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
STAMP=$(date +%Y%m%d_%H%M)

if [ -n "${QDRANT_URL:-}" ]; then
  COLLECTION="${QDRANT_COLLECTION:-qabuddy_kb}"
  curl -s -X POST "${QDRANT_URL}/collections/${COLLECTION}/snapshots" -o "backups/snapshot_${STAMP}.json"
  echo "qdrant snapshot requested -> backups/snapshot_${STAMP}.json"
else
  tar czf "backups/qdrant_data_${STAMP}.tgz" qdrant_data 2>/dev/null || true
  echo "embedded store archived -> backups/qdrant_data_${STAMP}.tgz"
fi
cp -f data/.ingest_manifest.json "backups/manifest_${STAMP}.json" 2>/dev/null || true
ls -t backups | tail -n +15 | while read -r f; do rm -f "backups/$f"; done  # keep last ~14
echo "backup done"
