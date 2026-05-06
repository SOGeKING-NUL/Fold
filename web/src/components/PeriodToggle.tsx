"use client";

import { cn } from "@/lib/utils";

interface Props {
  period: "weekly" | "monthly";
  onChange: (p: "weekly" | "monthly") => void;
}

export default function PeriodToggle({ period, onChange }: Props) {
  return (
    <div className="flex rounded-xl bg-white/5 p-1 w-fit border border-white/10 backdrop-blur-sm">
      {(["weekly", "monthly"] as const).map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={cn(
            "px-4 py-1.5 text-sm font-medium rounded-lg transition-all cursor-pointer",
            period === p
              ? "bg-[#1e3a8a] text-white shadow-sm"
              : "text-gray-300 hover:text-white"
          )}
        >
          {p === "weekly" ? "Week" : "Month"}
        </button>
      ))}
    </div>
  );
}
