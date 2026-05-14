@echo off
echo ================================================================================
echo                        FOLD - INITIAL SETUP SCRIPT
echo ================================================================================
echo.
echo This script will help you set up the Fold application for the first time.
echo.
pause

REM ============================================
REM STEP 1: Create Python Virtual Environment
REM ============================================
echo.
echo [STEP 1/5] Creating Python virtual environment...
echo.

if exist venv (
    echo Virtual environment already exists. Skipping creation.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        echo Please make sure Python 3.11+ is installed
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
)

REM ============================================
REM STEP 2: Activate Virtual Environment
REM ============================================
echo.
echo [STEP 2/5] Activating virtual environment...
echo.

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated!

REM ============================================
REM STEP 3: Install Python Dependencies
REM ============================================
echo.
echo [STEP 3/5] Installing Python dependencies...
echo This may take several minutes...
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)
echo Python dependencies installed successfully!

REM ============================================
REM STEP 4: Setup Backend Environment Variables
REM ============================================
echo.
echo [STEP 4/5] Setting up backend environment variables...
echo.

if exist .env (
    echo .env file already exists. Skipping.
) else (
    if exist .env.example (
        copy .env.example .env
        echo .env file created from .env.example
        echo IMPORTANT: Please edit .env and fill in your actual values!
    ) else (
        echo WARNING: .env.example not found
    )
)

REM ============================================
REM STEP 5: Setup Frontend
REM ============================================
echo.
echo [STEP 5/5] Setting up frontend...
echo.

cd web

echo Installing Node.js dependencies...
echo This may take several minutes...
echo.

call npm install
if errorlevel 1 (
    echo ERROR: Failed to install Node.js dependencies
    cd ..
    pause
    exit /b 1
)
echo Node.js dependencies installed successfully!

echo.
echo Setting up frontend environment variables...
echo.

if exist .env.local (
    echo .env.local file already exists. Skipping.
) else (
    if exist .env.example (
        copy .env.example .env.local
        echo .env.local file created from .env.example
        echo IMPORTANT: Please edit web\.env.local and fill in your actual values!
    ) else (
        echo WARNING: .env.example not found
    )
)

cd ..

REM ============================================
REM SETUP COMPLETE
REM ============================================
echo.
echo ================================================================================
echo                        SETUP COMPLETE!
echo ================================================================================
echo.
echo Next steps:
echo.
echo 1. Edit .env and fill in your database URL and API keys
echo 2. Edit web\.env.local and fill in your API URL and Clerk keys
echo 3. Make sure Ollama is installed and running (optional but recommended)
echo    - Download from: https://ollama.com/
echo    - Run: ollama pull qwen2.5:3b-instruct
echo.
echo 4. Start the backend server:
echo    - Run: start-backend.bat
echo    - Or manually: venv\Scripts\activate.bat then uvicorn src.api.main:app --reload --port 8000
echo.
echo 5. Start the frontend server (in a new terminal):
echo    - Run: start-frontend.bat
echo    - Or manually: cd web then npm run dev
echo.
echo 6. Open your browser and go to: http://localhost:3000
echo.
echo For detailed instructions, see STARTUP_GUIDE.txt
echo.
echo ================================================================================
pause
