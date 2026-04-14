"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Transaction, getTransactions } from "@/lib/api";
import TransactionTable from "@/components/TransactionTable";

const PAGE_SIZE = 50;

export default function TransactionsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const fetchPage = useCallback(
    async (newOffset: number, append = false) => {
      setLoading(true);
      try {
        const res = await getTransactions(PAGE_SIZE, newOffset);
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
    [router]
  );

  useEffect(() => {
    fetchPage(0);
  }, [fetchPage]);

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-16 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
          All Transactions
        </h1>
        <button
          onClick={() => router.push("/")}
          className="text-xs font-medium text-gray-400 hover:text-gray-600 transition-colors"
        >
          Back to dashboard
        </button>
      </header>

      <TransactionTable transactions={transactions} />

      {hasMore && (
        <div className="flex justify-center">
          <button
            onClick={() => fetchPage(offset, true)}
            disabled={loading}
            className="px-5 py-2 bg-gray-900 text-white rounded-xl text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {loading ? "Loading..." : "Load more"}
          </button>
        </div>
      )}
    </main>
  );
}
