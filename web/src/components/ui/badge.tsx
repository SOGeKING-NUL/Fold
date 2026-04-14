import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors",
  {
    variants: {
      variant: {
        expense: "bg-red-50 text-red-600",
        income: "bg-emerald-50 text-emerald-600",
        investment: "bg-blue-50 text-blue-600",
        transfer: "bg-amber-50 text-amber-600",
        default: "bg-gray-100 text-gray-600",
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
