@echo off
echo Starting Celery Worker...
cd backend
.\.venv\Scripts\celery -A app.tasks.celery_app:celery_app worker --loglevel=info -P solo
pause
