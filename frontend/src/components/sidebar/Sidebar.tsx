"use client";

import * as React from "react";
import type { ChatSession } from "@/types/chat";
import type { MemoryInsight } from "@/state/useAppStore";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";

export function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
  onNewChat,
  onOpenSettings,
  memoryEnabled,
  semanticInsights,
  relationalContext
}: {
  sessions: ChatSession[];
  currentSessionId?: string;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onNewChat: () => void;
  onOpenSettings: () => void;
  memoryEnabled: boolean;
  semanticInsights: MemoryInsight[];
  relationalContext?: {
    name?: string;
    role?: string;
    skills?: string[];
  };
}) {
  const [search, setSearch] = React.useState("");
  const filtered = sessions.filter((s) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    if (s.title.toLowerCase().includes(q)) return true;
    return s.messages.some((m) => {
      if (m.role === "user") {
        const t = m.input?.text ?? "";
        return t.toLowerCase().includes(q);
      }
      if (m.role === "assistant") {
        if (m.error && m.error.toLowerCase().includes(q)) return true;
        const maybe = m.output?.result ? JSON.stringify(m.output.result).slice(0, 2000) : "";
        return maybe.toLowerCase().includes(q);
      }
      return false;
    });
  });

  return (
    <aside className="w-[320px] flex-col border-r border-slate-200 bg-slate-50/30 dark:border-slate-800 dark:bg-slate-950/30">
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-900 dark:text-slate-50">Structured Extraction</div>
          <div className="truncate text-xs text-slate-500 dark:text-slate-400">Intelligence Engine</div>
        </div>
        <Button variant="ghost" size="icon" onClick={onOpenSettings} aria-label="Open settings">
          <span className="text-sm">⚙</span>
        </Button>
      </div>

      <div className="px-4 pb-3">
        <Button className="w-full" onClick={onNewChat}>
          New chat
        </Button>
      </div>

      <Separator />

      <ScrollArea className="flex-1 px-4 py-3">
        <div className="space-y-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Episodic memory
            </div>
            <div className="mt-2">
              <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search conversations..." />
            </div>
          </div>

          <div className="space-y-2">
            {filtered.slice(0, 40).map((s) => {
              const active = s.id === currentSessionId || (!currentSessionId && s.id === sessions[0]?.id);
              return (
                <div key={s.id} className="group relative">
                  <button
                    className={[
                      "w-full rounded-xl border px-3 py-2 text-left text-sm transition-colors",
                      active
                        ? "border-slate-900 bg-slate-900 text-slate-50"
                        : "border-slate-200 bg-white/60 hover:bg-white dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-100 dark:hover:bg-slate-950"
                    ].join(" ")}
                    onClick={() => onSelectSession(s.id)}
                  >
                    <div className="pr-6 truncate font-medium">{s.title}</div>
                    <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {s.messages.length} turns
                    </div>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(s.id);
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:bg-red-100 hover:text-red-600 dark:text-slate-500 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors"
                    title="Delete Chat"
                    aria-label="Delete chat"
                  >
                    🗑
                  </button>
                </div>
              );
            })}
          </div>

          {memoryEnabled ? (
            <div className="space-y-4">
              <Separator />
              
              {/* Relational Profile (Neo4j Showcase) */}
              {relationalContext && (relationalContext.name || relationalContext.role) && (
                <div className="rounded-xl border border-blue-100 bg-blue-50/30 p-3 dark:border-blue-900/30 dark:bg-blue-900/10">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                    Relational Profile (Graph)
                  </div>
                  <div className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-50">
                    {relationalContext.name || "Anonymous User"}
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-400">
                    {relationalContext.role || "Professional"}
                  </div>
                  {relationalContext.skills && relationalContext.skills.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {relationalContext.skills.slice(0, 5).map((s) => (
                        <span key={s} className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Semantic memory
              </div>
              {semanticInsights.length === 0 ? (
                <div className="text-xs text-slate-500 dark:text-slate-400">No semantic insights yet.</div>
              ) : (
                (() => {
                  const grouped = semanticInsights.reduce(
                    (acc, t) => {
                      acc[t.category] = acc[t.category] ?? [];
                      acc[t.category].push(t);
                      return acc;
                    },
                    {} as Record<string, typeof semanticInsights>
                  );
                  const categories: { key: string; label: string }[] = [
                    { key: "skill", label: "Skills" },
                    { key: "entity", label: "Entities" },
                    { key: "other", label: "Insights" }
                  ];
                  return (
                    <div className="space-y-3">
                      {categories.map((c) => {
                        const items = (grouped[c.key] ?? []).slice(0, 12);
                        if (items.length === 0) return null;
                        return (
                          <div key={c.key}>
                            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                              {c.label} ({items.length})
                            </div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {items.map((t) => (
                                <span
                                  key={t.id}
                                  className="max-w-full cursor-default rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200"
                                  title={t.category}
                                >
                                  {t.tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()
              )}
            </div>
          ) : (
            <div className="text-xs text-slate-500 dark:text-slate-400">Memory is disabled in settings.</div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t border-slate-200 p-4 dark:border-slate-800">
        <Button variant="outline" className="w-full justify-start gap-2" onClick={onOpenSettings}>
          <span className="text-lg">👤</span>
          <span className="truncate">{currentSessionId ? "Account Settings" : "Sign in / Account"}</span>
        </Button>
      </div>
    </aside>
  );
}

