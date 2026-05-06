"use client";

import { Account } from "@/lib/api";
import { formatINR } from "@/lib/format";

interface Props {
  accounts: Account[];
}

export default function BalanceCards({ accounts }: Props) {
  if (!accounts?.length) return null;

  return (
    <section className="animate-in fade-in slide-in-from-top-4 duration-700">
      <div className="flex items-center justify-between mb-4 px-1">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          Your Balances
        </h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 ">
        {accounts.map((a) => (
          <div 
            key={a.id} 
            className="p-5 flex flex-col gap-1.5 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm shadow-lg hover:bg-white/[0.07] hover:border-white/20 transition-all duration-300 group"
          >
            <span className="text-[10px] text-gray-400 uppercase tracking-wider font-medium group-hover:text-gray-300 transition-colors">
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