# Fold - Helper Scripts

This directory contains several helper scripts to make it easier to set up and run the Fold application.

## 📋 Available Scripts

### 🔧 Setup Scripts

#### `setup.bat` (Windows)
**First-time setup script** - Run this once when you first clone the repository.

**What it does:**
1. Creates Python virtual environment
2. Installs Python dependencies from `requirements.txt`
3. Creates `.env` file from `.env.example`
4. Installs Node.js dependencies in the `web` directory
5. Creates `web/.env.local` file from `web/.env.example`

**Usage:**
```bash
setup.bat
```

**After running:**
- Edit `.env` and fill in your database URL and API keys
- Edit `web/.env.local` and fill in your API URL and Clerk keys

---

### 🚀 Startup Scripts

#### `start-backend.bat` (Windows)
Starts the FastAPI backend server.

**What it does:**
1. Activates the Python virtual environment
2. Starts uvicorn server on port 8000

**Usage:**
```bash
start-backend.bat
```

**Server will be available at:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

#### `start-frontend.bat` (Windows)
Starts the Next.js frontend server.

**What it does:**
1. Navigates to the `web` directory
2. Starts Next.js development server

**Usage:**
```bash
start-frontend.bat
```

**Server will be available at:**
- Frontend: http://localhost:3000

---

#### `start-all.bat` (Windows)
Starts both backend and frontend servers in separate windows.

**What it does:**
1. Opens a new terminal window for the backend server
2. Opens a new terminal window for the frontend server
3. Both servers start automatically

**Usage:**
```bash
start-all.bat
```

**Servers will be available at:**
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

**To stop:**
- Close both terminal windows, or press Ctrl+C in each window

---

## 📝 Manual Commands

If you prefer to run commands manually or are on Linux/Mac:

### Backend (from project root):
```bash
# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
.\venv\Scripts\activate.bat

# Linux/Mac:
source venv/bin/activate

# Start server
uvicorn src.api.main:app --reload --port 8000
```

### Frontend (from project root):
```bash
cd web
npm run dev
```

---

## 🔍 Environment Files

### `.env.example` (Backend)
Template for backend environment variables. Copy to `.env` and fill in:
- `DATABASE_URL` - PostgreSQL connection string
- `ROBOFLOW_API_KEY` - For UPI logo detection
- `CLERK_SECRET_KEY` - Clerk authentication
- `OLLAMA_ENABLED` - Enable/disable Ollama LLM

### `web/.env.example` (Frontend)
Template for frontend environment variables. Copy to `web/.env.local` and fill in:
- `NEXT_PUBLIC_API_BASE_URL` - Backend API URL (usually http://localhost:8000)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Clerk public key
- `CLERK_SECRET_KEY` - Clerk secret key

---

## 🐧 Linux/Mac Users

For Linux/Mac users, you can create similar shell scripts:

### setup.sh
```bash
#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cd web
npm install
cp .env.example .env.local
cd ..
echo "Setup complete! Edit .env and web/.env.local with your values."
```

### start-backend.sh
```bash
#!/bin/bash
source venv/bin/activate
uvicorn src.api.main:app --reload --port 8000
```

### start-frontend.sh
```bash
#!/bin/bash
cd web
npm run dev
```

Make them executable:
```bash
chmod +x setup.sh start-backend.sh start-frontend.sh
```

---

## 📚 Additional Resources

- **STARTUP_GUIDE.txt** - Comprehensive startup guide with troubleshooting
- **README.md** - Full project documentation
- **PROJECT_OVERVIEW.md** - Architecture and system design
- **requirements.txt** - Python dependencies
- **web/package.json** - Node.js dependencies

---

## 🆘 Troubleshooting

### "Virtual environment not found"
Run `setup.bat` first to create the virtual environment.

### "Module not found" errors
Make sure you've run `setup.bat` or manually installed dependencies:
```bash
pip install -r requirements.txt
cd web && npm install
```

### "Port already in use"
Change the port in the startup command:
```bash
uvicorn src.api.main:app --reload --port 8001
```

### "Database connection failed"
Check your `DATABASE_URL` in `.env` is correct.

---

## 📞 Support

For detailed setup instructions and troubleshooting, see **STARTUP_GUIDE.txt**.
