"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Transaction, Account, getTransactions } from "@/lib/api";
import TransactionTable from "@/components/TransactionTable";
import BalanceCards from "@/components/BalanceCards";
import { useAuth } from "@clerk/nextjs";
import { OrbitalLoader } from "@/components/ui/OrbitalLoader";

const PAGE_SIZE = 10; // Optimized: Load only 10 transactions per page for faster load

export default function TransactionsPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchPage = useCallback(
    async (page: number, append = false) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      
      try {
        const token = await getToken();
        if (!token) throw new Error("Unauthorized");
        
        const offset = (page - 1) * PAGE_SIZE;
        const res = await getTransactions(PAGE_SIZE, offset, token);
        
        // Only fetch accounts on initial load (page 1, not appending)
        if (page === 1 && !append) {
          const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
          const userResponse = await fetch(`${API_BASE}/api/v1/web/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (userResponse.ok) {
            const userData = await userResponse.json();
            const accountsResponse = await fetch(`${API_BASE}/api/v1/ledger/accounts/${userData.user_ref}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (accountsResponse.ok) {
              const accountsData = await accountsResponse.json();
              setAccounts(accountsData.accounts || []);
            }
          }
        }

        if (append) {
          setTransactions((prev) => [...prev, ...res.transactions]);
        } else {
          setTransactions(res.transactions);
        }
        
        setHasMore(res.transactions.length >= PAGE_SIZE);
        setCurrentPage(page);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "";
        if (msg.includes("401") || msg.includes("Unauthorized")) {
          router.push("/login");
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [router, getToken]
  );

  useEffect(() => {
    fetchPage(1);
  }, [fetchPage]);

  const handleLoadMore = () => {
    fetchPage(currentPage + 1, true);
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      fetchPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (hasMore) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      fetchPage(currentPage + 1);
    }
  };

  return (
    <div className="min-h-screen font-sans bg-linear-to-br from-black via-gray-900 to-black">
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-16 space-y-10 mt-16">
        <BalanceCards accounts={accounts} />

        {loading && transactions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <OrbitalLoader message="Fetching transactions..." />
          </div>
        ) : (
          <>
            <TransactionTable transactions={transactions} />

            {/* Pagination Controls */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-8">
              <div className="text-sm text-gray-400">
                Page {currentPage} • Showing {transactions.length} transactions
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={handlePrevPage}
                  disabled={currentPage === 1 || loading}
                  className="px-6 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl text-sm font-medium transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] cursor-pointer border border-white/10"
                >
                  ← Previous
                </button>
                
                <button
                  onClick={handleNextPage}
                  disabled={!hasMore || loading}
                  className="px-6 py-2.5 bg-[#0d9488] hover:bg-[#0f766e] text-white rounded-xl text-sm font-medium transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
                >
                  {loading ? "Loading..." : "Next →"}
                </button>
              </div>
            </div>

            {/* Optional: Load More Button (for infinite scroll style) */}
            {hasMore && (
              <div className="flex justify-center pt-4">
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="px-8 py-3 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-2xl text-sm font-medium transition-all duration-300 disabled:opacity-50 border border-white/10 cursor-pointer"
                >
                  {loadingMore ? "Loading more..." : "Load more transactions"}
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
