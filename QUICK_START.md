# 🚀 Fold - Quick Start Guide

Get Fold up and running in 5 minutes!

## ⚡ First Time Setup (One-time only)

### Windows:
```bash
# Run the setup script
setup.bat

# Edit environment files with your values
notepad .env
notepad web\.env.local
```

### Linux/Mac:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
cd web && npm install && cd ..

# Setup environment files
cp .env.example .env
cp web/.env.example web/.env.local

# Edit with your values
nano .env
nano web/.env.local
```

## 🎯 Required Environment Variables

### `.env` (Backend)
```env
DATABASE_URL='postgresql://user:pass@host:port/db'
CLERK_SECRET_KEY='sk_test_...'
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY='pk_test_...'
```

### `web/.env.local` (Frontend)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY='pk_test_...'
CLERK_SECRET_KEY='sk_test_...'
```

## 🏃 Running the Application

### Option 1: Start Both Servers (Windows)
```bash
start-all.bat
```

### Option 2: Start Separately

**Terminal 1 - Backend:**
```bash
# Windows
start-backend.bat

# Linux/Mac
source venv/bin/activate
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
# Windows
start-frontend.bat

# Linux/Mac
cd web
npm run dev
```

## 🌐 Access the Application

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## 🧪 Test the Setup

```bash
# Make sure backend is running, then:
python test_extraction_pipelines.py
```

## 🛑 Stopping the Application

- Press `Ctrl+C` in each terminal window
- Or close the terminal windows

## 📦 Optional: Install Ollama (Recommended)

For better OCR text extraction:

1. Download from: https://ollama.com/
2. Install and run:
   ```bash
   ollama pull qwen2.5:3b-instruct
   ```

## 🆘 Common Issues

| Issue | Solution |
|-------|----------|
| "Module not found" | Run `pip install -r requirements.txt` |
| "Port already in use" | Change port: `--port 8001` |
| "Database connection failed" | Check `DATABASE_URL` in `.env` |
| "Clerk auth not working" | Verify Clerk keys match in both `.env` files |

## 📚 Need More Help?

- **Detailed Guide:** See `STARTUP_GUIDE.txt`
- **Scripts Info:** See `SCRIPTS_README.md`
- **Architecture:** See `PROJECT_OVERVIEW.md`
- **Full Docs:** See `README.md`

---

**That's it! You're ready to track expenses with Fold! 💰**
