# 🚀 Quick Start Guide

## ⚡ Get Running in 3 Steps

### Step 1: Database Setup (30 seconds)
```bash
python migrate_db.py
```
✅ Creates fresh database with Clerk support

### Step 2: Start Backend (1 minute)
```bash
uvicorn src.api.main:app --reload --port 8000
```
✅ API running at http://localhost:8000

### Step 3: Start Frontend (1 minute)
```bash
cd web
npm run dev
```
✅ App running at http://localhost:3000

## 🎯 First Use

1. **Visit** http://localhost:3000
2. **Sign Up** with your email
3. **Try the prompt box:**
   - Type: `Paid 450 for Swiggy order`
   - Or upload a receipt image
4. **View Dashboard** to see your transaction

## 📋 What's Already Configured

✅ **Database**: Fresh Neon PostgreSQL instance  
✅ **Authentication**: Clerk with test credentials  
✅ **AI Models**: NLP, OCR, Whisper (download on first use)  
✅ **Default Accounts**: Created automatically on signup  
✅ **API Endpoints**: Text, image, audio extraction  
✅ **Frontend**: Next.js with Clerk integration  

## 🔑 Credentials

### Clerk (Already in .env)
- Publishable Key: `pk_test_YXNzdXJlZC1idWxsZnJvZy04LmNsZXJrLmFjY291bnRzLmRldiQ`
- Secret Key: `sk_test_6GaccAIEcFZuzs6nGOx4BbC3u4c99Ch5htfSvXTfrnplease`

### Database (Already in .env)
- Neon PostgreSQL (fresh instance)
- Connection string configured

## 📚 Documentation

- **SETUP.md** - Detailed setup instructions
- **IMPLEMENTATION_SUMMARY.md** - What was built
- **TEST_GUIDE.md** - Testing checklist

## 🆘 Need Help?

### Backend not starting?
```bash
pip install -r requirements.txt
```

### Frontend not starting?
```bash
cd web
npm install
```

### Database issues?
```bash
python migrate_db.py
```

## 🎉 You're Ready!

The app is fully functional with:
- ✅ Clerk authentication
- ✅ AI-powered extraction
- ✅ Automatic ledger posting
- ✅ Beautiful UI with prompt box
- ✅ Dashboard and analytics

**Start building your financial tracking app!** 🚀
