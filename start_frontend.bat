@echo off
echo Starting Next.js Frontend (Writing logs to frontend.log)...
cd frontend
npm run dev > frontend.log 2>&1
pause
