"use client";

import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { DashboardSummary } from "@/lib/api";
import { formatINR } from "@/lib/format";

interface Props {
  summary: DashboardSummary;
}

export default function SpendVsIncomeChart({ summary }: Props) {
  const data = [
    { name: "Income", value: summary.income_minor, fill: "#10b981" },
    { name: "Expenses", value: summary.expense_minor, fill: "#ef4444" },
    { name: "Investment", value: summary.investment_minor, fill: "#3b82f6" },
  ];

  return (
    <div className="w-full" style={{ minHeight: 240 }}>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} barCategoryGap="30%">
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => formatINR(Number(v))}
            tick={{ fontSize: 10, fill: "#9ca3af" }}
            axisLine={false}
            tickLine={false}
            width={80}
          />
          <Tooltip
            formatter={(value) => formatINR(Number(value))}
            contentStyle={{
              backgroundColor: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: "0.75rem",
              fontSize: "0.75rem",
              boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05)",
            }}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: "0.75rem", color: "#6b7280" }}
          />
          <Bar dataKey="value" radius={[8, 8, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
