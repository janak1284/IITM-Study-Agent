@echo off
echo Starting Flask API Backend...
start "Flask API" cmd /c "python app.py"

echo Starting React Frontend...
cd frontend
start "React UI" cmd /c "npm run dev"

echo Both servers are starting. 
echo 1. The React app will open at http://localhost:5173
echo 2. The Flask API is running at http://localhost:5000
pause
