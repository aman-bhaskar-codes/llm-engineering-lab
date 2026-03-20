import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  variant?: "default" | "secondary" | "destructive" | "outline";
}) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
        variant === "default" &&
          "border-slate-200 bg-slate-900 text-slate-50 dark:border-slate-800 dark:bg-slate-100 dark:text-slate-900",
        variant === "secondary" &&
          "border-slate-200 bg-slate-100 text-slate-900 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-100",
        variant === "destructive" &&
          "border-red-200 bg-red-600 text-white dark:border-red-900 dark:bg-red-500",
        variant === "outline" &&
          "border-slate-200 bg-transparent text-slate-900 dark:border-slate-800 dark:text-slate-50",
        (!variant || variant === "default") && "border-slate-200 bg-slate-900 text-slate-50",
        className
      )}
      {...props}
    />
  );
}

