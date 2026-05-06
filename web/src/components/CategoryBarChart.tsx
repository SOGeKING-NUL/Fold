"use client";

import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { BreakdownRow } from "@/lib/api";
import { formatINR, categoryColor, capitalize } from "@/lib/format";

interface Props {
  data: BreakdownRow[];
}

export default function CategoryBarChart({ data }: Props) {
  if (!data.length) {
    return (
      <p className="text-gray-500 text-sm">No category data for this period.</p>
    );
  }

  const chartData = data.slice(0, 8).map((r) => ({
    name: capitalize(r.key),
    amount: r.amount_minor,
    color: categoryColor(r.key),
  }));

  const barHeight = Math.max(200, chartData.length * 40);

  return (
    <div className="w-full" style={{ minHeight: barHeight }}>
      <ResponsiveContainer width="100%" height={barHeight}>
        <BarChart data={chartData} layout="vertical" barCategoryGap="20%">
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.1)"
            horizontal={false}
          />
          <XAxis
            type="number"
            tickFormatter={(v) => formatINR(Number(v))}
            tick={{ fontSize: 10, fill: "#9ca3af" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12, fill: "#d1d5db" }}
            axisLine={false}
            tickLine={false}
            width={100}
          />
          <Tooltip
            formatter={(value) => formatINR(Number(value))}
            contentStyle={{
              backgroundColor: "rgba(0,0,0,0.9)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "0.75rem",
              fontSize: "0.75rem",
              color: "#fff",
            }}
          />
          <Bar dataKey="amount" radius={[0, 6, 6, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
