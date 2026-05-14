@echo off
echo ================================================================================
echo                        FOLD - STARTING ALL SERVERS
echo ================================================================================
echo.
echo This will start both the backend and frontend servers.
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press Ctrl+C in each window to stop the servers.
echo.
pause

REM Start backend in a new window
echo Starting backend server...
start "Fold Backend API" cmd /k "venv\Scripts\activate.bat && uvicorn src.api.main:app --reload --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
echo Starting frontend server...
start "Fold Frontend" cmd /k "cd web && npm run dev"

echo.
echo ================================================================================
echo Both servers are starting in separate windows.
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Close the terminal windows to stop the servers.
echo ================================================================================
echo.
