@echo off
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin
echo Starting Redis...
docker-compose up -d redis
echo Starting FastAPI Backend...
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
pause
