"""
Celery configuration for Tag Along backend.

Only configures Celery if CELERY_BROKER_URL is set in the environment.
On free-tier deployments without Redis, Celery tasks are skipped gracefully.
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Only initialise Celery if a broker is configured
_broker = os.environ.get('CELERY_BROKER_URL', '')
if _broker:
    from celery import Celery
    from celery.schedules import crontab

    app = Celery('tag_along')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()

    # Periodic tasks
    app.conf.beat_schedule = {
        'refresh-exchange-rates': {
            'task': 'apps.expenses.tasks.refresh_exchange_rates',
            'schedule': crontab(minute=0),  # Every hour
        },
        'cleanup-expired-consents': {
            'task': 'apps.locations.tasks.cleanup_expired_consents',
            'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        },
    }

    @app.task(bind=True, ignore_result=True)
    def debug_task(self):
        print(f'Request: {self.request!r}')
else:
    app = None
