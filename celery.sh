#!/usr/bin/env bash
celery -A app.celery worker --loglevel=INFO &
celery -A app.celery beat --loglevel=INFO
