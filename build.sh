#!/usr/bin/env bash
# Render.com build script for Tag Along Backend
set -o errexit

# Install dependencies
pip install -r requirements/production.txt

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate
