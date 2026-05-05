"use client";

import { cn } from "@/lib/utils";

interface Props {
  period: "weekly" | "monthly";
  onChange: (p: "weekly" | "monthly") => void;
}

export default function PeriodToggle({ period, onChange }: Props) {
  return (
    <div className="flex rounded-xl bg-[#f5f5f5] p-1 w-fit border border-[#e5e5e5]">
      {(["weekly", "monthly"] as const).map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={cn(
            "px-4 py-1.5 text-sm font-medium rounded-lg transition-all cursor-pointer",
            period === p
              ? "bg-[#156d95] text-white shadow-sm"
              : "text-[#666666] hover:text-[#202020]"
          )}
        >
          {p === "weekly" ? "Week" : "Month"}
        </button>
      ))}
    </div>
  );
}
