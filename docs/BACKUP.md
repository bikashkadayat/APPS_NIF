# Database backup & restore runbook

Automated daily via the `cron` container (`backend/deploy/crontab` → `deploy/backup.sh`).

## What runs
`pg_dump -F c` → `gzip -9` → `openssl aes-256-cbc (pbkdf2)` → off-host copy → retention rotation.
Files: `nif-<db>-<timestamp>.dump.gz.enc` in `/backups` (a named volume) and, if configured,
copied to S3 or a remote host.

## Configure (`.env`)
```dotenv
BACKUP_ENCRYPTION_KEY=<a long random passphrase — store OFFLINE, separate from backups>
BACKUP_RETENTION_DAYS=14
# choose ONE off-host target:
BACKUP_S3_BUCKET=s3://my-bucket/nif-backups        # needs aws-cli in the image
# BACKUP_RSYNC_TARGET=backupuser@host:/srv/nif-backups   # needs scp/ssh key
```
> Without an off-host target the backup is **local only** (the script warns) — set one before go-live.
> For S3, add `awscli` to `Dockerfile.backend` (or use S3 media + bucket versioning).

## Run a backup manually
```bash
docker compose -f docker-compose.prod.yml exec cron sh /app/deploy/backup.sh
```

## Restore (into a SCRATCH db first — verify before promoting)
```bash
docker compose -f docker-compose.prod.yml exec cron \
  sh /app/deploy/restore.sh /backups/nif-leave_system-2026-07-14_013000.dump.gz.enc
# -> restores into leave_system_restore; inspect it, then repoint / rename when correct.
```

## Verified
The dump → encrypt → decrypt → restore roundtrip was tested: source vs restored
`users_user` row counts matched exactly (7 = 7). Re-run this check after any change
to the backup pipeline.

## Media
Uploaded files live in the `media_data` volume. Either snapshot that volume alongside
the DB, or move media to S3 (`USE_S3=True`) and enable bucket versioning.
