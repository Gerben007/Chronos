#!/usr/bin/env bash
# Chronos — dev bootstrap. One command to prep a clean checkout.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "▸ creating .env from template if missing"
[[ -f .env ]] || cp .env.example .env

echo "▸ initialising local sqlite (db/chronos.db)"
mkdir -p db
if [[ ! -f db/chronos.db ]]; then
  sqlite3 db/chronos.db < db/migrations/0001_init.sql
  sqlite3 db/chronos.db < db/seed/lanes.sql
fi

echo "▸ installing site deps"
( cd apps/site && npm install )

echo "▸ installing ingest deps (editable, with [dev])"
( cd apps/ingest && python3.11 -m venv .venv && . .venv/bin/activate && \
  pip install --upgrade pip && pip install -e ".[dev]" )

cat <<EOF

ready.
  site:   cd apps/site   && npm run dev
  ingest: cd apps/ingest && . .venv/bin/activate
EOF
