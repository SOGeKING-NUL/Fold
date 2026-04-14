"use client";

import { Transaction } from "@/lib/api";
import { formatINR, formatDateTime, capitalize, categoryColor } from "@/lib/format";

interface Props {
  transactions: Transaction[];
}

export default function TopExpenses({ transactions }: Props) {
  const expenses = transactions
    .filter((t) => t.transaction_type === "expense")
    .sort((a, b) => b.total_debit_minor - a.total_debit_minor)
    .slice(0, 5);

  if (!expenses.length) {
    return <p className="text-gray-400 text-sm">No expenses found.</p>;
  }

  return (
    <div className="space-y-3">
      {expenses.map((tx, i) => {
        const meta = tx.metadata_json || {};
        const category = (meta.category as string) || "expense";
        return (
          <div key={tx.id} className="flex items-center gap-3">
            <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-semibold text-gray-500">
              {i + 1}
            </span>
            <div
              className="w-2 h-8 rounded-full flex-shrink-0"
              style={{ backgroundColor: categoryColor(category) }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-800 truncate">
                {tx.description || capitalize(tx.transaction_type)}
              </p>
              <p className="text-[11px] text-gray-400">
                {formatDateTime(tx.occurred_at)}
                {typeof meta.category === "string" && (
                  <span> &middot; {capitalize(meta.category)}</span>
                )}
              </p>
            </div>
            <span className="text-sm font-semibold text-gray-900 tabular-nums">
              {formatINR(tx.total_debit_minor)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
