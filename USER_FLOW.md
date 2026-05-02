# 👤 User Flow Guide

## 🎬 Complete User Journey

### Scenario 1: Brand New User

#### Step 1: Landing Page
```
User visits: http://localhost:3000
↓
Clerk middleware detects: Not authenticated
↓
Redirects to: /login
```

#### Step 2: Sign Up
```
User clicks: "Sign up"
↓
Enters: Email + Password (or Google/GitHub)
↓
Clerk creates account
↓
Redirects to: Home page (/)
```

#### Step 3: First Expense Attempt
```
User sees: AI Prompt Box + 3 Action Cards
↓
User types: "Paid 450 for Swiggy order"
↓
Presses: Enter
↓
Backend extracts: {amount: 450, category: "food_dining"}
↓
Backend checks: Does user have payment accounts?
↓
Result: NO payment accounts found
↓
Shows message: "Found food_dining expense of ₹450. 
               Please add a payment method first."
↓
Shows button: "Add Payment Method"
```

#### Step 4: Add Payment Method
```
User clicks: "Add Payment Method" button
↓
Navigates to: /accounts page
↓
User sees: Empty state with "Add Payment Method" button
↓
User clicks: "Add Payment Method"
↓
Form appears with fields:
  - Account Type: [Bank Account / Credit Card / Wallet]
  - Account Name: "HDFC Savings"
  - Institution: "HDFC Bank"
  - Last 4 digits: "1234"
  - Digital: ✓ checked
↓
User clicks: "Add Account"
↓
Account created in database
↓
Shows in list with green "Asset" badge
```

#### Step 5: Try Expense Again
```
User clicks: Back button or navigates to home
↓
User types: "Paid 450 for Swiggy order"
↓
Backend extracts: {amount: 450, category: "food_dining"}
↓
Backend checks: Does user have payment accounts?
↓
Result: YES - found "HDFC Savings"
↓
Transaction saved to ledger:
  - Debit: expense_operating (₹450)
  - Credit: hdfc_savings (₹450)
↓
Shows message: "Saved food_dining expense of ₹450" ✅
```

#### Step 6: View Dashboard
```
User clicks: "View Reports" action card
↓
Navigates to: /dashboard
↓
Sees:
  - Total Expenses: ₹450
  - Total Income: ₹0
  - Net: -₹450
  - Chart showing food_dining category
  - Recent transaction: "Paid 450 for Swiggy order"
```

---

### Scenario 2: Returning User (Has Accounts)

#### Step 1: Sign In
```
User visits: http://localhost:3000
↓
Redirects to: /login
↓
User enters: Email + Password
↓
Clerk authenticates
↓
Redirects to: Home page (/)
```

#### Step 2: Add Expense (Smooth!)
```
User types: "Bought groceries for 1200"
↓
Backend extracts: {amount: 1200, category: "groceries"}
↓
Backend checks: User has payment accounts ✓
↓
Transaction saved automatically
↓
Shows message: "Saved groceries expense of ₹1200" ✅
```

#### Step 3: Upload Receipt
```
User clicks: Paperclip icon
↓
Selects: receipt.jpg
↓
Image preview appears
↓
User clicks: Send button
↓
Backend processes:
  1. UPI logo detection
  2. OCR text extraction
  3. Ollama structuring
  4. NLP categorization
↓
Extracts: {amount: 850, category: "shopping", method: "upi"}
↓
Transaction saved
↓
Shows message: "Saved shopping expense of ₹850" ✅
```

---

### Scenario 3: Power User (Multiple Accounts)

#### Step 1: Manage Accounts
```
User navigates to: /accounts
↓
Sees existing accounts:
  - HDFC Savings (Asset) - ₹25,000
  - ICICI Credit Card (Liability) - ₹5,000
  - Paytm Wallet (Asset) - ₹500
↓
User clicks: "Add Payment Method"
↓
Adds: "SBI Fixed Deposit" (Investment)
↓
Now has 4 payment accounts
```

#### Step 2: Add Expense with Specific Method
```
User types: "Paid 2000 for rent using HDFC"
↓
Backend extracts: {
  amount: 2000,
  category: "rent",
  payment_method: "bank_transfer",
  bank_account: "hdfc"
}
↓
Transaction saved with HDFC account
↓
HDFC balance: ₹25,000 → ₹23,000
```

#### Step 3: View Breakdown
```
User navigates to: /dashboard
↓
Clicks: Period toggle → "Monthly"
↓
Sees breakdown:
  - By Category: Food ₹450, Groceries ₹1200, Rent ₹2000
  - By Payment Method: HDFC ₹2000, Paytm ₹450, etc.
  - By Account: HDFC -₹2000, Paytm -₹450
↓
Sees account balances:
  - HDFC Savings: ₹23,000
  - ICICI Credit Card: ₹5,000
  - Paytm Wallet: ₹50
```

---

## 🎨 UI Elements

### Home Page
```
┌─────────────────────────────────────────────┐
│  [Logo] Fold AI          [Dashboard] [👤]  │
├─────────────────────────────────────────────┤
│                                             │
│        Your AI Financial Assistant          │
│   Upload receipts, record voice notes...    │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  [📎] Type your message...      [🎤]  │ │
│  │                                 [↑]   │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │ 💳 Add  │  │ 📊 View │  │ 📝 All  │   │
│  │ Payment │  │ Reports │  │ Trans.  │   │
│  └─────────┘  └─────────┘  └─────────┘   │
│                                             │
│  📸 Image  🎤 Voice  🤖 AI  📊 Analytics   │
└─────────────────────────────────────────────┘
```

### Accounts Page
```
┌─────────────────────────────────────────────┐
│  [←] Payment Methods              [👤]      │
├─────────────────────────────────────────────┤
│                                             │
│  [+ Add Payment Method]                     │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ HDFC Savings          [Asset] 🟢      │ │
│  │ 🏦 HDFC Bank  •••• 1234  Digital      │ │
│  │                          ₹25,000      │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ ICICI Credit Card  [Liability] 🔴     │ │
│  │ 🏦 ICICI Bank  •••• 5678  Digital     │ │
│  │                           ₹5,000      │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ Paytm Wallet          [Asset] 🟢      │ │
│  │ 🏦 Paytm  Digital                     │ │
│  │                             ₹500      │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Add Account Form
```
┌─────────────────────────────────────────────┐
│  Add New Payment Method                     │
├─────────────────────────────────────────────┤
│                                             │
│  Account Type:                              │
│  [Bank Account / Cash / Wallet ▼]           │
│                                             │
│  Account Name: *                            │
│  [HDFC Savings Account_____________]        │
│                                             │
│  Institution Name:                          │
│  [HDFC Bank____________________]            │
│                                             │
│  Last 4 Digits:                             │
│  [1234]                                     │
│                                             │
│  ☑ Digital payment method                  │
│                                             │
│  [Add Account]  [Cancel]                    │
└─────────────────────────────────────────────┘
```

---

## 🔄 State Transitions

### User State Machine
```
[New User]
    ↓
[Sign Up] → [Authenticated]
    ↓
[No Accounts] → [Try Expense] → [Blocked]
    ↓
[Add Account] → [Has Accounts]
    ↓
[Try Expense] → [Success] → [View Dashboard]
```

### Transaction State Machine
```
[User Input]
    ↓
[Extract Data] → [Has Amount?]
    ↓ Yes
[Check Accounts] → [Has Payment Method?]
    ↓ Yes              ↓ No
[Save to Ledger]   [Show Message]
    ↓                  ↓
[Success]          [Redirect to /accounts]
```

---

## 📱 Responsive Behavior

### Mobile (< 768px)
- Action cards: 1 column (stacked)
- Prompt box: Full width
- Feature pills: Wrap to multiple rows
- Account cards: Full width

### Tablet (768px - 1024px)
- Action cards: 2 columns
- Prompt box: Full width
- Feature pills: Single row

### Desktop (> 1024px)
- Action cards: 3 columns
- Prompt box: Max width 3xl
- Feature pills: Single row
- Account cards: Full width with side-by-side info

---

## 🎯 Key User Actions

### Primary Actions
1. **Add Expense** - Type in prompt box
2. **Upload Receipt** - Click paperclip or drag & drop
3. **Add Payment Method** - Navigate to /accounts
4. **View Dashboard** - Click "View Reports"

### Secondary Actions
1. **View Transactions** - Click "All Transactions"
2. **Sign Out** - Click profile picture → Sign out
3. **Edit Account** - (Future feature)
4. **Delete Account** - (Future feature)

---

## ✅ Success Indicators

### User knows they're successful when:
- ✅ Green success message appears
- ✅ Transaction shows in dashboard
- ✅ Account balance updates
- ✅ Chart reflects new data

### User knows they need action when:
- ⚠️ "Please add payment method" message
- ⚠️ Button to add payment method appears
- ⚠️ Empty state on accounts page

---

## 🎉 Complete Flow Summary

```
Sign Up → Add Account → Add Expense → View Dashboard → Success! 🎉
```

That's it! Simple, intuitive, and powerful. 🚀
