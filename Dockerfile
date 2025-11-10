FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl netcat-traditional \
  && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# App code
COPY . /app

# Expose Django port
EXPOSE 8000

# Default environment (override in docker-compose)
ENV DJANGO_SETTINGS_MODULE=school_management.settings \
    GUNICORN_WORKERS=3 \
    GUNICORN_TIMEOUT=60

# Healthcheck (optional; relies on an accessible endpoint)
# HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
#   CMD curl -fsS http://localhost:8000/api/v1/events/public || exit 1

# Entrypoint runs migrations if needed (SQLite only used for Django internals)
CMD gunicorn school_management.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS} \
    --timeout ${GUNICORN_TIMEOUT} \
    --log-level info


