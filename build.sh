#!/usr/bin/env bash
# Render.com build script for Tag Along Backend
set -o errexit

# Install dependencies
pip install -r requirements/production.txt

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate

# Auto-create superuser from env vars (optional — for Django Admin access)
# Set DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_USERNAME on Render
# The || true ensures build doesn't fail if superuser already exists or env vars aren't set
python manage.py createsuperuser --noinput || true
