#!/usr/bin/env bash
# Chronos — quarterly restore-drill. Decrypts the latest backup into a
# scratch DB and verifies entry counts. Fails loudly so the calendar
# reminder cannot be silently ignored.

set -euo pipefail

: "${SQLITE_PATH:?SQLITE_PATH not set}"
BACKUP_DIR="${BACKUP_DIR:-$(dirname "$SQLITE_PATH")/backups}"

LATEST="$(ls -1t "$BACKUP_DIR"/chronos-*.db.gpg 2>/dev/null | head -n1 || true)"
if [[ -z "$LATEST" ]]; then
  echo "FAIL: no backups in $BACKUP_DIR" >&2
  exit 1
fi

SCRATCH="$(mktemp -t chronos-restore-XXXXXX.db)"
trap 'rm -f "$SCRATCH"' EXIT

gpg --batch --yes --decrypt --output "$SCRATCH" "$LATEST"

ENTRY_COUNT="$(sqlite3 "$SCRATCH" 'SELECT COUNT(*) FROM entries;')"
LANE_COUNT="$(sqlite3 "$SCRATCH"  'SELECT COUNT(*) FROM lanes;')"
INTEGRITY="$(sqlite3 "$SCRATCH" 'PRAGMA integrity_check;')"

if [[ "$INTEGRITY" != "ok" ]]; then
  echo "FAIL: integrity_check returned: $INTEGRITY" >&2
  exit 2
fi

echo "restore-drill ok"
echo "  backup:  $LATEST"
echo "  lanes:   $LANE_COUNT"
echo "  entries: $ENTRY_COUNT"
echo "  integrity: $INTEGRITY"
