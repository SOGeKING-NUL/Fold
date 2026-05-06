"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Transaction, Account, getTransactions, getDashboard } from "@/lib/api";
import TransactionTable from "@/components/TransactionTable";
import BalanceCards from "@/components/BalanceCards";
import { useAuth } from "@clerk/nextjs";
import { OrbitalLoader } from "@/components/ui/OrbitalLoader";

const PAGE_SIZE = 50;

export default function TransactionsPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const fetchPage = useCallback(
    async (newOffset: number, append = false) => {
      setLoading(true);
      try {
        const token = await getToken();
        if (!token) throw new Error("Unauthorized");
        const res = await getTransactions(PAGE_SIZE, newOffset, token);
        
        if (newOffset === 0) {
          // Also fetch accounts for the top balance cards on initial load
          const dash = await getDashboard("monthly", token);
          setAccounts(dash.accounts || []);
        }

        if (append) {
          setTransactions((prev) => [...prev, ...res.transactions]);
        } else {
          setTransactions(res.transactions);
        }
        setHasMore(res.transactions.length >= PAGE_SIZE);
        setOffset(newOffset + res.transactions.length);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "";
        if (msg.includes("401") || msg.includes("Unauthorized")) {
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    },
    [router, getToken]
  );

  useEffect(() => {
    fetchPage(0);
  }, [fetchPage]);

  return (
    <div className="min-h-screen font-sans bg-linear-to-br from-black via-gray-900 to-black">
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-16 space-y-10 mt-16">
        <BalanceCards accounts={accounts} />

      {loading && transactions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20">
          <OrbitalLoader message="Fetching transactions..." />
        </div>
      ) : (
        <TransactionTable transactions={transactions} />
      )}

      {hasMore && (
        <div className="flex justify-center pt-8">
          <button
            onClick={() => fetchPage(offset, true)}
            disabled={loading}
            className="px-8 py-3 bg-[#1e3a8a] hover:bg-[#1e40af] text-white rounded-2xl text-sm font-semibold transition-all duration-300 disabled:opacity-50 hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
          >
            {loading ? "Loading more..." : "Show older transactions"}
          </button>
        </div>
      )}
      </main>
    </div>
  );
}
