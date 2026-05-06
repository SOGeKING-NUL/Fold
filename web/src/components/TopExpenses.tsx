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
    return <p className="text-gray-500 text-sm">No expenses found.</p>;
  }

  return (
    <div className="space-y-3">
      {expenses.map((tx, i) => {
        const category = tx.category || "expense";
        return (
          <div key={tx.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/[0.07] hover:border-white/20 transition-all duration-200">
            <span className="w-7 h-7 rounded-full bg-white/10 border border-white/10 flex items-center justify-center text-xs font-semibold text-gray-300">
              {i + 1}
            </span>
            <div
              className="w-1 h-10 rounded-full shrink-0"
              style={{ backgroundColor: categoryColor(category) }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate font-medium">
                {tx.description || capitalize(tx.type)}
              </p>
              <p className="text-[11px] text-gray-400">
                {formatDateTime(tx.occurred_at)}
                {tx.category && (
                  <span> &middot; {capitalize(tx.category)}</span>
                )}
              </p>
            </div>
            <span className="text-sm font-semibold text-white tabular-nums">
              {formatINR(tx.amount)}
            </span>
          </div>
        );
      })}
    </div>
  );
}