"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  DashboardData,
  getDashboard,
} from "@/lib/api";
import { formatINR } from "@/lib/format";
import { useAuth } from "@clerk/nextjs";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import BalanceCards from "@/components/BalanceCards";
import CategoryChart from "@/components/CategoryChart";
import CategoryBarChart from "@/components/CategoryBarChart";
import BreakdownList from "@/components/BreakdownList";
import SpendVsIncomeChart from "@/components/SpendVsIncomeChart";
import DailyTrendChart from "@/components/DailyTrendChart";
import TopExpenses from "@/components/TopExpenses";
import TransactionTable from "@/components/TransactionTable";
import PeriodToggle from "@/components/PeriodToggle";
import { OrbitalLoader } from "./ui/OrbitalLoader";

type Period = "weekly" | "monthly";

export default function DashboardClient() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { getToken, signOut } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const initialPeriod =
    (searchParams.get("period") === "weekly" ? "weekly" : "monthly") as Period;
  const [period, setPeriod] = useState<Period>(initialPeriod);

  const fetchDashboard = useCallback(
    async (p: Period) => {
      setLoading(true);
      setError(null);
      try {
        const token = await getToken();
        if (!token) throw new Error("Unauthorized");
        const d = await getDashboard(p, token);
        setData(d);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Failed to load";
        if (msg.includes("Unauthorized") || msg.includes("401")) {
          router.push("/login");
          return;
        }
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [router, getToken]
  );

  useEffect(() => {
    fetchDashboard(period);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePeriodChange = (p: Period) => {
    setPeriod(p);
    fetchDashboard(p);
  };

  const handleLogout = async () => {
    await signOut();
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-linear-to-br from-black via-gray-900 to-black">
        <div className="flex flex-col items-center gap-4">
          <OrbitalLoader />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4 bg-linear-to-br from-black via-gray-900 to-black">
        <div className="text-center">
          <p className="text-red-400 text-sm mb-4">{error}</p>
          <button
            onClick={() => fetchDashboard(period)}
            className="px-4 py-2 bg-[#1e3a8a] text-white rounded-xl text-sm hover:bg-[#1e40af] transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <main className="px-4 sm:px-6 lg:px-8 py-8 pb-16 space-y-6 bg-linear-to-br from-black via-gray-900 to-black min-h-screen mt-16">
      <header className="flex items-center justify-between pb-6 border-b border-white/10">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Fold Reports
          </h1>
          <p className="text-sm text-gray-400 mt-1">{data.period_label}</p>
        </div>
        <div className="flex items-center gap-3">
          <PeriodToggle period={period} onChange={handlePeriodChange} />
          <button
            onClick={handleLogout}
            className="text-xs text-gray-400 hover:text-white transition-colors cursor-pointer"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-5 flex flex-col gap-3 shadow-lg hover:bg-white/[0.07] hover:border-white/20 transition-all duration-300">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                Expenses
              </span>
              <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-red-500/10 text-red-400 border border-red-500/20">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
            <span className="text-2xl font-bold text-white tabular-nums">
              {formatINR(data.summary.expense_minor)}
            </span>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-5 flex flex-col gap-3 shadow-lg hover:bg-white/[0.07] hover:border-white/20 transition-all duration-300">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                Income
              </span>
              <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                </svg>
              </div>
            </div>
            <span className="text-2xl font-bold text-white tabular-nums">
              {formatINR(data.summary.income_minor)}
            </span>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-5 flex flex-col gap-3 shadow-lg hover:bg-white/[0.07] hover:border-white/20 transition-all duration-300">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                Investments
              </span>
              <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
            <span className="text-2xl font-bold text-white tabular-nums">
              {formatINR(data.summary.investment_minor)}
            </span>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-5 flex flex-col gap-3 shadow-lg hover:bg-white/[0.07] hover:border-white/20 transition-all duration-300">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                Net Cash Flow
              </span>
              <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-gray-500/10 text-gray-400 border border-gray-500/20">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
            </div>
            <span className="text-2xl font-bold text-white tabular-nums">
              {formatINR(data.summary.net_cashflow_minor)}
            </span>
          </div>
        </div>
        <div className="col-span-12 lg:col-span-5">
          <Card>
            <CardContent>
              <CardTitle className="mb-4">Daily Spending Trend</CardTitle>
              <DailyTrendChart data={data.daily_trend} />
            </CardContent>
          </Card>
        </div>

        <div className="col-span-12 lg:col-span-7">
          <Card>
            <CardContent>
              <CardTitle className="mb-4">Income vs Spending</CardTitle>
              <SpendVsIncomeChart summary={data.summary} />
            </CardContent>
          </Card>
        </div>

        <div className="col-span-12 lg:col-span-7">
          <Card>
            <CardContent>
              <CategoryChart
                data={data.by_category}
                title="Spending by Category"
              />
            </CardContent>
          </Card>
        </div>

        <div className="col-span-12 lg:col-span-5">
          <Card>
            <CardContent>
              <CardTitle className="mb-4">Top Expenses</CardTitle>
              <TopExpenses transactions={data.recent_transactions} />
            </CardContent>
          </Card>
        </div>

        <div className="col-span-12 lg:col-span-6">
          <Card>
            <CardContent>
              <CardTitle className="mb-4">Category Breakdown</CardTitle>
              <CategoryBarChart data={data.by_category} />
            </CardContent>
          </Card>
        </div>

        <div className="col-span-12 lg:col-span-6">
          <Card>
            <CardContent>
              <h2 className="text-sm font-semibold text-gray-300 tracking-wide mb-4">
                Recent Transactions
              </h2>
              <TransactionTable
                transactions={data.recent_transactions.slice(0, 5)}
                showViewAll
                onViewAll={() => router.push("/transactions")}
              />
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="hidden">
        <BalanceCards accounts={data.accounts} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardContent>
              <BreakdownList
                data={data.by_payment_method}
                title="By Payment Method"
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <BreakdownList data={data.by_account} title="By Account" />
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
