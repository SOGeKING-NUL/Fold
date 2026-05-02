# Testing Guide

## 🧪 Quick Test Checklist

### 1. Database Setup ✅
```bash
python migrate_db.py
```
Expected output:
```
Creating database schema with Clerk support...
✅ Database schema created successfully!
✅ Tables created: users, accounts, payment_profiles, journal_transactions, journal_media, ledger_entries, ingestion_events
✅ Clerk fields added: clerk_user_id, email, full_name, avatar_url
```

### 2. Start Backend
```bash
uvicorn src.api.main:app --reload --port 8000
```
Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

Visit http://localhost:8000/docs to see API documentation.

### 3. Start Frontend
```bash
cd web
npm run dev
```
Expected output:
```
▲ Next.js 16.2.3
- Local:        http://localhost:3000
```

## 🔐 Authentication Tests

### Test 1: Sign Up
1. Visit http://localhost:3000
2. You should be redirected to `/login` (Clerk middleware)
3. Click "Sign up" link
4. Create account with:
   - Email
   - Password
   - Or use Google/GitHub (if configured in Clerk)
5. After sign-up, you should be redirected to home page
6. Check database:
```sql
SELECT clerk_user_id, email, full_name FROM users;
```
You should see your new user!

### Test 2: Default Accounts Created
After signing up, check that default accounts were created:
```sql
SELECT code, name, account_type FROM accounts WHERE user_id = (SELECT id FROM users LIMIT 1);
```
Expected accounts:
- cash_wallet
- bank_primary
- credit_card
- expense_operating
- income_operating
- equity_opening_balance

### Test 3: Sign Out and Sign In
1. Click on your profile picture (top right)
2. Click "Sign out"
3. You should be redirected to `/login`
4. Sign in with your credentials
5. You should be back on the home page

## 💬 Text Extraction Tests

### Test 1: Simple Expense
1. Type in prompt box: `Paid 450 for Swiggy order`
2. Press Enter or click send button
3. Expected result:
   - Loading indicator appears
   - Success message: "Saved food_dining expense of ₹450"
4. Verify in database:
```sql
SELECT description, metadata_json->>'category', metadata_json->>'amount' 
FROM journal_transactions 
ORDER BY created_at DESC LIMIT 1;
```

### Test 2: Expense with Payment Method
1. Type: `Bought groceries for 1200 rupees using credit card`
2. Expected extraction:
   - Amount: 1200
   - Category: groceries
   - Payment method: credit_card
3. Check success message

### Test 3: UPI Payment
1. Type: `Paid 350 to PhonePe for electricity bill`
2. Expected extraction:
   - Amount: 350
   - Category: utilities
   - Payment method: upi
   - Provider: phonepe

## 📸 Image Extraction Tests

### Test 1: Upload Receipt
1. Click paperclip icon in prompt box
2. Select a receipt image (use one from project root: `receipt.jpg`, `receipt2.jpg`, etc.)
3. Image preview should appear
4. Click send button
5. Expected result:
   - Loading indicator
   - OCR processing
   - Success message with extracted amount and category
6. Verify in database

### Test 2: Drag and Drop
1. Drag a receipt image from your file explorer
2. Drop it on the prompt box
3. Image should appear in preview
4. Click send
5. Verify extraction

### Test 3: Paste Image
1. Copy an image to clipboard (Ctrl+C on an image file)
2. Click in the prompt box
3. Paste (Ctrl+V)
4. Image should appear
5. Click send
6. Verify extraction

## 🎤 Voice Recording Tests

### Test 1: Voice Input (Placeholder)
1. Click the microphone icon
2. Currently shows: "Voice recording feature coming soon!"
3. This is expected - browser recording needs to be implemented

### Future Voice Test (when implemented):
1. Click microphone icon
2. Speak: "I spent five hundred rupees on groceries"
3. Click stop
4. Should transcribe and extract
5. Should save to ledger

## 📊 Dashboard Tests

### Test 1: View Dashboard
1. Click "View Dashboard" button in header
2. Should navigate to `/dashboard`
3. Should show:
   - Summary cards (income, expenses, net)
   - Charts (daily trend, category breakdown)
   - Recent transactions
   - Account balances

### Test 2: Period Toggle
1. On dashboard, toggle between "Weekly" and "Monthly"
2. Data should update
3. Charts should refresh

### Test 3: View All Transactions
1. On dashboard, scroll to transactions table
2. Click "View All"
3. Should navigate to `/transactions`
4. Should show full transaction list

## 🔍 API Direct Tests (with cURL)

### Get Clerk Token
1. Sign in to the web app
2. Open browser DevTools (F12)
3. Go to Application > Cookies
4. Find `__session` cookie (Clerk session)
5. Or use: `await clerk.session.getToken()` in console

### Test Text Extraction
```bash
curl -X POST http://localhost:8000/api/v1/web/extract/text \
  -H "Authorization: Bearer YOUR_CLERK_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Paid 500 for groceries"}'
```

Expected response:
```json
{
  "status": "success",
  "source": "text",
  "extracted_data": {
    "amount": 500.0,
    "category": "groceries",
    "payment_method": null,
    "payment_provider": null
  },
  "ledger_result": {
    "transaction_id": 1,
    "journal_id": 1
  },
  "message": "Saved groceries expense of ₹500"
}
```

### Test Image Extraction
```bash
curl -X POST http://localhost:8000/api/v1/web/extract/image \
  -H "Authorization: Bearer YOUR_CLERK_JWT_TOKEN" \
  -F "file=@receipt.jpg"
```

## 🐛 Common Issues

### Issue: "Authentication required"
**Solution:** 
- Make sure you're signed in
- Check Clerk keys in `.env` and `web/.env.local`
- Verify middleware is working

### Issue: "Database connection failed"
**Solution:**
- Check `DATABASE_URL` in `.env`
- Verify Neon DB is accessible
- Run `python migrate_db.py` again

### Issue: "Module not found" errors
**Solution:**
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd web
npm install
```

### Issue: OCR/Whisper not working
**Solution:**
- First run downloads models (~1-2GB)
- Ensure sufficient disk space
- Check internet connection for downloads

### Issue: Ollama not working
**Solution:**
- Ollama is optional
- Set `OLLAMA_ENABLED=false` in `.env` to disable
- Or install Ollama: https://ollama.ai/

## ✅ Success Criteria

After all tests, you should have:
- ✅ User account created in database
- ✅ Default accounts created
- ✅ At least 3 transactions from text input
- ✅ At least 1 transaction from image upload
- ✅ Dashboard showing data
- ✅ Charts rendering correctly
- ✅ No console errors

## 📝 Test Results Template

```
Date: ___________
Tester: ___________

✅ Database migration successful
✅ Backend starts without errors
✅ Frontend starts without errors
✅ Sign up works
✅ Sign in works
✅ Default accounts created
✅ Text extraction works
✅ Image extraction works
✅ Dashboard loads
✅ Transactions display correctly

Issues found:
1. ___________
2. ___________

Notes:
___________
```

## 🎉 Ready to Test!

Follow the checklist above and report any issues. Good luck! 🚀
