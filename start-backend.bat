@echo off
echo Starting Fold Backend API Server...
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found at venv\
    echo Please ensure you have created a virtual environment
    echo.
)

echo Starting FastAPI server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

uvicorn src.api.main:app --reload --port 8000
