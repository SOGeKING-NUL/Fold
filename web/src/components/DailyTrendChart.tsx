"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { DailyTrendPoint } from "@/lib/api";
import { formatINR } from "@/lib/format";

interface Props {
  data: DailyTrendPoint[];
}

function formatDay(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export default function DailyTrendChart({ data }: Props) {
  if (!data.length) {
    return (
      <p className="text-[#999999] text-sm">No trend data for this period.</p>
    );
  }

  const chartData = data.map((p) => ({
    day: formatDay(p.day),
    Expenses: p.expense_minor,
    Income: p.income_minor,
  }));

  return (
    <div className="w-full" style={{ minHeight: 280 }}>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="incGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis
            dataKey="day"
            tick={{ fontSize: 11, fill: "#999999" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={(v) => formatINR(Number(v))}
            tick={{ fontSize: 10, fill: "#999999" }}
            axisLine={false}
            tickLine={false}
            width={72}
          />
          <Tooltip
            formatter={(value) => formatINR(Number(value))}
            contentStyle={{
              backgroundColor: "#ffffff",
              border: "1px solid #e5e5e5",
              borderRadius: "0.75rem",
              fontSize: "0.75rem",
              boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
            }}
          />
          <Area
            type="monotone"
            dataKey="Expenses"
            stroke="#ef4444"
            strokeWidth={2.5}
            fill="url(#expGrad)"
            dot={{ r: 3, fill: "#ef4444", strokeWidth: 0 }}
            activeDot={{ r: 5, fill: "#ef4444" }}
          />
          <Area
            type="monotone"
            dataKey="Income"
            stroke="#10b981"
            strokeWidth={2.5}
            fill="url(#incGrad)"
            dot={{ r: 3, fill: "#10b981", strokeWidth: 0 }}
            activeDot={{ r: 5, fill: "#10b981" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
