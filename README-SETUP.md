# Fold - Setup Instructions

## Quick Start

### 1. Start the Backend API Server

The backend must be running for the web app to work.

**Option A: Using the batch file (Windows)**
```bash
start-backend.bat
```

**Option B: Manual start**
```bash
# Activate virtual environment (if using one)
venv\Scripts\activate

# Start the server
uvicorn src.api.main:app --reload --port 8000
```

The backend will be available at: http://localhost:8000

### 2. Start the Frontend (Next.js)

In a separate terminal:

```bash
cd web
npm run dev
```

The frontend will be available at: http://localhost:3000

## Troubleshooting

### "Failed to get user info" Error

This error means the backend API is not running. Make sure:

1. The backend server is started (see step 1 above)
2. It's running on port 8000
3. You can access http://localhost:8000/health in your browser

### Port Already in Use

If port 8000 or 3000 is already in use:

**Backend (port 8000):**
```bash
# Find and kill the process
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

**Frontend (port 3000):**
```bash
# Find and kill the process
netstat -ano | findstr :3000
taskkill /PID <process_id> /F
```

## Environment Variables

Make sure you have:

- `.env` in the root directory (for backend)
- `web/.env.local` (for frontend)

Both should be configured with the correct API URLs and Clerk keys.
