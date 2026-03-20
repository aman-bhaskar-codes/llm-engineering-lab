"use client";

import * as React from "react";
import type { ExtractionMode, OutputFormat, ExtractionResult } from "@/types/extraction";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { JsonViewer } from "@/components/output/JsonViewer";
import { PrettyOutput } from "@/components/output/PrettyOutput";
import { ReasoningOutput } from "@/components/output/ReasoningOutput";

export function OutputTabs({
  mode,
  result,
  outputFormat
}: {
  mode: ExtractionMode;
  result: ExtractionResult;
  outputFormat: OutputFormat;
}) {
  const data = React.useMemo(() => result.data ?? {}, [result.data]);

  const inferred = React.useMemo(() => {
    if (mode !== "advanced") return null;

    const expYearsRaw = (data as any).experience_years;
    const expYears =
      typeof expYearsRaw === "number" && Number.isFinite(expYearsRaw)
        ? expYearsRaw
        : typeof expYearsRaw === "string"
          ? (() => {
              const n = Number.parseFloat(expYearsRaw);
              return Number.isFinite(n) ? n : null;
            })()
          : null;
    const skills = (data as any).skills;
    const skillsArr = Array.isArray(skills) ? skills.filter((s: any) => typeof s === "string") : [];

    const expBucket =
      expYears === null
        ? null
        : expYears < 2
          ? "Junior"
          : expYears < 5
            ? "Mid"
            : expYears < 9
              ? "Senior"
              : "Staff+";

    const summary = typeof (data as any).summary === "string" ? String((data as any).summary) : "";
    const summaryShort = summary ? summary.slice(0, 160) : null;

    return {
      exp_years_inferred: expYears,
      seniority: expBucket,
      skills_count: skillsArr.length,
      summary_short: summaryShort
    };
  }, [data, mode]);

  const jsonValue = React.useMemo(() => {
    const base: Record<string, any> = { ...data };

    if (inferred && mode === "advanced") {
      base._inferred = inferred;
    }

    if (outputFormat === "enriched") {
      base._metadata = {
        mode,
        confidence: result.confidence,
        valid: result.valid,
        issues: result.issues
      };
    }

    return base;
  }, [data, inferred, mode, outputFormat, result.confidence, result.issues, result.valid]);

  const prettyData = jsonValue as Record<string, any>;

  const showReasoning = mode === "reasoning";

  return (
    <Tabs defaultValue="json">
      <TabsList className="w-full justify-start">
        <TabsTrigger value="json">JSON</TabsTrigger>
        <TabsTrigger value="pretty">Pretty</TabsTrigger>
        {showReasoning ? <TabsTrigger value="reasoning">Reasoning</TabsTrigger> : null}
      </TabsList>

      <TabsContent value="json" className="mt-3">
        <JsonViewer value={jsonValue} />
      </TabsContent>

      <TabsContent value="pretty" className="mt-3">
        <PrettyOutput data={prettyData} />
      </TabsContent>

      {showReasoning ? (
        <TabsContent value="reasoning" className="mt-3">
          <ReasoningOutput result={result} />
        </TabsContent>
      ) : null}
    </Tabs>
  );
}

