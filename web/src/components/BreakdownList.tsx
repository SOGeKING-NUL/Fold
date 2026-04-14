"use client";

import { BreakdownRow } from "@/lib/api";
import { formatINR, capitalize, categoryColor } from "@/lib/format";

interface Props {
  data: BreakdownRow[];
  title: string;
}

export default function BreakdownList({ data, title }: Props) {
  if (!data.length) return null;

  const max = Math.max(...data.map((r) => r.amount_minor), 1);

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-500 mb-3">{title}</h2>
      <div className="space-y-3">
        {data.map((row) => {
          const pct = (row.amount_minor / max) * 100;
          return (
            <div key={row.key}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-700 truncate">
                  {capitalize(row.key)}
                </span>
                <span className="text-gray-500 tabular-nums ml-2">
                  {formatINR(row.amount_minor)}
                </span>
              </div>
              <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: categoryColor(row.key),
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
