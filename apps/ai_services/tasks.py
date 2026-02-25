"""
Celery tasks for asynchronous AI processing.

These tasks allow expensive AI operations (bill scanning, trip planning)
to be offloaded to a Celery worker queue so the HTTP request can return
immediately with a task ID.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='apps.ai_services.tasks.task_scan_bill',
    max_retries=2,
    default_retry_delay=10,
    soft_time_limit=120,
    time_limit=150,
)
def task_scan_bill(self, image_base64, group_members=None):
    """
    Asynchronously scan a receipt image and return parsed data.

    Parameters
    ----------
    image_base64 : str
        Base64-encoded receipt image.
    group_members : list[dict] | None
        Optional member list for split suggestions.

    Returns
    -------
    dict
        Parsed receipt data (items, total, splits, etc.).
    """
    try:
        from apps.ai_services.services.bill_scanner import parse_receipt

        result = parse_receipt(
            image_data=image_base64,
            group_members=group_members,
        )
        logger.info('Async bill scan completed successfully.')
        return result

    except Exception as exc:
        logger.error('Async bill scan failed (attempt %d): %s', self.request.retries, exc)
        # Retry on transient failures
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name='apps.ai_services.tasks.task_plan_trip',
    max_retries=2,
    default_retry_delay=10,
    soft_time_limit=120,
    time_limit=150,
)
def task_plan_trip(self, description, preferences=None):
    """
    Asynchronously generate a trip plan.

    Parameters
    ----------
    description : str
        Natural-language trip description.
    preferences : dict | None
        Optional user preferences.

    Returns
    -------
    dict
        Structured trip plan.
    """
    try:
        from apps.ai_services.services.trip_planner import generate_trip_plan

        result = generate_trip_plan(
            description=description,
            preferences=preferences,
        )
        logger.info('Async trip planning completed successfully.')
        return result

    except Exception as exc:
        logger.error('Async trip planning failed (attempt %d): %s', self.request.retries, exc)
        raise self.retry(exc=exc)
