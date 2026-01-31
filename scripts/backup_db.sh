#!/bin/sh
# Production backup script (DoD §13.4, docs/31-backups-and-dr.md).
#
# Run from a sidecar container or host cron. Set:
#   DATABASE_URL              postgres://user:pass@host:5432/db
#   BACKUP_DIR                /var/orbiteus/backups (local staging)
#   BACKUP_RETENTION_DAYS     default 30
#
# Optional S3 push (set ALL three to enable):
#   BACKUP_S3_BUCKET          e.g. "orbiteus-backups"
#   BACKUP_S3_PREFIX          e.g. "prod/orbiteus/"  (trailing slash)
#   BACKUP_S3_ENDPOINT        e.g. "https://s3.amazonaws.com" (or
#                             your S3-compatible provider's endpoint)
# AWS / S3-compatible auth from the standard env vars
# (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION).
#
# Flow:
#   pg_dump → gzip → atomic rename → optional `aws s3 cp` →
#   expire local files older than BACKUP_RETENTION_DAYS.
set -eu

: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${BACKUP_DIR:=/var/orbiteus/backups}"
: "${BACKUP_RETENTION_DAYS:=30}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
FILENAME="orbiteus_$TIMESTAMP.sql.gz"
TARGET="$BACKUP_DIR/$FILENAME"
TMP="$TARGET.partial"

echo "[backup] dumping → $TMP"
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip --best > "$TMP"
mv "$TMP" "$TARGET"
SIZE=$(du -h "$TARGET" | cut -f1)
echo "[backup] done: $TARGET ($SIZE)"

if [ "${BACKUP_S3_BUCKET:-}" ] && [ "${BACKUP_S3_PREFIX:-}" ] && [ "${BACKUP_S3_ENDPOINT:-}" ]; then
  if command -v aws >/dev/null 2>&1; then
    REMOTE="s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX$FILENAME"
    echo "[backup] uploading → $REMOTE"
    aws --endpoint-url="$BACKUP_S3_ENDPOINT" \
        s3 cp "$TARGET" "$REMOTE" --no-progress
    echo "[backup] uploaded: $REMOTE"
  else
    echo "[backup] WARN: BACKUP_S3_BUCKET set but \`aws\` CLI is not installed; skipping push" >&2
  fi
fi

echo "[backup] expiring files older than $BACKUP_RETENTION_DAYS days"
find "$BACKUP_DIR" -name 'orbiteus_*.sql.gz' -type f -mtime "+$BACKUP_RETENTION_DAYS" -delete || true
