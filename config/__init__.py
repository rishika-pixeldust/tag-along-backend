# Import Celery app if configured (requires Redis broker)
from .celery import app as celery_app  # noqa: F401

__all__ = ('celery_app',)
