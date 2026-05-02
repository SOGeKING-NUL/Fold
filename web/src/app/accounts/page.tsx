"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth, UserButton } from "@clerk/nextjs";

interface Account {
  id: number;
  code: string;
  name: string;
  account_type: string;
  institution_name?: string;
  account_number_last4?: string;
  is_digital: boolean;
  balance_minor?: number;
}

export default function AccountsPage() {
  const router = useRouter();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    account_type: "asset",
    institution_name: "",
    account_number_last4: "",
    is_digital: true,
  });

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      fetchAccounts();
    }
  }, [isLoaded, isSignedIn]);

  const fetchAccounts = async () => {
    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      
      // Get user info first
      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        credentials: "include",
      });
      
      if (!userResponse.ok) throw new Error("Failed to get user info");
      
      const userData = await userResponse.json();
      const userRef = userData.user_ref;

      // Get accounts
      const accountsResponse = await fetch(`${API_BASE}/api/v1/ledger/accounts/${userRef}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!accountsResponse.ok) throw new Error("Failed to fetch accounts");

      const data = await accountsResponse.json();
      setAccounts(data.accounts || []);
    } catch (error) {
      console.error("Error fetching accounts:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      
      // Get user info
      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        credentials: "include",
      });
      
      if (!userResponse.ok) throw new Error("Failed to get user info");
      
      const userData = await userResponse.json();
      const userRef = userData.user_ref;

      // Generate code from name
      const code = formData.name.toLowerCase().replace(/[^a-z0-9]/g, "_");

      // Create account
      const response = await fetch(`${API_BASE}/api/v1/ledger/accounts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_ref: userRef,
          code,
          name: formData.name,
          account_type: formData.account_type,
          institution_name: formData.institution_name || null,
          account_number_last4: formData.account_number_last4 || null,
          is_digital: formData.is_digital,
          currency: "INR",
        }),
      });

      if (!response.ok) throw new Error("Failed to create account");

      // Reset form and refresh
      setFormData({
        name: "",
        account_type: "asset",
        institution_name: "",
        account_number_last4: "",
        is_digital: true,
      });
      setShowAddForm(false);
      fetchAccounts();
    } catch (error) {
      console.error("Error adding account:", error);
      alert("Failed to add account. Please try again.");
    }
  };

  const getAccountTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      asset: "Asset",
      liability: "Liability",
      expense: "Expense",
      income: "Income",
      equity: "Equity",
      investment: "Investment",
    };
    return labels[type] || type;
  };

  const getAccountTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      asset: "bg-green-500/10 text-green-400 border-green-500/20",
      liability: "bg-red-500/10 text-red-400 border-red-500/20",
      expense: "bg-orange-500/10 text-orange-400 border-orange-500/20",
      income: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      equity: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      investment: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    };
    return colors[type] || "bg-gray-500/10 text-gray-400 border-gray-500/20";
  };

  if (!isLoaded || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-black flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-black font-sans">
      {/* Header */}
      <header className="w-full px-6 py-4 flex items-center justify-between border-b border-gray-800/50">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/")}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-xl font-semibold text-white">Payment Methods</h1>
        </div>
        <UserButton afterSignOutUrl="/" />
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Add Account Button */}
        <div className="mb-6">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Payment Method
          </button>
        </div>

        {/* Add Account Form */}
        {showAddForm && (
          <div className="mb-6 p-6 bg-gray-800/50 border border-gray-700/50 rounded-2xl">
            <h2 className="text-lg font-semibold text-white mb-4">Add New Payment Method</h2>
            <form onSubmit={handleAddAccount} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Account Type
                </label>
                <select
                  value={formData.account_type}
                  onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="asset">Bank Account / Cash / Wallet</option>
                  <option value="liability">Credit Card / Loan</option>
                  <option value="investment">Investment Account</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Account Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., HDFC Savings, Paytm Wallet, ICICI Credit Card"
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Institution Name (Optional)
                </label>
                <input
                  type="text"
                  value={formData.institution_name}
                  onChange={(e) => setFormData({ ...formData, institution_name: e.target.value })}
                  placeholder="e.g., HDFC Bank, Paytm, ICICI"
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Last 4 Digits (Optional)
                </label>
                <input
                  type="text"
                  value={formData.account_number_last4}
                  onChange={(e) => setFormData({ ...formData, account_number_last4: e.target.value.slice(0, 4) })}
                  placeholder="e.g., 1234"
                  maxLength={4}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_digital"
                  checked={formData.is_digital}
                  onChange={(e) => setFormData({ ...formData, is_digital: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-700 bg-gray-900 text-blue-500 focus:ring-blue-500"
                />
                <label htmlFor="is_digital" className="text-sm text-gray-300">
                  Digital payment method (UPI, Card, Wallet)
                </label>
              </div>

              <div className="flex gap-3">
                <button
                  type="submit"
                  className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
                >
                  Add Account
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Accounts List */}
        <div className="space-y-3">
          {accounts.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-800/50 flex items-center justify-center">
                <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
              <p className="text-gray-400 mb-4">No payment methods added yet</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="text-blue-400 hover:text-blue-300 transition-colors"
              >
                Add your first payment method
              </button>
            </div>
          ) : (
            accounts.map((account) => (
              <div
                key={account.id}
                className="p-4 bg-gray-800/30 border border-gray-700/50 rounded-xl hover:border-gray-600/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-white">{account.name}</h3>
                      <span className={`px-2 py-1 rounded-md text-xs font-medium border ${getAccountTypeColor(account.account_type)}`}>
                        {getAccountTypeLabel(account.account_type)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-400">
                      {account.institution_name && (
                        <span>{account.institution_name}</span>
                      )}
                      {account.account_number_last4 && (
                        <span>.... {account.account_number_last4}</span>
                      )}
                      {account.is_digital && (
                        <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-xs">
                          Digital
                        </span>
                      )}
                    </div>
                  </div>
                  {account.balance_minor !== undefined && (
                    <div className="text-right">
                      <div className="text-2xl font-bold text-white">
                        ₹{(account.balance_minor / 100).toLocaleString("en-IN")}
                      </div>
                      <div className="text-xs text-gray-400">Current Balance</div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
