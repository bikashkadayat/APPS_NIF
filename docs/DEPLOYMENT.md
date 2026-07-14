# Deployment — self-hosted VPS (Docker Compose)

The whole stack runs on a single VPS with Docker Compose. The production stack
(`docker-compose.prod.yml`) bundles a **Caddy** reverse proxy that terminates
TLS (automatic HTTPS), serves the pre-built React SPA, and proxies the API to
Gunicorn — so the browser is always same-origin (no CORS).

Services: `db` (PostgreSQL), `backend` (Django + Gunicorn + WeasyPrint), `cron`
(scheduled jobs), `web` (Caddy: TLS + built SPA + reverse proxy).

> Requirements: a VPS with Docker + the Docker Compose plugin, a domain name
> whose DNS A/AAAA record points at the VPS IP, and public ports 80 + 443.

---

## Dev vs prod — which compose file

| | File | Command | TLS | Frontend | Security flags |
|---|---|---|---|---|---|
| **Local dev** | `docker-compose.yml` | `docker compose up` | none (HTTP) | Vite dev server `:5173` | forced **off** (localhost) |
| **Production** | `docker-compose.prod.yml` | `docker compose -f docker-compose.prod.yml up -d --build` | Caddy auto-HTTPS | built `dist` via Caddy | secure by default |

The two stacks are independent. This guide is entirely about the **prod** stack.

---

## 1. Get the code onto the VPS

```bash
git clone <your-repo-url> nif && cd nif
```

## 2. Configure `.env`

```bash
cp .env.example .env
```

Fill in **every** value below (the prod stack refuses to start if a required one
is missing). Example values are for `https://nif.example.com`.

| Variable | Example | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | *(random)* | `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"` |
| `DJANGO_DEBUG` | `False` | must be `False` in prod |
| `DJANGO_ALLOWED_HOSTS` | `nif.example.com` | your domain; `localhost,127.0.0.1` are appended automatically |
| `SITE_DOMAIN` | `nif.example.com` | domain Caddy serves + gets a TLS cert for |
| `DATABASE_PASSWORD` | *(strong)* | |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://nif.example.com` | **required** — admin/session POSTs 403 without it |
| `FRONTEND_URL` | `https://nif.example.com` | email action links |
| `SITE_URL` | `https://nif.example.com` | PDF QR verification URLs |

Security flags default to secure (`SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE` = True; `HSTS = 31536000`). Leave them unset in prod.

**Email (SMTP).** To actually send mail, set `EMAIL_BACKEND` to the SMTP backend
and all of `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` — the app
**fails fast at boot** if SMTP is selected but any of those are empty:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=apikey-or-user
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=no-reply@nif.example.com
```

Leave `EMAIL_BACKEND` unset for a mail-less deployment (emails print to logs).

`.env` is gitignored — never commit it.

## 3. Build and start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

`backend` runs `migrate` + `collectstatic` + Gunicorn on start; `web` builds the
SPA and starts Caddy, which fetches the TLS certificate (needs DNS + ports 80/443
reachable). Watch progress:

```bash
docker compose -f docker-compose.prod.yml logs -f web backend
```

## 4. Create the first admin user

The database starts empty:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py shell -c "
from users.models import User
u,_=User.objects.get_or_create(username='admin', defaults={'email':'admin@nif.test'})
u.email='admin@nif.test'; u.role=User.Roles.ADMIN; u.is_active=True; u.is_staff=True
u.must_change_password=False; u.set_password('CHANGE-ME-NOW'); u.save()
print('admin ready:', u.email)
"
```

Log in, then create the other users from the Admin console.

---

## 5. Reverse proxy — already included

The `web` service **is** the reverse proxy (Caddy). No separate nginx setup is
needed. It routes:

- `/api/*`, `/admin/*`, `/static/*`, `/media/*` → `backend:8000` (Gunicorn)
- everything else → the built SPA (`/srv`) with SPA fallback to `index.html`

Config lives in `deploy/Caddyfile`; the domain comes from `SITE_DOMAIN`. Caddy
forwards `X-Forwarded-Proto`, which Django reads (`SECURE_PROXY_SSL_HEADER`) to
recognise the forwarded HTTPS and avoid redirect loops.

To run a **local HTTP test** without a real domain/cert, set `SITE_DOMAIN=:80`
and the three `DJANGO_*_SECURE` flags to `False` in `.env`.

---

## 6. Verify

1. Open `https://nif.example.com` — valid TLS padlock.
2. Log in with the admin account from Step 4.
3. Create a memo, submit, review, approve, download the PDF (QR link uses your
   domain).

Run the post-deploy checklist below.

### Post-deploy checklist

- [ ] Site loads over **HTTPS** with a valid certificate.
- [ ] Session/CSRF cookies have the **Secure** flag (browser dev tools → Application → Cookies).
- [ ] Response carries **`Strict-Transport-Security`** (HSTS) — `curl -sI https://nif.example.com | grep -i strict`.
- [ ] Admin login + a POST from the domain succeed (**no CSRF 403**).
- [ ] A test email sends (`docker compose -f docker-compose.prod.yml exec backend python manage.py sendtestemail you@example.com`).
- [ ] Email action links + PDF QR URLs point at **`https://nif.example.com`**, not localhost.
- [ ] Upload a profile photo, then `docker compose -f docker-compose.prod.yml up -d --build` again — the photo **survives** (media volume).

---

## Notes / production hardening

- **Media persistence**: uploaded attachments, profile photos and generated PDFs
  live in the named Docker volume `media_data` (mounted at `/app/media` on both
  `backend` and `cron`), so they survive rebuilds, restarts and redeploys. For
  multi-instance / durable object storage, set `USE_S3=True` and the `AWS_*`
  vars in `.env` (needs `django-storages[boto3]` — see `backend/requirements/`).
- **Database backups**: `postgres_data` is a named volume — back it up regularly,
  e.g. `docker compose -f docker-compose.prod.yml exec db pg_dump -U leave_user leave_system > backup.sql`.
- **Static files**: served by WhiteNoise from within Gunicorn (content-hashed,
  far-future cache headers); `collectstatic` runs on every backend start.
- **Secrets**: `DJANGO_SECRET_KEY`, DB credentials and SMTP come from `.env` only;
  the insecure defaults baked into `Dockerfile.backend` are always overridden.
- **Updating**: `git pull && docker compose -f docker-compose.prod.yml up -d --build`.
