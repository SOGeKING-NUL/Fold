"use client";

import { cn } from "@/lib/utils";

interface Props {
  period: "weekly" | "monthly";
  onChange: (p: "weekly" | "monthly") => void;
}

export default function PeriodToggle({ period, onChange }: Props) {
  return (
    <div className="flex rounded-xl bg-gray-100 p-0.5 w-fit">
      {(["weekly", "monthly"] as const).map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={cn(
            "px-4 py-1.5 text-sm font-medium rounded-lg transition-all",
            period === p
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          )}
        >
          {p === "weekly" ? "Week" : "Month"}
        </button>
      ))}
    </div>
  );
}
