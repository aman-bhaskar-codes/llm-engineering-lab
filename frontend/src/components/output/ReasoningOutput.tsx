"use client";

import * as React from "react";
import type { ExtractionResult } from "@/types/extraction";
import { ConfidenceBadge } from "@/components/output/ConfidenceBadge";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export function ReasoningOutput({ result }: { result: ExtractionResult }) {
  const issues = React.useMemo(() => result.issues ?? [], [result.issues]);
  const valid = typeof result.valid === "boolean" ? result.valid : undefined;
  const explanation = React.useMemo(() => {
    const conf = typeof result.confidence === "number" ? result.confidence : null;
    const pct = conf === null ? null : Math.round(conf * 100);

    if (valid === true && issues.length === 0) {
      return `High confidence extraction: the structured fields appear consistent with the source text${pct !== null ? ` (confidence ${pct}%).` : "."}`;
    }

    if (valid === false && issues.length > 0) {
      const top = issues.slice(0, 3).join("; ");
      return `Verification flagged potential mismatches${pct !== null ? ` (confidence ${pct}%).` : "."} Key issues: ${top}`;
    }

    if (issues.length > 0) {
      const top = issues.slice(0, 3).join("; ");
      return `Verification reported potential issues${pct !== null ? ` (confidence ${pct}%).` : "."} Key issues: ${top}`;
    }

    return `The extraction was verified with a confidence score${pct !== null ? ` of ${pct}%.` : "."}`;
  }, [issues, result.confidence, valid]);

  return (
    <div className="space-y-4">
      <ConfidenceBadge confidence={result.confidence} valid={result.valid} />

      <Separator />

      <div>
        <div className="flex items-center gap-2">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">Verification</div>
          {valid !== undefined ? (
            <Badge variant={valid ? "default" : "destructive"}>{valid ? "Valid" : "Issues found"}</Badge>
          ) : (
            <Badge variant="outline">Unverified</Badge>
          )}
        </div>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{explanation}</p>
      </div>

      <div>
        <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">Issues</div>
        {issues.length === 0 ? (
          <div className="mt-2 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
            No issues reported by verification.
          </div>
        ) : (
          <ul className="mt-2 space-y-2">
            {issues.slice(0, 20).map((i, idx) => (
              <li
                key={`${idx}_${i}`}
                className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200"
              >
                {i}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

