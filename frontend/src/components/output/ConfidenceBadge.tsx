"use client";

import * as React from "react";
import type { Verification } from "@/types/extraction";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

function variantForConfidence(conf: number) {
  if (conf >= 0.8) return "default";
  if (conf >= 0.55) return "secondary";
  return "destructive";
}

export function ConfidenceBadge({ confidence, valid }: { confidence?: number; valid?: boolean }) {
  const conf = typeof confidence === "number" ? confidence : undefined;
  const v = typeof valid === "boolean" ? valid : undefined;

  if (conf === undefined) {
    return <Badge variant="outline">Confidence: n/a</Badge>;
  }

  const pct = Math.round(conf * 100);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <Badge variant={variantForConfidence(conf)}>
          Confidence: {pct}%
        </Badge>
        {v !== undefined ? (
          <Badge variant={v ? "default" : "destructive"}>{v ? "Verified" : "Flagged"}</Badge>
        ) : null}
      </div>
      <Progress value={pct} />
    </div>
  );
}

