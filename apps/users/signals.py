"""
Signals for the Users app.
"""
import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

User = None


def get_user_model_lazy():
    global User
    if User is None:
        from django.contrib.auth import get_user_model
        User = get_user_model()
    return User


@receiver(post_save, sender='users.User')
def user_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for post-save on User model.
    Logs user creation events.
    """
    if created:
        logger.info(
            'New user registered: %s (id=%s)',
            instance.email,
            instance.id,
        )
