import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex max-w-full items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold leading-tight", {
  variants: {
    variant: {
      default: "border-cyan-300/40 bg-cyan-300/15 text-cyan-100",
      success: "border-emerald-300/40 bg-emerald-300/15 text-emerald-100",
      warning: "border-amber-300/40 bg-amber-300/15 text-amber-100",
      destructive: "border-red-300/40 bg-red-300/15 text-red-100",
      muted: "border-border bg-muted text-muted-foreground"
    }
  },
  defaultVariants: { variant: "default" }
});

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
