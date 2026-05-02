# Fold AI - Setup Guide

## 🎯 Overview

Fold AI is a web-first financial tracking application with AI-powered expense extraction from:
- 📝 Text input
- 🎤 Voice recordings
- 📸 Receipt images

## 🔧 Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL database (Neon DB configured)
- Clerk account for authentication

## 📦 Installation

### 1. Backend Setup (FastAPI)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials (already configured)

# Run database migrations
python migrate_db.py

# Start the FastAPI server
uvicorn src.api.main:app --reload --port 8000
```

### 2. Frontend Setup (Next.js)

```bash
cd web

# Install dependencies
npm install

# Environment is already configured in .env.local

# Start the development server
npm run dev
```

The app will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🔐 Authentication

The app uses **Clerk** for authentication:

- **Publishable Key**: `pk_test_YXNzdXJlZC1idWxsZnJvZy04LmNsZXJrLmFjY291bnRzLmRldiQ`
- **Secret Key**: Configured in `.env`

### Clerk Setup

1. Users sign up at `/sign-up`
2. Users sign in at `/login`
3. Clerk automatically creates a user in the database on first login
4. Default accounts are created automatically:
   - Cash & Wallet
   - Primary Bank Account
   - Credit Card
   - Operating Expenses
   - Operating Income
   - Opening Balance Equity

## 🗄️ Database Schema

### Users Table
```sql
- id (BIGSERIAL PRIMARY KEY)
- external_user_ref (TEXT UNIQUE) -- Clerk user ID
- clerk_user_id (TEXT UNIQUE)
- email (TEXT)
- full_name (TEXT)
- avatar_url (TEXT)
- preferences_json (JSONB)
- created_at (TIMESTAMPTZ)
- updated_at (TIMESTAMPTZ)
```

### Key Changes from Telegram Version
- ✅ Removed Telegram-specific fields
- ✅ Added Clerk authentication fields
- ✅ Added email, full_name, avatar_url
- ✅ Kept flexible `external_user_ref` for compatibility

## 🚀 API Endpoints

### Extraction Endpoints (Clerk-authenticated)

#### POST `/api/v1/web/extract/text`
Extract transaction from text input.

**Headers:**
```
Authorization: Bearer <clerk_jwt_token>
Content-Type: application/json
```

**Body:**
```json
{
  "text": "Paid 450 rupees for Swiggy order via UPI"
}
```

**Response:**
```json
{
  "status": "success",
  "source": "text",
  "extracted_data": {
    "amount": 450.0,
    "category": "food_dining",
    "payment_method": "upi",
    "payment_provider": "swiggy"
  },
  "ledger_result": {
    "transaction_id": 123,
    "journal_id": 456
  },
  "message": "Saved food_dining expense of ₹450"
}
```

#### POST `/api/v1/web/extract/audio`
Extract transaction from voice recording.

**Headers:**
```
Authorization: Bearer <clerk_jwt_token>
```

**Body:** `multipart/form-data`
- `file`: Audio file (.ogg, .wav, .mp3, .m4a)

**Response:** Same as text endpoint, with added `transcript` field

#### POST `/api/v1/web/extract/image`
Extract transaction from receipt image.

**Headers:**
```
Authorization: Bearer <clerk_jwt_token>
```

**Body:** `multipart/form-data`
- `file`: Image file (.jpg, .png, .jpeg)

**Response:** Same as text endpoint, with added OCR fields

### Dashboard Endpoints

#### GET `/api/v1/web/dashboard?period=monthly`
Get dashboard data (requires Clerk session cookie).

#### GET `/api/v1/web/transactions?limit=50&offset=0`
Get transaction list (requires Clerk session cookie).

## 🎨 Frontend Components

### AI Prompt Box
Located at `web/src/components/ui/ai-prompt-box.tsx`

Features:
- Text input with auto-resize
- Image upload with drag & drop
- Voice recording with visualization
- Search/Think/Canvas modes (for future features)
- Real-time feedback

### Usage in Home Page
```typescript
import { PromptInputBox } from "@/components/ui/ai-prompt-box";

<PromptInputBox
  onSend={handleSendMessage}
  isLoading={isLoading}
  placeholder="Upload a receipt, record audio, or type your expense..."
/>
```

## 🔄 Data Flow

### Text Input Flow
1. User types expense in prompt box
2. Frontend calls `/api/v1/web/extract/text` with Clerk JWT
3. Backend verifies Clerk token
4. NLP extracts structured data
5. Expense saved to ledger
6. Success message shown to user

### Image Upload Flow
1. User uploads receipt image
2. Frontend calls `/api/v1/web/extract/image` with Clerk JWT
3. Backend verifies Clerk token
4. UPI logo detection (if enabled)
5. OCR extracts text
6. Ollama structures data (if enabled)
7. NLP categorizes transaction
8. Expense saved to ledger
9. Success message shown to user

### Voice Recording Flow
1. User records voice note
2. Frontend calls `/api/v1/web/extract/audio` with Clerk JWT
3. Backend verifies Clerk token
4. Whisper transcribes audio
5. NLP extracts structured data
6. Expense saved to ledger
7. Success message with transcript shown

## 🧪 Testing

### Test Text Extraction
```bash
curl -X POST http://localhost:8000/api/v1/web/extract/text \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Paid 500 for groceries"}'
```

### Test Image Extraction
```bash
curl -X POST http://localhost:8000/api/v1/web/extract/image \
  -H "Authorization: Bearer YOUR_CLERK_TOKEN" \
  -F "file=@receipt.jpg"
```

## 🐛 Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` in `.env`
- Check Neon DB is accessible
- Run `python migrate_db.py` to reset schema

### Clerk Authentication Issues
- Verify Clerk keys in `.env` and `web/.env.local`
- Check Clerk dashboard for application status
- Ensure middleware is configured in `web/src/middleware.ts`

### AI Model Issues
- **Whisper**: Requires ~1GB RAM, downloads on first use
- **PaddleOCR**: Requires ~500MB RAM, downloads on first use
- **Ollama**: Optional, requires local Ollama server running

## 📝 Environment Variables

### Backend (.env)
```bash
DATABASE_URL='postgresql://...'
CLERK_SECRET_KEY='sk_test_...'
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY='pk_test_...'
ROBOFLOW_API_KEY='...'  # Optional
OLLAMA_ENABLED=true  # Optional
```

### Frontend (web/.env.local)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY='pk_test_...'
CLERK_SECRET_KEY='sk_test_...'
```

## 🚀 Deployment

### Backend (FastAPI)
- Deploy to Railway, Render, or AWS
- Set environment variables
- Run migrations: `python migrate_db.py`
- Start with: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`

### Frontend (Next.js)
- Deploy to Vercel (recommended)
- Set environment variables in Vercel dashboard
- Update `NEXT_PUBLIC_API_BASE_URL` to production API URL

## 📚 Additional Resources

- [Clerk Documentation](https://clerk.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Neon DB Documentation](https://neon.tech/docs)

## 🎉 Success!

Your Fold AI application is now set up with:
- ✅ Clerk authentication
- ✅ Fresh Neon database
- ✅ AI-powered extraction endpoints
- ✅ Beautiful prompt box UI
- ✅ Automatic ledger posting

Start the servers and visit http://localhost:3000 to begin!
