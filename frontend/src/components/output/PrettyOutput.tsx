"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";

function renderPrimitive(v: unknown) {
  if (typeof v === "string") return <span className="text-slate-900 dark:text-slate-50">{v}</span>;
  if (typeof v === "number") return <span>{v}</span>;
  if (typeof v === "boolean") return <span>{v ? "true" : "false"}</span>;
  if (v === null) return <span className="text-slate-500 dark:text-slate-400">null</span>;
  return <span className="text-slate-500 dark:text-slate-400">{String(v)}</span>;
}

export function PrettyOutput({ data }: { data: Record<string, any> }) {
  const entries = Object.entries(data ?? {});

  if (entries.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
        No structured output yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map(([key, value]) => {
        if (Array.isArray(value)) {
          return (
            <div key={key} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="text-sm font-semibold capitalize text-slate-900 dark:text-slate-50">{key}</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {value.length === 0 ? (
                  <span className="text-slate-500 dark:text-slate-400">[]</span>
                ) : (
                  value.slice(0, 20).map((item, idx) => (
                    <Badge key={`${key}_${idx}`} variant="secondary">
                      {typeof item === "string" ? item : JSON.stringify(item)}
                    </Badge>
                  ))
                )}
              </div>
            </div>
          );
        }

        if (value && typeof value === "object") {
          return (
            <div key={key} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="text-sm font-semibold capitalize text-slate-900 dark:text-slate-50">{key}</div>
              <div className="mt-2 space-y-2 text-sm">
                {Object.entries(value as Record<string, any>).slice(0, 10).map(([k, v]) => (
                  <div key={k} className="flex items-start justify-between gap-3">
                    <div className="font-medium text-slate-600 dark:text-slate-300">{k}</div>
                    <div className="max-w-[65%] text-right text-slate-900 dark:text-slate-50">{renderPrimitive(v)}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        }

        return (
          <div key={key} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <div className="text-sm font-semibold capitalize text-slate-900 dark:text-slate-50">{key}</div>
            <div className="mt-2 text-sm text-slate-900 dark:text-slate-50">{renderPrimitive(value)}</div>
          </div>
        );
      })}
    </div>
  );
}

