#!/usr/bin/env bash
# Chronos — nightly SQLite backup. gpg-encrypts to BACKUP_GPG_RECIPIENT
# then rsyncs to BACKUP_OFFSITE_RSYNC_TARGET. Idempotent; safe to re-run.
#
# Schedule via cron on the homelab:
#   0 3 * * * /opt/chronos/scripts/backup-db.sh >> /var/log/chronos-backup.log 2>&1

set -euo pipefail

: "${SQLITE_PATH:?SQLITE_PATH not set}"
: "${BACKUP_GPG_RECIPIENT:?BACKUP_GPG_RECIPIENT not set}"
: "${BACKUP_OFFSITE_RSYNC_TARGET:=}"

BACKUP_DIR="${BACKUP_DIR:-$(dirname "$SQLITE_PATH")/backups}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
SNAPSHOT="$BACKUP_DIR/chronos-${STAMP}.db"
ENCRYPTED="${SNAPSHOT}.gpg"

# Live snapshot via online .backup (consistent under WAL).
sqlite3 "$SQLITE_PATH" ".backup '$SNAPSHOT'"

# Encrypt then remove the plaintext.
gpg --batch --yes --trust-model always \
    --output "$ENCRYPTED" \
    --encrypt --recipient "$BACKUP_GPG_RECIPIENT" \
    "$SNAPSHOT"
shred -u "$SNAPSHOT"
chmod 600 "$ENCRYPTED"

# Prune local copies older than 30 days.
find "$BACKUP_DIR" -name 'chronos-*.db.gpg' -type f -mtime +30 -delete

# Offsite rsync (weekly is fine; this script runs daily and rsync is incremental).
if [[ -n "$BACKUP_OFFSITE_RSYNC_TARGET" ]]; then
  rsync -az --delete \
        --include='chronos-*.db.gpg' --exclude='*' \
        "$BACKUP_DIR/" "$BACKUP_OFFSITE_RSYNC_TARGET/"
fi

echo "backup ok: $ENCRYPTED"
