"use client";

import { DashboardSummary } from "@/lib/api";
import { formatINR } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  ArrowDownLeft,
  ArrowUpRight,
  TrendingUp,
  Wallet,
} from "lucide-react";

interface Props {
  summary: DashboardSummary;
}

const cards = [
  {
    key: "expense_minor" as const,
    label: "Expenses",
    color: "text-red-600",
    icon: ArrowUpRight,
    iconBg: "bg-red-50 text-red-500",
  },
  {
    key: "income_minor" as const,
    label: "Income",
    color: "text-emerald-600",
    icon: ArrowDownLeft,
    iconBg: "bg-emerald-50 text-emerald-500",
  },
  {
    key: "investment_minor" as const,
    label: "Investments",
    color: "text-blue-600",
    icon: TrendingUp,
    iconBg: "bg-blue-50 text-blue-500",
  },
  {
    key: "net_cashflow_minor" as const,
    label: "Net Cash Flow",
    color: "text-gray-900",
    icon: Wallet,
    iconBg: "bg-gray-100 text-gray-600",
  },
];

export default function SummaryCards({ summary }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((c) => {
        const value = summary[c.key];
        const Icon = c.icon;
        return (
          <div
            key={c.key}
            className="rounded-2xl border border-[#d0d0d0] bg-linear-to-br from-[#f8f8f8] to-[#ececec] p-5 flex flex-col gap-3 shadow-sm hover:shadow-md hover:border-[#156d95] transition-all duration-300"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#666666] uppercase tracking-wider">
                {c.label}
              </span>
              <div
                className={cn(
                  "w-8 h-8 rounded-xl flex items-center justify-center",
                  c.iconBg
                )}
              >
                <Icon className="w-4 h-4" />
              </div>
            </div>
            <span className={cn("text-2xl font-bold text-[#156d95] tabular-nums")}>
              {formatINR(value)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
