"""
Utility functions for the Groups app.
"""
import secrets
import string


def generate_invite_code(length=8):
    """
    Generate a unique, uppercase alphanumeric invite code.

    Args:
        length: Length of the code (default 8).

    Returns:
        A random uppercase alphanumeric string.
    """
    from apps.groups.models import Group

    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(length))
        if not Group.objects.filter(invite_code=code).exists():
            return code
