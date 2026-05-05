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
              ? "bg-gray-700 text-white shadow-sm"
              : "text-gray-400 hover:text-gray-200"
          )}
        >
          {p === "weekly" ? "Week" : "Month"}
        </button>
      ))}
    </div>
  );
}
