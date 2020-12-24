web: gunicorn app:app
worker: celery -A app.celery worker --loglevel=INFO
beat: celery -A app.celery beat --loglevel=INFO
