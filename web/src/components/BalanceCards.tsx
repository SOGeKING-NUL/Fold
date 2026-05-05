"use client";

import { Account } from "@/lib/api";
import { formatINR, capitalize } from "@/lib/format";

interface Props {
  accounts: Account[];
}

export default function BalanceCards({ accounts }: Props) {
  if (!accounts?.length) return null;

  return (
    <section className="animate-in fade-in slide-in-from-top-4 duration-700">
      <div className="flex items-center justify-between mb-4 px-1">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          Your Balances
        </h2>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {accounts.map((a) => (
          <div 
            key={a.id} 
            className="p-5 flex flex-col gap-1.5 rounded-2xl border border-gray-800/50 bg-gray-800/30 backdrop-blur-sm shadow-lg hover:border-blue-500/30 hover:bg-gray-800/50 transition-all duration-300 group"
          >
            <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium group-hover:text-blue-400/80 transition-colors">
              {a.account_type}
            </span>
            <span className="text-lg font-bold text-white tabular-nums tracking-tight">
              {formatINR(a.balance)}
            </span>
            <span className="text-xs text-gray-400 truncate font-medium">
              {a.name}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
