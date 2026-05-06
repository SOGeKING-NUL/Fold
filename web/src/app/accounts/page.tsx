"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { OrbitalLoader } from "@/components/ui/OrbitalLoader";
import { CreditCard } from "@/components/shared-assets/credit-card/credit-card";

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
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [profiles, setProfiles] = useState<PaymentProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "cards" | "cash" | "upi">("overview");
  const [currentCardIndex, setCurrentCardIndex] = useState(0);

  const fetchAccounts = useCallback(async () => {
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
      setApiError(null);
    } catch (error) {
      console.error("Error fetching accounts:", error);
      setApiError("Unable to connect to backend server. Please ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      fetchAccounts();
    }
  }, [isLoaded, isSignedIn, fetchAccounts]);

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

  const cardAccounts = accounts.filter(acc => acc.account_type === "credit" || acc.account_type === "bank");
  const cashAccounts = accounts.filter(acc => acc.account_type === "cash");


  const nextCard = () => {
    setCurrentCardIndex((prev) => (prev + 1) % cardAccounts.length);
  };

  const prevCard = () => {
    setCurrentCardIndex((prev) => (prev - 1 + cardAccounts.length) % cardAccounts.length);
  };

  if (!isLoaded || loading) {
    return (
      <div className="min-h-screen bg-linear-to-br from-black via-gray-900 to-black flex items-center justify-center">
        <OrbitalLoader message="Loading accounts..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-black via-gray-900 to-black font-sans">
      {apiError && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="max-w-md w-full p-8 bg-red-500/10 backdrop-blur-sm border border-red-500/20 rounded-2xl shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h2 className="text-xl font-bold text-red-400">Connection Error</h2>
            </div>
            <p className="text-white mb-6">{apiError}</p>
            <div className="space-y-3">
              <button
                onClick={() => {
                  setApiError(null);
                  setLoading(true);
                  fetchAccounts();
                }}
                className="w-full px-4 py-3 bg-red-500/20 hover:bg-red-500/30 text-white rounded-xl font-medium transition-colors cursor-pointer border border-red-500/30"
              >
                Retry Connection
              </button>
              <button
                onClick={() => setApiError(null)}
                className="w-full px-4 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-medium transition-colors cursor-pointer border border-white/10"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}


      <main className="max-w-7xl mx-auto px-4 py-8 mt-16">
        {!isFormOpen && (
          <>
            <div className="mb-8">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">Accounts</h1>
                  <p className="text-gray-400">Manage your financial accounts</p>
                </div>
                <button
                  onClick={handleOpenAdd}
                  className="px-5 py-2.5 bg-[#1e3a8a] hover:bg-[#1e40af] text-white rounded-xl font-medium transition-colors flex items-center gap-2 cursor-pointer shadow-lg"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Account
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-5 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl">
                  <p className="text-sm text-gray-400 mb-1">Total Balance</p>
                  <p className={`text-2xl font-bold ${accounts.reduce((sum, acc) => sum + (acc.balance !== undefined ? acc.balance / 100 : 0), 0) < 0 ? 'text-red-400' : 'text-white'}`}>
                    ₹{accounts.reduce((sum, acc) => sum + (acc.balance !== undefined ? acc.balance / 100 : 0), 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </p>
                </div>
                <div className="p-5 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl">
                  <p className="text-sm text-gray-400 mb-1">Total Accounts</p>
                  <p className="text-2xl font-bold text-white">{accounts.length}</p>
                </div>
                <div className="p-5 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl">
                  <p className="text-sm text-gray-400 mb-1">Linked UPI Apps</p>
                  <p className="text-2xl font-bold text-white">{profiles.length}</p>
                </div>
              </div>
            </div>


            <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
              <button
                onClick={() => setActiveTab("overview")}
                className={`px-5 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap cursor-pointer ${activeTab === "overview"
                  ? "bg-white/10 text-white border border-white/20"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
                  }`}
              >
                Overview
              </button>
              {cardAccounts.length > 0 && (
                <button
                  onClick={() => setActiveTab("cards")}
                  className={`px-5 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap cursor-pointer ${activeTab === "cards"
                    ? "bg-white/10 text-white border border-white/20"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                    }`}
                >
                  Cards ({cardAccounts.length})
                </button>
              )}
              {cashAccounts.length > 0 && (
                <button
                  onClick={() => setActiveTab("cash")}
                  className={`px-5 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap cursor-pointer ${activeTab === "cash"
                    ? "bg-white/10 text-white border border-white/20"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                    }`}
                >
                  Cash ({cashAccounts.length})
                </button>
              )}
              <button
                onClick={() => setActiveTab("upi")}
                className={`px-5 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap cursor-pointer ${activeTab === "upi"
                  ? "bg-white/10 text-white border border-white/20"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
                  }`}
              >
                UPI Apps ({profiles.length})
              </button>
            </div>


            <div className="min-h-[500px]">
              {activeTab === "overview" && (
                <div className="space-y-6">
                  {accounts.length === 0 ? (
                    <div className="text-center py-20">
                      <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                        <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                        </svg>
                      </div>
                      <h3 className="text-xl font-semibold text-white mb-2">No accounts yet</h3>
                      <p className="text-gray-400 mb-6">Get started by adding your first account</p>
                      <button onClick={handleOpenAdd} className="px-6 py-3 bg-[#1e3a8a] hover:bg-[#1e40af] text-white rounded-xl font-medium transition-colors cursor-pointer">
                        Add Your First Account
                      </button>
                    </div>
                  ) : (
                    <>
                      {cardAccounts.length > 0 && (
                        <div className="mb-8">  
                          <h3 className="text-lg font-semibold text-white mb-4">Featured Card</h3>
                          <div className="relative">
                            <div className="flex items-center justify-center">
                              {cardAccounts.length > 1 && (
                                <button
                                  onClick={prevCard}
                                  className="absolute left-0 z-10 p-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors cursor-pointer border border-white/10"
                                >
                                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                  </svg>
                                </button>
                              )}

                              <div className="max-w-md mx-auto">
                                {cardAccounts.map((acc, index) => {
                                  if (index !== currentCardIndex) return null;
                                  const balance = acc.balance !== undefined ? acc.balance / 100 : 0;

                                  return (
                                    <div key={acc.id} className="text-center">
                                      <CreditCard
                                        company={acc.institution_name || "Bank"}
                                        cardNumber={acc.account_number_last4 ? `•••• •••• •••• ${acc.account_number_last4}` : "•••• •••• •••• ••••"}
                                        cardHolder={acc.name.toUpperCase()}
                                        width={380}
                                        type="transparent-gradient" />
                                      <div className="mt-6 flex items-center justify-center gap-4">
                                        <div className="text-center">
                                          <p className="text-sm text-gray-400 mb-1">Balance</p>
                                          <p className={`text-2xl font-bold ${balance < 0 ? 'text-red-400' : 'text-white'}`}>
                                            ₹{balance.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                          </p>
                                        </div>
                                      </div>
                                      <div className="mt-4 flex justify-center gap-3">
                                        <button
                                          onClick={() => handleOpenEdit(acc)}
                                          className="px-5 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm cursor-pointer border border-white/10 transition-colors"
                                        >
                                          Manage Card
                                        </button>
                                        {!acc.is_default && (
                                          <SetDefaultButton accountName={acc.name} onSuccess={fetchAccounts} />
                                        )}
                                      </div>
                                    </div>
                                  );
                                })};
                              </div>

                              {cardAccounts.length > 1 && (
                                <button
                                  onClick={nextCard}
                                  className="absolute right-0 z-10 p-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors cursor-pointer border border-white/10"
                                >
                                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                  </svg>
                                </button>
                              )}
                            </div>

                            {cardAccounts.length > 1 && (
                              <div className="flex justify-center gap-2 mt-6">
                                {cardAccounts.map((_, index) => (
                                  <button
                                    key={index}
                                    onClick={() => setCurrentCardIndex(index)}
                                    className={`h-2 rounded-full transition-all cursor-pointer ${index === currentCardIndex ? "w-8 bg-white" : "w-2 bg-white/30"
                                      }`}
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      <div>
                        <h3 className="text-lg font-semibold text-white mb-4">Quick Access</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[400px] overflow-y-auto pr-2">
                          {accounts.slice(0, 6).map((acc) => (
                            <AccountCard key={acc.id} account={acc} onEdit={() => handleOpenEdit(acc)} onRefresh={fetchAccounts} compact />
                          ))}
                        </div>
                        {accounts.length > 6 && (
                          <button
                            onClick={() => setActiveTab(cardAccounts.length > 0 ? "cards" : "cash")}
                            className="mt-4 w-full py-3 text-center text-blue-400 hover:text-blue-300 transition-colors cursor-pointer"
                          >
                            View all {accounts.length} accounts →
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}

              {activeTab === "cards" && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-h-[600px] overflow-y-auto pr-2">
                  {cardAccounts.map((acc) => {
                    const balance = acc.balance !== undefined ? acc.balance / 100 : 0;

                    return (
                      <div key={acc.id} className="p-6 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl hover:bg-white/[0.07] transition-all">
                        <CreditCard
                          company={acc.institution_name || "Bank"}
                          cardNumber={acc.account_number_last4 ? `•••• •••• •••• ${acc.account_number_last4}` : "•••• •••• •••• ••••"}
                          cardHolder={acc.name.toUpperCase()}
                          width={320}
                        />
                        <div className="mt-4 flex items-center justify-between">
                          <div>
                            <p className="text-sm text-gray-400">Balance</p>
                            <p className={`text-xl font-bold ${balance < 0 ? 'text-red-400' : 'text-white'}`}>
                              ₹{balance.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </p>
                          </div>
                          <button
                            onClick={() => handleOpenEdit(acc)}
                            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm cursor-pointer border border-white/10"
                          >
                            Manage
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {activeTab === "cash" && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[600px] overflow-y-auto pr-2">
                  {cashAccounts.map((acc) => {
                    const balance = acc.balance !== undefined ? acc.balance / 100 : 0;
                    return (
                      <div key={acc.id} className="p-5 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl hover:bg-white/[0.07] transition-all">
                        <h3 className="text-lg font-semibold text-white mb-2">{acc.name}</h3>
                        <p className={`text-2xl font-bold ${balance < 0 ? 'text-red-400' : 'text-white'}`}>
                          ₹{balance.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                        <button
                          onClick={() => handleOpenEdit(acc)}
                          className="mt-4 w-full px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm cursor-pointer border border-white/10"
                        >
                          Manage
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {activeTab === "upi" && (
                <div className="max-h-[600px] overflow-y-auto pr-2">
                  <PaymentProfilesSection profiles={profiles} accounts={accounts} onRefresh={fetchAccounts} />
                </div>
              )}
            </div>
          </>
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
      </main>
    </div>
  );
}


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
        <div key={p.id} className="p-4 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl flex justify-between items-center hover:bg-white/[0.07] hover:border-white/20 transition-all duration-300 shadow-lg">
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
          className="w-full p-4 border border-dashed border-white/10 rounded-2xl text-gray-400 hover:text-white hover:border-white/20 hover:bg-white/5 transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Link UPI / Payment App
        </button>
      ) : (
        <form onSubmit={handleLink} className="p-5 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl space-y-4 shadow-lg">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Provider</label>
              <select
                value={provider}
                onChange={e => setProvider(e.target.value)}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500 [&>option]:bg-gray-900 [&>option]:text-white"
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
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Link to Bank Account</label>
              <select
                required
                value={linkedAccount}
                onChange={e => setLinkedAccount(e.target.value)}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500 [&>option]:bg-gray-900 [&>option]:text-white"
              >
                <option value="">Select Account...</option>
                {accounts.filter(a => a.account_type === "bank").map(a => (
                  <option key={a.id} value={a.name}>{a.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={() => setIsLinking(false)} className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm font-medium transition-colors cursor-pointer border border-white/10">
              Cancel
            </button>
            <button type="submit" className="px-4 py-2 bg-[#1e3a8a] hover:bg-[#1e40af] text-white rounded-lg text-sm font-medium transition-colors cursor-pointer">
              Link App
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function SetDefaultButton({ accountName, onSuccess }: { accountName: string; onSuccess: () => void }) {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleSetDefault = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!userResponse.ok) throw new Error("Failed to get user info");

      const userData = await userResponse.json();
      const res = await fetch(
        `${API_BASE}/api/v1/ledger/accounts/${userData.user_ref}/set-default?account_name=${encodeURIComponent(accountName)}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) throw new Error("Failed to set default");

      onSuccess();
    } catch (err) {
      console.error(err);
      alert("Failed to set as default.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleSetDefault}
      disabled={loading}
      className="px-5 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg text-sm cursor-pointer border border-green-500/30 transition-colors disabled:opacity-50"
    >
      {loading ? "Setting..." : "Set as Default"}
    </button>
  );
}

function AccountCard({ account, onEdit, onRefresh, compact }: { account: Account; onEdit: () => void; onRefresh: () => void; compact?: boolean }) {
  const { getToken } = useAuth();
  const [isAddingFunds, setIsAddingFunds] = useState(false);
  const [fundAmount, setFundAmount] = useState("");

  const balance = account.balance !== undefined ? account.balance / 100 : 0;
  const isNegative = balance < 0;

  const typeColors: Record<string, string> = {
    bank: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    credit: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    cash: "bg-green-500/10 text-green-400 border-green-500/20",
  };

  const handleAddFunds = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(fundAmount);
    if (isNaN(amount) || amount <= 0) return alert("Enter a valid amount");

    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const userData = await userResponse.json();

      const res = await fetch(`${API_BASE}/api/v1/ledger/accounts/${userData.user_ref}/add-funds`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          account_name: account.name,
          amount_cents: Math.round(amount * 100),
        }),
      });

      if (!res.ok) throw new Error("Failed to add funds");

      setIsAddingFunds(false);
      setFundAmount("");
      onRefresh();
    } catch (err) {
      console.error(err);
      alert("Failed to add funds.");
    }
  };

  if (compact) {
    return (
      <div className="p-4 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl hover:bg-white/[0.07] transition-all">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="text-white font-medium">{account.name}</h3>
            <span className={`inline-block px-2 py-0.5 rounded text-xs mt-1 border ${typeColors[account.account_type] || typeColors.bank}`}>
              {account.account_type}
            </span>
          </div>
          {account.is_default && (
            <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-400 rounded text-xs border border-yellow-500/20">
              Default
            </span>
          )}
        </div>
        <p className={`text-xl font-bold ${isNegative ? 'text-red-400' : 'text-white'}`}>
          ₹{balance.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
        <div className="mt-3 flex gap-2">
          {!account.is_default && (
            <SetDefaultButton accountName={account.name} onSuccess={onRefresh} />
          )}
          <button
            onClick={onEdit}
            className="flex-1 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm cursor-pointer border border-white/10 transition-colors"
          >
            Edit
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl hover:bg-white/[0.07] transition-all">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white mb-1">{account.name}</h3>
          <span className={`inline-block px-2 py-1 rounded text-xs border ${typeColors[account.account_type] || typeColors.bank}`}>
            {account.account_type}
          </span>
          {account.institution_name && (
            <p className="text-sm text-gray-400 mt-1">{account.institution_name}</p>
          )}
          {account.account_number_last4 && (
            <p className="text-sm text-gray-400">•••• {account.account_number_last4}</p>
          )}
        </div>
        {account.is_default && (
          <span className="px-3 py-1 bg-yellow-500/10 text-yellow-400 rounded-lg text-sm border border-yellow-500/20">
            Default
          </span>
        )}
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-400 mb-1">Balance</p>
        <p className={`text-2xl font-bold ${isNegative ? 'text-red-400' : 'text-white'}`}>
          ₹{balance.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
      </div>

      <div className="flex gap-2">
        {!account.is_default && (
          <SetDefaultButton accountName={account.name} onSuccess={onRefresh} />
        )}
        <button
          onClick={onEdit}
          className="flex-1 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm cursor-pointer border border-white/10 transition-colors"
        >
          Edit Account
        </button>
        {account.account_type === "cash" && !isAddingFunds && (
          <button
            onClick={() => setIsAddingFunds(true)}
            className="px-4 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg text-sm cursor-pointer border border-green-500/30 transition-colors"
          >
            Add Funds
          </button>
        )}
      </div>

      {isAddingFunds && (
        <form onSubmit={handleAddFunds} className="mt-4 p-3 bg-white/5 rounded-lg border border-white/10">
          <label className="block text-xs text-gray-400 mb-1">Amount to Add</label>
          <input
            type="number"
            step="0.01"
            value={fundAmount}
            onChange={(e) => setFundAmount(e.target.value)}
            placeholder="0.00"
            className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500 mb-2"
            autoFocus
          />
          <div className="flex gap-2">
            <button type="submit" className="flex-1 px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg text-sm cursor-pointer border border-green-500/30">
              Add
            </button>
            <button type="button" onClick={() => setIsAddingFunds(false)} className="flex-1 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm cursor-pointer border border-white/10">
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function AccountForm({ initialData, onClose, onSuccess }: { initialData: Account | null; onClose: () => void; onSuccess: () => void }) {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: initialData?.name || "",
    account_type: initialData?.account_type || "bank",
    institution_name: initialData?.institution_name || "",
    account_number_last4: initialData?.account_number_last4 || "",
    balance: initialData?.balance !== undefined ? (initialData.balance / 100).toString() : "0",
  });

  const isEditing = !!initialData;

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

      if (isEditing) {
        const res = await fetch(`${API_BASE}/api/v1/ledger/accounts/${userRef}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            account_name: initialData.name,
            new_data: {
              name: formData.name,
              account_type: formData.account_type,
              institution_name: formData.institution_name || null,
              account_number_last4: formData.account_number_last4 || null,
              balance: Math.round(parseFloat(formData.balance) * 100),
            },
          }),
        });

        if (!res.ok) throw new Error("Failed to update account");
      } else {
        const res = await fetch(`${API_BASE}/api/v1/ledger/accounts`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            user_ref: userRef,
            name: formData.name,
            account_type: formData.account_type,
            institution_name: formData.institution_name || null,
            account_number_last4: formData.account_number_last4 || null,
            balance: Math.round(parseFloat(formData.balance) * 100),
          }),
        });

        if (!res.ok) throw new Error("Failed to create account");
      }

      onSuccess();
    } catch (error) {
      console.error("Error saving account:", error);
      alert("Failed to save account. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!isEditing) return;
    if (!confirm(`Are you sure you want to delete "${initialData.name}"? This action cannot be undone.`)) return;

    setLoading(true);
    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

      const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const userData = await userResponse.json();

      const res = await fetch(
        `${API_BASE}/api/v1/ledger/accounts/${userData.user_ref}?account_name=${encodeURIComponent(initialData.name)}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) throw new Error("Failed to delete account");

      onSuccess();
    } catch (err) {
      console.error(err);
      alert("Failed to delete account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="max-w-2xl w-full max-h-[90vh] overflow-y-auto bg-gradient-to-br from-gray-900 to-black border border-white/10 rounded-2xl shadow-2xl">
        <div className="sticky top-0 bg-gradient-to-br from-gray-900 to-black border-b border-white/10 p-6 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-white">
            {isEditing ? "Edit Account" : "Add New Account"}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Account Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. HDFC Savings, Cash Wallet"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Account Type <span className="text-red-400">*</span>
            </label>
            <select
              required
              value={formData.account_type}
              onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all [&>option]:bg-gray-900 [&>option]:text-white"
            >
              <option value="bank">Bank Account</option>
              <option value="credit">Credit Card</option>
              <option value="cash">Cash</option>
            </select>
          </div>

          {formData.account_type !== "cash" && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Institution Name
                </label>
                <input
                  type="text"
                  value={formData.institution_name}
                  onChange={(e) => setFormData({ ...formData, institution_name: e.target.value })}
                  placeholder="e.g. HDFC Bank, ICICI Bank"
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Last 4 Digits of Account/Card Number
                </label>
                <input
                  type="text"
                  maxLength={4}
                  value={formData.account_number_last4}
                  onChange={(e) => setFormData({ ...formData, account_number_last4: e.target.value.replace(/\D/g, "") })}
                  placeholder="1234"
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Current Balance (₹) <span className="text-red-400">*</span>
            </label>
            <input
              type="number"
              step="0.01"
              required
              value={formData.balance}
              onChange={(e) => setFormData({ ...formData, balance: e.target.value })}
              placeholder="0.00"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
            />
            <p className="text-xs text-gray-500 mt-1">
              For credit cards, enter negative balance if you owe money
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            {isEditing && (
              <button
                type="button"
                onClick={handleDelete}
                disabled={loading}
                className="px-5 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-xl font-medium transition-colors cursor-pointer border border-red-500/30 disabled:opacity-50"
              >
                Delete Account
              </button>
            )}
            <div className="flex-1"></div>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-5 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-medium transition-colors cursor-pointer border border-white/10 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-3 bg-[#1e3a8a] hover:bg-[#1e40af] text-white rounded-xl font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              {loading ? "Saving..." : isEditing ? "Update Account" : "Create Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
