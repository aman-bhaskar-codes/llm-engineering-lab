"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export function Switch({
  checked,
  onCheckedChange,
  disabled,
  className,
}: {
  checked: boolean;
  onCheckedChange: (next: boolean) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      className={cn(
        "relative inline-flex h-6 w-11 cursor-pointer items-center rounded-full border border-slate-200 bg-white transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-slate-200 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-800 dark:bg-slate-950",
        checked && "bg-slate-900 dark:bg-slate-100",
        className
      )}
      onClick={() => !disabled && onCheckedChange(!checked)}
    >
      <span
        className={cn(
          "inline-block h-5 w-5 transform rounded-full bg-slate-100 shadow transition-transform dark:bg-slate-900",
          checked && "translate-x-5"
        )}
      />
      <span className="sr-only">Toggle</span>
    </button>
  );
}

