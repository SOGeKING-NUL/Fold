"use client";

import { Transaction } from "@/lib/api";
import { formatINR, formatDateTime, capitalize, categoryColor } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

interface Props {
  transactions: Transaction[];
  showViewAll?: boolean;
  onViewAll?: () => void;
}

function badgeVariant(type: string) {
  const map: Record<string, "expense" | "income" | "investment" | "transfer" | "default"> = {
    expense: "expense",
    income: "income",
    investment: "investment",
    transfer: "transfer",
  };
  return map[type] || "default";
}

export default function TransactionTable({
  transactions,
  showViewAll,
  onViewAll,
}: Props) {
  if (!transactions.length) {
    return <p className="text-gray-400 text-sm">No transactions yet.</p>;
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-500">
          Recent Transactions
        </h2>
        {showViewAll && (
          <button
            onClick={onViewAll}
            className="text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
          >
            View all
          </button>
        )}
      </div>
      <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden shadow-sm">
        <div className="divide-y divide-gray-100">
          {transactions.map((tx) => {
            const meta = tx.metadata_json || {};
            const category = (meta.category as string) || tx.transaction_type;
            const amount = tx.total_debit_minor || tx.total_credit_minor;

            return (
              <div
                key={tx.id}
                className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors"
              >
                <div
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: categoryColor(category) }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 truncate">
                    {tx.description || capitalize(tx.transaction_type)}
                  </p>
                  <p className="text-[11px] text-gray-400 flex gap-2 mt-0.5">
                    <span>{formatDateTime(tx.occurred_at)}</span>
                    {typeof meta.payment_method === "string" &&
                      meta.payment_method && (
                        <span className="text-gray-400">
                          via {capitalize(meta.payment_method)}
                        </span>
                      )}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-gray-900 tabular-nums">
                    {formatINR(amount)}
                  </p>
                  <Badge variant={badgeVariant(tx.transaction_type)}>
                    {capitalize(tx.transaction_type)}
                  </Badge>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
