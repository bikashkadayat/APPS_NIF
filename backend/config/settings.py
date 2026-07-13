import os
import sys
from pathlib import Path
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# H6: fail-closed, prod-safe defaults. DEBUG must be explicitly opted in; the
# insecure fallbacks below are only tolerated in DEBUG or under the test runner,
# and the boot guards refuse to start a real production process configured
# insecurely.
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')
_RUNNING_TESTS = 'pytest' in sys.modules or 'test' in sys.argv
_ALLOW_INSECURE = DEBUG or _RUNNING_TESTS


def _env_bool(name, default):
    """Read a boolean from the environment, falling back to `default`."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('true', '1', 'yes', 'on')


def _env_list(name, default=''):
    """Read a comma-separated list from the environment."""
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if _ALLOW_INSECURE:
        SECRET_KEY = 'django-insecure-nif-portal-secret-key'  # dev / test only
    else:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY must be set when DEBUG is off.'
        )

_default_hosts = '*' if _ALLOW_INSECURE else ''
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', _default_hosts).split(',') if h.strip()]
if not _ALLOW_INSECURE and (not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        'DJANGO_ALLOWED_HOSTS must be an explicit host list (no "*") when DEBUG is off.'
    )

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    
    # Local Apps
    'users.apps.UsersConfig',
    'leaves.apps.LeavesConfig',
    'memos.apps.MemosConfig',
    'audit.apps.AuditConfig',
    'reports.apps.ReportsConfig',
    'notifications.apps.NotificationsConfig',
    'documents.apps.DocumentsConfig',
    'attendance.apps.AttendanceConfig',
]

# Attendance policy (configurable). Times are Asia/Kathmandu (TIME_ZONE).
ATTENDANCE_OFFICE_START = os.getenv('ATTENDANCE_OFFICE_START', '10:00')     # late after this
ATTENDANCE_FULL_DAY_HOURS = float(os.getenv('ATTENDANCE_FULL_DAY_HOURS', '8'))
ATTENDANCE_HALF_DAY_HOURS = float(os.getenv('ATTENDANCE_HALF_DAY_HOURS', '5'))  # half-day if below

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serves the collected static files (Django admin + DRF assets)
    # straight from Gunicorn in production; must sit immediately after
    # SecurityMiddleware and before everything else.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'config.middleware.RequestIDMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database - configured entirely via environment variables (12-factor).
DATABASE_ENGINE = os.getenv('DATABASE_ENGINE', 'postgresql')
if DATABASE_ENGINE == 'sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # No hardcoded credentials: the DB password must come from the environment.
    # In a real (non-DEBUG, non-test) run a missing password fails fast instead
    # of silently falling back to a shared, world-readable default.
    _db_password = os.getenv('DATABASE_PASSWORD')
    if not _db_password:
        if _ALLOW_INSECURE:
            _db_password = 'postgres'  # dev / test only
        else:
            raise ImproperlyConfigured(
                'DATABASE_PASSWORD must be set when DEBUG is off.'
            )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'leave_system'),
            'USER': os.getenv('DATABASE_USER', 'leave_user'),
            'PASSWORD': _db_password,
            'HOST': os.getenv('DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
            # Reuse connections across requests (production performance).
            'CONN_MAX_AGE': int(os.getenv('DATABASE_CONN_MAX_AGE', '60')),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    # Phase 9: reject common/breached passwords and all-numeric passwords.
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kathmandu'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Let WhiteNoise also serve assets straight from the finders under runserver,
# so behaviour matches production even before collectstatic.
WHITENOISE_USE_FINDERS = True

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# File storage (Django 4.2+ STORAGES API) - Phase 1 (static) & Phase 2 (media).
#   staticfiles -> WhiteNoise, compressed + content-hashed manifest, so the
#                  Django admin / DRF browsable API load their CSS/JS in prod
#                  with far-future cache headers.
#   default     -> local filesystem by default (Render persistent disk, so
#                  uploads survive redeploys), or an S3-compatible bucket when
#                  USE_S3=True (recommended at scale / multi-instance).
# ---------------------------------------------------------------------------
USE_S3 = _env_bool('USE_S3', False)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
if USE_S3:
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': os.getenv('AWS_STORAGE_BUCKET_NAME'),
            'region_name': os.getenv('AWS_S3_REGION_NAME', ''),
            # Set for S3-compatible providers (Cloudflare R2, MinIO, Spaces).
            'endpoint_url': os.getenv('AWS_S3_ENDPOINT_URL') or None,
            'access_key': os.getenv('AWS_ACCESS_KEY_ID'),
            'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'file_overwrite': False,
            'querystring_auth': _env_bool('AWS_S3_QUERYSTRING_AUTH', False),
            'default_acl': None,
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'users.authentication.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# H6: do not allow all CORS origins in production unless explicitly opted in.
CORS_ALLOW_ALL_ORIGINS = _env_bool('CORS_ALLOW_ALL_ORIGINS', DEBUG)
CORS_ALLOWED_ORIGINS = _env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:8000')

# ---------------------------------------------------------------------------
# HTTPS / security hardening (Phase 3).
# Designed to run behind Render's / Vercel's TLS-terminating proxy: the proxy
# forwards X-Forwarded-Proto, so Django recognises forwarded HTTPS and does not
# redirect-loop. Cookie / HSTS / redirect enforcement is gated on production
# (not DEBUG) and each toggle is env-overridable, so local HTTP and the test
# suite keep working while production is locked down by default.
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Admin / session CSRF over HTTPS behind a proxy needs the exact origin(s).
# Default covers any Render subdomain; add your Vercel/custom domain via env.
CSRF_TRUSTED_ORIGINS = _env_list('DJANGO_CSRF_TRUSTED_ORIGINS', 'https://*.onrender.com')

# Response security headers (always on - harmless over HTTP too).
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# HTTPS enforcement - defaults to ON in production, OFF in DEBUG/local HTTP.
SESSION_COOKIE_SECURE = _env_bool('DJANGO_SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = _env_bool('DJANGO_CSRF_COOKIE_SECURE', not DEBUG)
SECURE_SSL_REDIRECT = _env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = _env_bool('DJANGO_SECURE_HSTS_PRELOAD', not DEBUG)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    # H6: fail closed - every endpoint requires auth unless it explicitly opts
    # out with permission_classes = [AllowAny] (health, login, refresh).
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/min',
        'user': '200/min',
        'memo_directory': '30/min',  # assignee-directory search (H5)
    },
}

SIMPLE_JWT = {
    # M3: short-lived access tokens; refresh tokens rotate and the old one is
    # blacklisted on use, so a leaked token has a small window and can be revoked.
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# ---------------------------------------------------------------------------
# Structured logging (Phase 5)
# Daily-rotating JSON file at logs/nifn.log (30 days), per-module loggers,
# correlation ids injected by config.middleware.RequestIDMiddleware.
# ---------------------------------------------------------------------------
# Email (scheduled reports). Console backend by default in dev; configure SMTP
# via env in production.
# Default to the console backend only in DEBUG/tests; real deployments default to
# SMTP so nobody silently ships with emails going nowhere.
_DEFAULT_EMAIL_BACKEND = (
    'django.core.mail.backends.console.EmailBackend' if _ALLOW_INSECURE
    else 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', _DEFAULT_EMAIL_BACKEND)
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@nifportal.local')

# Fail-closed on boot: if a prod run uses the SMTP backend, the host + credentials
# must be present (a misconfigured mailer should fail at startup, not silently at
# send time). The request path itself stays fail-safe (sends are wrapped + logged).
if not _ALLOW_INSECURE and EMAIL_BACKEND.endswith('smtp.EmailBackend'):
    _missing_smtp = [
        name for name, val in (
            ('EMAIL_HOST', EMAIL_HOST),
            ('EMAIL_HOST_USER', EMAIL_HOST_USER),
            ('EMAIL_HOST_PASSWORD', EMAIL_HOST_PASSWORD),
        ) if not val
    ]
    if _missing_smtp:
        raise ImproperlyConfigured(
            f"SMTP email backend requires {', '.join(_missing_smtp)} when DEBUG is off. "
            "Set them, or set EMAIL_BACKEND to the console backend for a mail-less deployment."
        )

# Send notification emails synchronously (tests / small deployments). In prod the
# default (False) runs each send in a background thread so the API never blocks.
NOTIFICATIONS_RUN_SYNC = os.getenv('NOTIFICATIONS_RUN_SYNC', 'False').lower() in ('true', '1', 'yes')
# Leave-workflow email toggles (global; per-user opt-out lives in NotificationPreference).
NOTIFY_CC_HR_ON_SUBMIT = os.getenv('NOTIFY_CC_HR_ON_SUBMIT', 'True').lower() in ('true', '1', 'yes')
NOTIFY_EMPLOYEE_ON_L1 = os.getenv('NOTIFY_EMPLOYEE_ON_L1', 'True').lower() in ('true', '1', 'yes')
NOTIFY_AUDIT_COPY_ON_FINAL = os.getenv('NOTIFY_AUDIT_COPY_ON_FINAL', 'False').lower() in ('true', '1', 'yes')

# Generate reports synchronously (set True in tests / small deployments).
REPORTS_RUN_SYNC = os.getenv('REPORTS_RUN_SYNC', 'False').lower() in ('true', '1', 'yes')

# Notifications: base URL for building action/unsubscribe links in emails, and a
# flag to send notification emails synchronously (tests / small deployments).
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
# Public base URL of this backend (used to build QR verification links on PDFs).
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8001')
# Organization details printed on PDF letterheads/certificates (CMS-overridable).
ORG_INFO = {
    'name': os.getenv('ORG_NAME', 'Nepal Internet Foundation'),
    'address': os.getenv('ORG_ADDRESS', 'Kathmandu, Nepal'),
    'tel': os.getenv('ORG_TEL', '+977-1-0000000'),
    'email': os.getenv('ORG_EMAIL', 'info@nif.org.np'),
    'website': os.getenv('ORG_WEBSITE', 'www.nif.org.np'),
}
NOTIFICATIONS_RUN_SYNC = os.getenv('NOTIFICATIONS_RUN_SYNC', 'False').lower() in ('true', '1', 'yes')
# Reports older than this are purged by purge_expired_reports.
REPORTS_RETENTION_DAYS = int(os.getenv('REPORTS_RETENTION_DAYS', '30'))

# ---------------------------------------------------------------------------
# Logging (Phase 6): stream everything to stdout so the platform (Render /
# Docker) aggregates it. No local log files -> safe under multi-worker Gunicorn
# (no rotation races) and nothing is lost on redeploy. Structured JSON in
# production for log aggregation, human-readable in DEBUG. Correlation ids are
# injected by config.middleware.RequestIDMiddleware.
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv('DJANGO_LOG_LEVEL', 'INFO').upper()
_LOG_FORMATTER = 'simple' if DEBUG else 'json'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_id': {'()': 'config.logging_utils.RequestIDFilter'},
    },
    'formatters': {
        'json': {'()': 'config.logging_utils.JSONFormatter'},
        'simple': {'format': '%(levelname)s %(name)s [%(request_id)s] %(message)s'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': _LOG_FORMATTER,
            'filters': ['request_id'],
        },
    },
    'loggers': {
        module: {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False}
        for module in ('memos', 'leaves', 'audit')
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}



