#!/usr/bin/env sh
# Encrypted, off-host PostgreSQL backup for the NIF Office Management System.
# Runs daily from the `cron` container (see backend/deploy/crontab).
#
# Pipeline:  pg_dump (custom format) -> gzip -> AES-256 (openssl) -> off-host copy
#            -> retention rotation.
#
# Required env (from .env):
#   DATABASE_HOST DATABASE_PORT DATABASE_NAME DATABASE_USER DATABASE_PASSWORD
#   BACKUP_ENCRYPTION_KEY      strong passphrase for AES-256 (KEEP OFFLINE/SECRET)
# Optional env:
#   BACKUP_DIR                 local staging dir (default /backups)
#   BACKUP_RETENTION_DAYS      keep N days locally (default 14)
#   BACKUP_S3_BUCKET           s3://bucket/prefix  -> uploaded with `aws s3 cp`
#   BACKUP_RSYNC_TARGET        user@host:/path     -> uploaded with `scp`
# Restore: see deploy/restore.sh / docs/BACKUP.md.
set -eu

: "${BACKUP_ENCRYPTION_KEY:?set BACKUP_ENCRYPTION_KEY (backup passphrase) in .env}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
OUT="${BACKUP_DIR}/nif-${DATABASE_NAME:-leave_system}-${STAMP}.dump.gz.enc"
mkdir -p "$BACKUP_DIR"

export PGPASSWORD="${DATABASE_PASSWORD}"
echo "[backup] dumping ${DATABASE_NAME} ..."
pg_dump -h "${DATABASE_HOST:-db}" -p "${DATABASE_PORT:-5432}" -U "${DATABASE_USER}" \
        -F c "${DATABASE_NAME}" \
  | gzip -9 \
  | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_ENCRYPTION_KEY -out "$OUT"
echo "[backup] wrote $OUT ($(wc -c < "$OUT") bytes)"

# --- Off-host copy (choose whichever target env is set) ---
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
  echo "[backup] uploading to ${BACKUP_S3_BUCKET} ..."
  aws s3 cp "$OUT" "${BACKUP_S3_BUCKET}/"
elif [ -n "${BACKUP_RSYNC_TARGET:-}" ]; then
  echo "[backup] copying to ${BACKUP_RSYNC_TARGET} ..."
  scp -o StrictHostKeyChecking=accept-new "$OUT" "${BACKUP_RSYNC_TARGET}/"
else
  echo "[backup] WARNING: no BACKUP_S3_BUCKET / BACKUP_RSYNC_TARGET set — backup is LOCAL ONLY (not off-host)."
fi

# --- Retention: delete local encrypted backups older than N days ---
find "$BACKUP_DIR" -name 'nif-*.dump.gz.enc' -type f -mtime "+${RETENTION}" -delete 2>/dev/null || true
echo "[backup] done. Local retention: ${RETENTION} days."
