@echo off
echo Starting Fold Frontend (Next.js)...
echo.

REM Check if node_modules exists
if not exist web\node_modules (
    echo Warning: node_modules not found in web directory
    echo Please run 'npm install' in the web directory first
    echo.
    pause
    exit /b 1
)

echo Navigating to web directory...
cd web

echo Starting Next.js development server on http://localhost:3000
echo Press Ctrl+C to stop the server
echo.

npm run dev
