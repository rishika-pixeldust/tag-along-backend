"""
Django settings module.

Loads the appropriate settings based on the DJANGO_ENV environment variable.
Defaults to 'development' if not set.
"""
import os

env = os.environ.get('DJANGO_ENV', 'development')

if env == 'production':
    from config.settings.production import *  # noqa: F401, F403
else:
    from config.settings.development import *  # noqa: F401, F403
