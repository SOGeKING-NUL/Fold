"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth, UserButton } from "@clerk/nextjs";

interface Account {
  id: number;
  name: string;
  account_type: string;
  institution_name?: string;
  account_number_last4?: string;
  balance?: number;
  is_default?: boolean;
}

interface PaymentProfile {
  id: number;
  profile_name: string;
  provider: string;
  linked_account_name: string;
}

export default function AccountsPage() {
  const router = useRouter();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [profiles, setProfiles] = useState<PaymentProfile[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);

  const fetchAccounts = async () => {
    try {
      const token = await getToken();
      if (!token) return;
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      
      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!userResponse.ok) throw new Error("Failed to get user info");
      
      const userData = await userResponse.json();
      const userRef = userData.user_ref;

      const accountsResponse = await fetch(`${API_BASE}/api/v1/ledger/accounts/${userRef}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!accountsResponse.ok) throw new Error("Failed to fetch accounts");

      const data = await accountsResponse.json();
      setAccounts(data.accounts || []);

      const profilesResponse = await fetch(`${API_BASE}/api/v1/ledger/payment-profiles/${userRef}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (profilesResponse.ok) {
        const profData = await profilesResponse.json();
        setProfiles(profData.profiles || []);
      }
    } catch (error) {
      console.error("Error fetching accounts:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      fetchAccounts();
    }
  }, [isLoaded, isSignedIn]);

  if (!isLoaded || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-black flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  const handleOpenAdd = () => {
    setEditingAccount(null);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (account: Account) => {
    setEditingAccount(account);
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
    setEditingAccount(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-black font-sans">
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
          <h1 className="text-xl font-semibold text-white">Payment Methods & Accounts</h1>
        </div>
        <UserButton afterSignOutUrl="/" />
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {!isFormOpen && (
          <div className="mb-6 flex justify-between items-center">
            <h2 className="text-lg text-gray-300">Your Accounts</h2>
            <button
              onClick={handleOpenAdd}
              className="px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add New Account
            </button>
          </div>
        )}

        {isFormOpen && (
          <AccountForm
            initialData={editingAccount}
            onClose={closeForm}
            onSuccess={() => {
              closeForm();
              fetchAccounts();
            }}
          />
        )}

        {!isFormOpen && (
          <>
            <div className="space-y-4 mb-12">
              {accounts.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-400 mb-4">No accounts added yet.</p>
                  <button onClick={handleOpenAdd} className="text-blue-400 hover:text-blue-300 transition-colors">
                    Setup your first account
                  </button>
                </div>
              ) : (
                accounts.map((acc) => (
                  <AccountCard key={acc.id} account={acc} onEdit={() => handleOpenEdit(acc)} onRefresh={fetchAccounts} />
                ))
              )}
            </div>

            <div className="mb-6 flex justify-between items-center">
              <h2 className="text-lg text-gray-300">Linked Payment Apps (UPI)</h2>
            </div>
            
            <PaymentProfilesSection profiles={profiles} accounts={accounts} onRefresh={fetchAccounts} />
          </>
        )}
      </main>
    </div>
  );
}

// ----------------------------------------------------------------------
// Payment Profiles Section
// ----------------------------------------------------------------------
function PaymentProfilesSection({ profiles, accounts, onRefresh }: { profiles: PaymentProfile[], accounts: Account[], onRefresh: () => void }) {
  const { getToken } = useAuth();
  const [isLinking, setIsLinking] = useState(false);
  const [provider, setProvider] = useState("gpay");
  const [profileName, setProfileName] = useState("");
  const [linkedAccount, setLinkedAccount] = useState("");
  
  const handleLink = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!linkedAccount) return alert("Select an account to link to.");

    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      
      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const userData = await userResponse.json();

      const res = await fetch(`${API_BASE}/api/v1/ledger/payment-profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          user_ref: userData.user_ref,
          provider: provider,
          profile_name: profileName || `${provider} default`,
          linked_account_name: linkedAccount,
        }),
      });

      if (!res.ok) throw new Error("Failed to link profile");
      
      setIsLinking(false);
      setProfileName("");
      setLinkedAccount("");
      onRefresh();
    } catch (err) {
      console.error(err);
      alert("Failed to link profile.");
    }
  };

  return (
    <div className="space-y-4">
      {profiles.map(p => (
        <div key={p.id} className="p-4 bg-gray-800/40 border border-gray-700/50 rounded-2xl flex justify-between items-center">
          <div>
            <h3 className="text-white font-medium capitalize">{p.provider}</h3>
            <p className="text-sm text-gray-400">{p.profile_name}</p>
          </div>
          <div className="text-right">
            <span className="text-xs text-gray-400 block mb-1">Linked to</span>
            <span className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs border border-blue-500/20">
              {p.linked_account_name}
            </span>
          </div>
        </div>
      ))}

      {!isLinking ? (
        <button
          onClick={() => setIsLinking(true)}
          className="w-full p-4 border border-dashed border-gray-700 rounded-2xl text-gray-400 hover:text-white hover:border-gray-500 transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Link UPI / Payment App
        </button>
      ) : (
        <form onSubmit={handleLink} className="p-5 bg-gray-800/50 border border-gray-700/50 rounded-2xl space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Provider</label>
              <select
                value={provider}
                onChange={e => setProvider(e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="gpay">Google Pay</option>
                <option value="phonepe">PhonePe</option>
                <option value="paytm">Paytm</option>
                <option value="cred">CRED</option>
                <option value="amazon_pay">Amazon Pay</option>
                <option value="bhim">BHIM</option>
                <option value="other">Other UPI</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Profile Name</label>
              <input
                type="text"
                value={profileName}
                onChange={e => setProfileName(e.target.value)}
                placeholder="e.g. Personal GPay"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Link to Bank Account</label>
              <select
                required
                value={linkedAccount}
                onChange={e => setLinkedAccount(e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">Select Account...</option>
                {accounts.filter(a => a.account_type === "bank").map(a => (
                  <option key={a.id} value={a.name}>{a.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={() => setIsLinking(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors">
              Cancel
            </button>
            <button type="submit" className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors">
              Link App
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
// Account Card Component
// ----------------------------------------------------------------------
function AccountCard({ account, onEdit, onRefresh }: { account: Account; onEdit: () => void; onRefresh: () => void }) {
  const { getToken } = useAuth();
  const [isAddingFunds, setIsAddingFunds] = useState(false);
  const [fundAmount, setFundAmount] = useState("");

  const handleAddFunds = async (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseFloat(fundAmount);
    if (isNaN(val) || val <= 0) {
      alert("Please enter a valid positive amount.");
      return;
    }

    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      
      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const userData = await userResponse.json();

      const res = await fetch(`${API_BASE}/api/v1/ledger/opening-balance`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          user_ref: userData.user_ref,
          account_name: account.name,
          amount: val,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to add funds");
      }
      
      setIsAddingFunds(false);
      setFundAmount("");
      onRefresh();
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to add funds.");
    }
  };

  const handleSetDefault = async () => {
    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      
      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const userData = await userResponse.json();

      const res = await fetch(
        `${API_BASE}/api/v1/ledger/accounts/${userData.user_ref}/set-default?account_name=${encodeURIComponent(account.name)}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to set default");
      }
      
      onRefresh();
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to set as default.");
    }
  };

  const typeColors: Record<string, string> = {
    cash: "bg-green-500/10 text-green-400 border-green-500/20",
    bank: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    credit: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  };

  const balance = account.balance !== undefined ? account.balance / 100 : 0;
  const isNegative = balance < 0;

  return (
    <div className="p-5 bg-gray-800/40 border border-gray-700/50 rounded-2xl hover:border-gray-600/50 transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-lg font-semibold text-white">{account.name}</h3>
            <span className={`px-2 py-1 rounded-md text-xs font-medium border ${typeColors[account.account_type] || typeColors.asset}`}>
              {account.account_type.charAt(0).toUpperCase() + account.account_type.slice(1)}
            </span>
            {account.is_default && (
              <span className="px-2 py-1 rounded-md text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                Default
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-400">
            {account.institution_name && account.account_type !== "cash" && <span>{account.institution_name}</span>}
            {account.account_number_last4 && <span>•••• {account.account_number_last4}</span>}
          </div>
        </div>

        <div className="flex flex-col items-start sm:items-end gap-3">
          {account.balance !== undefined && (
            <div className="text-left sm:text-right">
              <div className={`text-2xl font-bold ${isNegative ? 'text-red-400' : 'text-white'}`}>
                ₹{balance.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Current Balance</div>
            </div>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            {!account.is_default && (
              <button 
                onClick={handleSetDefault} 
                className="text-xs px-3 py-1.5 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border border-yellow-500/20 rounded-lg transition-colors"
              >
                Set as Default
              </button>
            )}
            <button onClick={onEdit} className="text-xs px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors">
              Edit
            </button>
            {account.account_type !== "credit" && !isAddingFunds && (
              <button onClick={() => setIsAddingFunds(true)} className="text-xs px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors">
                Add Funds
              </button>
            )}
          </div>
        </div>
      </div>

      {isAddingFunds && (
        <form onSubmit={handleAddFunds} className="mt-4 p-4 bg-gray-900/50 rounded-xl border border-gray-700 flex items-end gap-3">
          <div className="flex-1 max-w-xs">
            <label className="block text-xs text-gray-400 mb-1">Amount to Add (₹)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              value={fundAmount}
              onChange={(e) => setFundAmount(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g. 5000"
            />
          </div>
          <button type="submit" className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors">
            Confirm
          </button>
          <button type="button" onClick={() => setIsAddingFunds(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors">
            Cancel
          </button>
        </form>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
// Account Form Component (Add / Edit)
// ----------------------------------------------------------------------
function AccountForm({ initialData, onClose, onSuccess }: { initialData: Account | null; onClose: () => void; onSuccess: () => void }) {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const isEditing = !!initialData;

  const [formData, setFormData] = useState({
    name: initialData?.name || "",
    account_type: initialData?.account_type || "bank",
    institution_name: initialData?.institution_name || "",
    account_number_last4: initialData?.account_number_last4 || "",
    initial_amount: "", // Only used for new accounts
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      
      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!userResponse.ok) throw new Error("Failed to get user info");
      const userData = await userResponse.json();
      const userRef = userData.user_ref;

      // For cash wallets, use a default name if none provided
      const accountName = formData.name.trim() || (formData.account_type === "cash" ? "Cash Wallet" : "");
      if (!accountName) {
        alert("Please provide an account name.");
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_BASE}/api/v1/ledger/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          user_ref: userRef,
          name: accountName,
          account_type: formData.account_type,
          institution_name: formData.account_type === "cash" ? null : (formData.institution_name || null),
          account_number_last4: formData.account_type === "cash" ? null : (formData.account_number_last4 || null),
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to save account");
      }

      // Set initial amount if this is a new account and amount was provided
      if (!isEditing && formData.initial_amount && parseFloat(formData.initial_amount) > 0) {
        await fetch(`${API_BASE}/api/v1/ledger/opening-balance`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            user_ref: userRef,
            account_name: accountName,
            amount: parseFloat(formData.initial_amount),
          }),
        });
      }

      onSuccess();
    } catch (error: any) {
      console.error(error);
      alert(error.message || "An error occurred while saving the account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-800/50 border border-gray-700/50 rounded-2xl">
      <h2 className="text-xl font-bold text-white mb-6">
        {isEditing ? "Edit Account" : "Add New Account"}
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Account Type</label>
            <select
              value={formData.account_type}
              onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
              className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-blue-500"
              disabled={isEditing} // Cannot change type easily after creation
            >
              <option value="bank">Bank Account</option>
              <option value="cash">Cash Wallet</option>
              <option value="credit">Credit Card</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {formData.account_type === "cash" ? "Nickname (Optional)" : "Account Name *"}
            </label>
            <input
              type="text"
              required={formData.account_type !== "cash"}
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder={
                formData.account_type === "cash" 
                  ? "e.g. My Cash, Wallet" 
                  : "e.g. HDFC Checking, ICICI Credit"
              }
              className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {formData.account_type !== "cash" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Institution (Optional)</label>
                <input
                  type="text"
                  value={formData.institution_name}
                  onChange={(e) => setFormData({ ...formData, institution_name: e.target.value })}
                  placeholder="e.g. HDFC, ICICI, Paytm"
                  className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Last 4 Digits (Optional)</label>
                <input
                  type="text"
                  maxLength={4}
                  value={formData.account_number_last4}
                  onChange={(e) => setFormData({ ...formData, account_number_last4: e.target.value.replace(/\D/g, '') })}
                  placeholder="e.g. 1234"
                  className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </>
          )}
        </div>

        {!isEditing && formData.account_type !== "credit" && (
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {formData.account_type === "cash" ? "Current Cash Amount (₹)" : "Initial Balance / Opening Amount (₹)"}
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.initial_amount}
              onChange={(e) => setFormData({ ...formData, initial_amount: e.target.value })}
              placeholder="e.g. 5000"
              className="w-full px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-blue-500 max-w-sm"
            />
            <p className="text-xs text-gray-500 mt-2">
              {formData.account_type === "cash" 
                ? "How much cash do you currently have?" 
                : "Optional. You can also add funds later."}
            </p>
          </div>
        )}



        <div className="flex gap-4 pt-4 border-t border-gray-700/50">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded-xl font-medium transition-colors"
          >
            {loading ? "Saving..." : isEditing ? "Save Changes" : "Create Account"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-6 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

