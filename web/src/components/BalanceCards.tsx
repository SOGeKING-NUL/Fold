"use client";

import { BalanceRow } from "@/lib/api";
import { formatINR, capitalize } from "@/lib/format";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface Props {
  balances: BalanceRow[];
}

export default function BalanceCards({ balances }: Props) {
  if (!balances.length) return null;

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-500 mb-3">
        Account Balances
      </h2>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        {balances.map((b) => (
          <Card key={b.code} className="p-4 flex flex-col gap-1">
            <span className="text-xs text-gray-500 truncate">
              {capitalize(b.code)}
            </span>
            <span className="text-base font-bold text-gray-900 tabular-nums">
              {formatINR(b.balance_minor)}
            </span>
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">
              {b.account_type}
            </span>
          </Card>
        ))}
      </div>
    </section>
  );
}
