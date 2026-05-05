"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  DashboardData,
  getDashboard,
} from "@/lib/api";
import { useAuth } from "@clerk/nextjs";
import { Card, CardContent, CardTitle } from "@/components/ui/card";

import SummaryCards from "@/components/SummaryCards";
import BalanceCards from "@/components/BalanceCards";
import CategoryChart from "@/components/CategoryChart";
import CategoryBarChart from "@/components/CategoryBarChart";
import BreakdownList from "@/components/BreakdownList";
import SpendVsIncomeChart from "@/components/SpendVsIncomeChart";
import DailyTrendChart from "@/components/DailyTrendChart";
import TopExpenses from "@/components/TopExpenses";
import TransactionTable from "@/components/TransactionTable";
import PeriodToggle from "@/components/PeriodToggle";

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
      <div className="flex items-center justify-center min-h-screen bg-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[#f5f5f5] border-t-[#156d95] rounded-full animate-spin" />
          <span className="text-[#666666] text-sm">Loading reports...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4 bg-white">
        <div className="text-center">
          <p className="text-red-500 text-sm mb-4">{error}</p>
          <button
            onClick={() => fetchDashboard(period)}
            className="px-4 py-2 bg-[#156d95] text-white rounded-xl text-sm hover:bg-[#146e96] transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <main className="mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-16 space-y-8 bg-white min-h-screen mt-16">
      <header className="flex items-center justify-between pb-6 border-b border-[#e5e5e5]">
        <div>
          <h1 className="text-3xl font-bold text-[#202020] tracking-tight">
            Fold Reports
          </h1>
          <p className="text-sm text-[#666666] mt-1">{data.period_label}</p>
        </div>
        <div className="flex items-center gap-3">
          <PeriodToggle period={period} onChange={handlePeriodChange} />
          <button
            onClick={handleLogout}
            className="text-xs text-[#666666] hover:text-[#202020] transition-colors cursor-pointer"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Main Layout: Left Column (Summary + Daily Trend) + Right Column (Income vs Spending + Spending by Category) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          <SummaryCards summary={data.summary} />
          <Card>
            <CardContent>
              <CardTitle className="mb-4">Daily Spending Trend</CardTitle>
              <DailyTrendChart data={data.daily_trend} />
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          <Card>
            <CardContent>
              <CardTitle className="mb-4">Income vs Spending</CardTitle>
              <SpendVsIncomeChart summary={data.summary} />
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <CategoryChart
                data={data.by_category}
                title="Spending by Category"
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Bottom Row: Category Breakdown + Top Expenses */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardContent>
            <CardTitle className="mb-4">Category Breakdown</CardTitle>
            <CategoryBarChart data={data.by_category} />
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <CardTitle className="mb-4">Top Expenses</CardTitle>
            <TopExpenses transactions={data.recent_transactions} />
          </CardContent>
        </Card>
      </div>

      {/* Transaction History Section */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-[#202020] tracking-tight">
          Transaction History
        </h2>
        <TransactionTable
          transactions={data.recent_transactions}
          showViewAll
          onViewAll={() => router.push("/transactions")}
        />
      </div>

      {/* Hidden sections - keeping functionality intact */}
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
