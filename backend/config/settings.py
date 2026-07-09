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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

# Database - uses environment variables for Docker
import os
DATABASE_ENGINE = os.getenv('DATABASE_ENGINE', 'postgresql')
if DATABASE_ENGINE == 'sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'leave_system'),
            'USER': os.getenv('DATABASE_USER', 'leave_user'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD', 'leave_password_123'),
            'HOST': os.getenv('DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kathmandu'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'users.authentication.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# H6: do not allow all CORS origins in production unless explicitly opted in.
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'True' if DEBUG else 'False').lower() in ('true', '1', 'yes')
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:8000').split(',')

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
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# ---------------------------------------------------------------------------
# Structured logging (Phase 5)
# Daily-rotating JSON file at logs/nifn.log (30 days), per-module loggers,
# correlation ids injected by config.middleware.RequestIDMiddleware.
# ---------------------------------------------------------------------------
# Email (scheduled reports). Console backend by default in dev; configure SMTP
# via env in production.
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@nifportal.local')

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

LOGS_DIR = BASE_DIR / 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)

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
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': str(LOGS_DIR / 'nifn.log'),
            'when': 'midnight',
            'backupCount': 30,
            'formatter': 'json',
            'filters': ['request_id'],
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['request_id'],
        },
    },
    'loggers': {
        module: {'handlers': ['file', 'console'], 'level': 'INFO', 'propagate': False}
        for module in ('memos', 'leaves', 'audit')
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}



