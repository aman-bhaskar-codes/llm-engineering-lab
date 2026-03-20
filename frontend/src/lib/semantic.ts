import type { ExtractionResult } from "@/types/extraction";
import type { MemoryInsight } from "@/state/useAppStore";

function safeString(v: unknown): string | null {
  if (typeof v !== "string") return null;
  const s = v.trim();
  if (!s) return null;
  return s.length > 120 ? s.slice(0, 120) : s;
}

export function extractSemanticInsights(
  result: ExtractionResult,
  createdAt: number
): MemoryInsight[] {
  const data = result.data ?? {};
  if (!data || typeof data !== "object") return [];

  const insights: MemoryInsight[] = [];

  const pushUnique = (insight: MemoryInsight) => {
    if (insights.some((i) => i.tag === insight.tag && i.category === insight.category)) return;
    insights.push(insight);
  };

  const makeId = () => `ins_${crypto.randomUUID()}`;
  const confidenceHint = typeof result.confidence === "number" ? result.confidence : undefined;

  const skillsVal = (data as any).skills;
  if (Array.isArray(skillsVal)) {
    for (const sk of skillsVal) {
      const s = safeString(sk);
      if (!s) continue;
      pushUnique({
        id: makeId(),
        tag: s,
        category: "skill",
        confidenceHint,
        createdAt
      });
    }
  }

  // Common "entity-like" fields
  for (const key of ["name", "role", "education"]) {
    const v = (data as any)[key];
    const s = safeString(v);
    if (!s) continue;
    pushUnique({
      id: makeId(),
      tag: s,
      category: "entity",
      confidenceHint,
      createdAt
    });
  }

  // Fallback: pick a few short string values for tags
  for (const [k, v] of Object.entries(data)) {
    if (insights.length >= 12) break;
    const s = safeString(v);
    if (!s) continue;
    if (s.length > 45) continue;
    pushUnique({
      id: makeId(),
      tag: s,
      category: k === "summary" ? "entity" : "other",
      confidenceHint,
      createdAt
    });
  }

  return insights;
}

