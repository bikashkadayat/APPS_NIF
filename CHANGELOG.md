# Changelog

All notable changes to the NIF Office Management System are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning:
[SemVer](https://semver.org/). Commit convention: [Conventional Commits](https://www.conventionalcommits.org/)
(see `docs/CONTRIBUTING.md`).

## [Unreleased]

### Security
- **Closed unauthenticated media serving (Critical).** Removed the public
  `/media/<path>` catch-all that streamed every upload without auth. All
  user files (memo attachments/vouchers, profile photos, report files) are now
  served only via short-lived HMAC-**signed, expiring URLs** (`documents.protected_media`),
  header-free so they work in `<img>`/`<a>`. Added regression tests.
- **Idle auto-logout** (default 20 min, configurable `VITE_IDLE_TIMEOUT_MIN`): a
  30s warning modal, activity resets the timer, on timeout the refresh token is
  blacklisted and the user is returned to login; multi-tab consistent.

### Added
- **CI/CD** (GitHub Actions): backend `pytest`+coverage, `ruff`, migration-drift
  check, `pip-audit`; frontend `vitest`+`eslint`+`vite build`+`npm audit`; secret
  scan (gitleaks); Conventional-Commits gate on PRs.
- **Automated encrypted off-host DB backups** (`backend/deploy/backup.sh`): daily
  `pg_dump` → gzip → AES-256, off-host copy (S3/rsync), retention rotation, plus a
  tested restore runbook (`backend/deploy/restore.sh`, `docs/BACKUP.md`).
- **Daily notification reconciliation** cron so the bell count can never drift
  from the actionable Pending Approvals queue.
- Contributor guide + Conventional-Commits config (`docs/CONTRIBUTING.md`,
  `commitlint.config.js`), this CHANGELOG.

### Fixed
- `react-hooks/rules-of-hooks` violation on the Asset Assignment page (a `useMemo`
  after an early return).

<!-- Backfill note: commits prior to this entry used placeholder messages
     ("your message"). History from here forward follows Conventional Commits. -->

## Earlier (pre-CHANGELOG)
Leave/memo/inventory/attendance modules, category-based leave engine, PDF
generation with the NIF letterhead, notifications, favicon set, login polish,
approval-queue ⇄ notification single-source resolver, attendance registration-date
absent floor, and inventory RBAC — delivered incrementally (see git history).
