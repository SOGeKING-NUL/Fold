"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { BreakdownRow } from "@/lib/api";
import { formatINR, categoryColor, capitalize } from "@/lib/format";

interface Props {
  data: BreakdownRow[];
  title: string;
}

export default function CategoryChart({ data, title }: Props) {
  if (!data.length) {
    return (
      <section>
        <h2 className="text-sm font-semibold text-gray-300 mb-3">{title}</h2>
        <p className="text-gray-500 text-sm">No data for this period.</p>
      </section>
    );
  }

  const total = data.reduce((s, r) => s + r.amount_minor, 0);

  return (
    <section className="flex flex-col h-full">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">{title}</h2>
      <div className="flex flex-col sm:flex-row items-center gap-4 flex-1 min-h-0">
        <div className="flex-shrink-0" style={{ width: 180, height: 180 }}>
          <ResponsiveContainer width={180} height={180}>
            <PieChart>
              <Pie
                data={data}
                dataKey="amount_minor"
                nameKey="key"
                cx="50%"
                cy="50%"
                innerRadius={48}
                outerRadius={76}
                strokeWidth={2}
                stroke="rgba(255,255,255,0.1)"
              >
                {data.map((entry) => (
                  <Cell key={entry.key} fill={categoryColor(entry.key)} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => formatINR(Number(value))}
                labelFormatter={(label) => capitalize(String(label))}
                contentStyle={{
                  backgroundColor: "rgba(0,0,0,0.9)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "0.75rem",
                  fontSize: "0.75rem",
                  color: "#fff",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ul className="flex-1 space-y-2 w-full overflow-y-auto max-h-[200px] pr-1">
          {data.map((row) => {
            const pct =
              total > 0 ? ((row.amount_minor / total) * 100).toFixed(1) : "0";
            return (
              <li key={row.key} className="flex items-center gap-2 text-sm">
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: categoryColor(row.key) }}
                />
                <span className="text-white flex-1 truncate font-medium">
                  {capitalize(row.key)}
                </span>
                <span className="text-gray-400 tabular-nums text-xs">
                  {formatINR(row.amount_minor)}
                </span>
                <span className="text-gray-500 text-xs w-10 text-right tabular-nums">
                  {pct}%
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
