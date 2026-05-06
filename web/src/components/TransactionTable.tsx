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
    transfer: "transfer",
    opening_balance: "default",
  };
  return map[type] || "default";
}

export default function TransactionTable({
  transactions,
  showViewAll,
  onViewAll,
}: Props) {
  if (!transactions.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-500">
        <svg className="w-12 h-12 mb-3 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p className="text-sm">No transactions found</p>
      </div>
    );
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3 px-1">
        <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
          Transaction History
        </h2>
        {showViewAll && (
          <button
            onClick={onViewAll}
            className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors cursor-pointer"
          >
            View all
          </button>
        )}
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm overflow-hidden shadow-lg">
        <div className="divide-y divide-white/10">
          {transactions.map((tx) => {
            const category = tx.category || tx.type;
            const amount = tx.amount || 0;

            return (
              <div
                key={tx.id}
                className="flex items-center gap-4 px-5 py-4 hover:bg-white/[0.07] transition-all duration-200 group"
              >
                <div
                  className="w-2 h-2 rounded-full shrink-0 shadow-sm"
                  style={{ backgroundColor: categoryColor(category) }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors truncate">
                    {tx.description || capitalize(tx.type || "transaction")}
                  </p>
                  <p className="text-[11px] text-gray-400 flex items-center gap-2 mt-1">
                    <span>{formatDateTime(tx.occurred_at)}</span>
                    <span className="w-1 h-1 bg-gray-600 rounded-full" />
                    {tx.source && (
                      <span className="text-gray-400">
                        via {capitalize(tx.source)}
                      </span>
                    )}
                  </p>
                </div>
                <div className="text-right shrink-0 space-y-1">
                  <p className="text-sm font-bold text-white tabular-nums">
                    {formatINR(amount)}
                  </p>
                  <div className="scale-75 origin-right">
                    <Badge variant={badgeVariant(tx.type)}>
                      {capitalize(tx.type || "transaction")}
                    </Badge>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
