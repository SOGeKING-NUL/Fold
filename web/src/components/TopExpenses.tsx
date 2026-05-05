"use client";

import { Transaction } from "@/lib/api";
import { formatINR, formatDateTime, capitalize, categoryColor } from "@/lib/format";

interface Props {
  transactions: Transaction[];
}

export default function TopExpenses({ transactions }: Props) {
  const expenses = transactions
    .filter((t) => t.type === "expense")
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 5);

  if (!expenses.length) {
    return <p className="text-[#999999] text-sm">No expenses found.</p>;
  }

  return (
    <div className="space-y-3">
      {expenses.map((tx, i) => {
        const category = tx.category || "expense";
        return (
          <div key={tx.id} className="flex items-center gap-3 p-3 rounded-xl bg-white border border-[#e5e5e5] hover:border-[#156d95] transition-all duration-300">
            <span className="w-7 h-7 rounded-full bg-linear-to-br from-[#f8f8f8] to-[#ececec] border border-[#e5e5e5] flex items-center justify-center text-xs font-semibold text-[#666666]">
              {i + 1}
            </span>
            <div
              className="w-1 h-10 rounded-full shrink-0"
              style={{ backgroundColor: categoryColor(category) }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-[#202020] truncate font-medium">
                {tx.description || capitalize(tx.type)}
              </p>
              <p className="text-[11px] text-[#999999]">
                {formatDateTime(tx.occurred_at)}
                {tx.category && (
                  <span> &middot; {capitalize(tx.category)}</span>
                )}
              </p>
            </div>
            <span className="text-sm font-semibold text-[#202020] tabular-nums">
              {formatINR(tx.amount)}
            </span>
          </div>
        );
      })}
    </div>
  );
}