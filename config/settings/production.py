"""
Production-specific Django settings.

All sensitive values are read from environment variables.
"""
from config.settings.base import *  # noqa: F401, F403
from config.settings.base import env

# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------
DEBUG = False

# ---------------------------------------------------------------------------
# Allowed Hosts
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# ---------------------------------------------------------------------------
# Secret Key
# ---------------------------------------------------------------------------
SECRET_KEY = env('SECRET_KEY')

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    'default': env.db('DATABASE_URL'),
}
DATABASES['default']['CONN_MAX_AGE'] = env.int('DB_CONN_MAX_AGE', default=600)
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# ---------------------------------------------------------------------------
# Cache — Redis if available, otherwise LocMemCache (free tier fallback)
# ---------------------------------------------------------------------------
_redis_url = env('REDIS_URL', default='')
if _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_url,
            'TIMEOUT': 300,
            'OPTIONS': {
                'db': 0,
            },
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'tag-along-prod-cache',
        }
    }

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

# ---------------------------------------------------------------------------
# CORS — configurable via env (allow all for mobile app, restrict for web)
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# ---------------------------------------------------------------------------
# Email (production should use a real email backend)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@tagalong.app')

# ---------------------------------------------------------------------------
# Static files — WhiteNoise by default, S3 if bucket configured
# ---------------------------------------------------------------------------
_s3_bucket = env('AWS_STORAGE_BUCKET_NAME', default='')
if _s3_bucket:
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
