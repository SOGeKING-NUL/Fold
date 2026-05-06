import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors",
  {
    variants: {
      variant: {
        expense: "bg-red-500/10 text-red-300 border-red-500/20",
        income: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
        investment: "bg-blue-500/10 text-blue-300 border-blue-500/20",
        transfer: "bg-amber-500/10 text-amber-300 border-amber-500/20",
        default: "bg-white/5 text-gray-300 border-white/10",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
