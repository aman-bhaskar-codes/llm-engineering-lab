"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/sidebar/Sidebar";
import type { ExtractionMode } from "@/types/extraction";
import { ChatArea } from "@/components/chat/ChatArea";
import { SettingsDialog } from "@/components/settings/SettingsDialog";
import { LoginDialog } from "@/components/settings/LoginDialog";
import { useAppStore } from "@/state/useAppStore";
import type { MemoryInsight } from "@/state/useAppStore";
import type { ExtractionApiResponse } from "@/types/extraction";
import { getConversation, getMemory, listConversations, deleteConversation, getRelationalContext } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const modeOptions: { value: ExtractionMode; label: string }[] = [
  { value: "simple", label: "Simple" },
  { value: "advanced", label: "Advanced" },
  { value: "reasoning", label: "Reasoning (Premium)" }
];

export function AppShell() {
  const sessions = useAppStore((s) => s.sessions);
  const currentSessionId = useAppStore((s) => s.currentSessionId);
  const setCurrentSessionId = useAppStore((s) => s.setCurrentSessionId);
  const createSession = useAppStore((s) => s.createSession);
  const settings = useAppStore((s) => s.settings);
  const memoryEnabled = settings.memoryEnabled;
  const semanticInsights = useAppStore((s) => s.memory.semanticInsights);
  const openSettings = useAppStore((s) => s.openSettings);
  const themeChoice = useAppStore((s) => s.theme);
  const token = useAppStore((s) => s.auth.token);
  const hydrateFromBackendConversations = useAppStore((s) => s.hydrateFromBackendConversations);
  const hydrateSessionMessages = useAppStore((s) => s.hydrateSessionMessages);
  const clearAllMemory = useAppStore((s) => s.clearAllMemory);
  const deleteSession = useAppStore((s) => s.deleteSession);
  const setRelationalContext = useAppStore((s) => s.setRelationalContext);
  const relationalContext = useAppStore((s) => s.memory.relationalContext);

  const { setTheme: setNextTheme } = useTheme();

  const activeSession = React.useMemo(() => {
    const id = currentSessionId ?? sessions[0]?.id;
    return sessions.find((s) => s.id === id) ?? sessions[0];
  }, [currentSessionId, sessions]);

  const [selectedMode, setSelectedMode] = React.useState<ExtractionMode>(settings.defaultMode);
  React.useEffect(() => {
    setSelectedMode(settings.defaultMode);
  }, [settings.defaultMode]);

  const [extractStatus, setExtractStatus] = React.useState<{ extracting: boolean; progress?: number }>({
    extracting: false
  });

  const [mobileSidebarOpen, setMobileSidebarOpen] = React.useState(false);
  const authUser = useAppStore((s) => s.auth.user);
  const openLogin = useAppStore((s) => s.openLogin);
  const closeLogin = useAppStore((s) => s.closeLogin);

  React.useEffect(() => {
    setNextTheme(themeChoice);
  }, [setNextTheme, themeChoice]);

  React.useEffect(() => {
    if (!authUser) openLogin();
    else closeLogin();
  }, [authUser, closeLogin, openLogin]);

  const addUserMessage = useAppStore((s) => s.addUserMessage);
  const addAssistantMessage = useAppStore((s) => s.addAssistantMessage);
  const upsertSemanticInsights = useAppStore((s) => s.upsertSemanticInsights);
  const setSessionBackendConversationId = useAppStore((s) => s.setSessionBackendConversationId);

  React.useEffect(() => {
    if (!token) return;

    const run = async () => {
      try {
        const conversations = await listConversations();
        hydrateFromBackendConversations(conversations);

        const mem = await getMemory();
        clearAllMemory();

        const semantic: MemoryInsight[] = (mem.semantic ?? []).flatMap((m): MemoryInsight[] => {
          const sourceId = m.source_extraction_id ?? "unknown";
          const createdAt = Date.now();

          if (m.key === "skills" && m.value?.skills) {
            const skills: string[] = Array.isArray(m.value.skills) ? m.value.skills : [];
            return skills.map((skill) => ({
              id: `skill:${sourceId}:${skill}`,
              tag: skill,
              category: "skill" as const,
              createdAt
            }));
          }

          if (m.key === "domain") {
            const domain = m.value?.domain ?? "unknown";
            return [
              {
                id: `domain:${sourceId}:${domain}`,
                tag: domain,
                category: "entity" as const,
                createdAt
              }
            ];
          }

          if (m.key === "role") {
            const role = m.value?.role ?? "unknown";
            return [
              {
                id: `role:${sourceId}:${role}`,
                tag: role,
                category: "entity" as const,
                createdAt
              }
            ];
          }

          if (m.key === "name") {
            const name = m.value?.name ?? "unknown";
            return [
              {
                id: `name:${sourceId}:${name}`,
                tag: name,
                category: "entity" as const,
                createdAt
              }
            ];
          }

          return [
            {
              id: `${m.key}:${sourceId}`,
              tag: m.key,
              category: "other" as const,
              createdAt
            }
          ];
        });

        upsertSemanticInsights(semantic);
        const rel = await getRelationalContext();
        setRelationalContext(rel.context);
      } catch {
        // Fail open.
      }
    };

    void run();
  }, [token, hydrateFromBackendConversations, clearAllMemory, upsertSemanticInsights]);

  async function handleDeleteChat(id: string) {
    if (!confirm("Are you sure you want to delete this chat?")) return;
    try {
      await deleteConversation(id);
      deleteSession(id);
    } catch {
      toast.error("Failed to delete chat.");
    }
  }


  async function handleComplete(payload: ExtractionApiResponse) {
    const result = payload.result;
    addAssistantMessage(activeSession.id, {
      role: "assistant",
      output: {
        mode: selectedMode,
        result
      }
    });

    if (payload.conversation_id) {
      setSessionBackendConversationId(activeSession.id, payload.conversation_id);

      try {
        const conv = await getConversation(String(payload.conversation_id));
        const messages = (conv.messages ?? []).map((m) => {
          if (m.role === "user") {
            return {
              id: m.id,
              role: "user" as const,
              createdAt: Date.parse(m.created_at),
              input: { text: m.content, attachment: { kind: "none" as const } }
            };
          }

          let parsed: any = {};
          try {
            parsed = JSON.parse(m.content);
          } catch {
            parsed = {};
          }
          // Handle standardized SaaS format
          const extracted = parsed?.result ?? parsed;

          return {
            id: m.id,
            role: "assistant" as const,
            createdAt: Date.parse(m.created_at),
            output: {
              mode: parsed?.mode ?? "simple",
              result: {
                data: extracted?.data ?? extracted ?? {},
                confidence: extracted?.confidence ?? 0.8,
                valid: extracted?.valid ?? true,
                issues: extracted?.issues ?? []
              }
            }
          };
        });

        hydrateSessionMessages({ sessionId: activeSession.id, title: conv.title, messages });
      } catch {
        // Fail open.
      }
    }

    if (memoryEnabled && payload.conversation_id) {
      try {
        const mem = await getMemory();
        clearAllMemory();

        const semantic: any[] = (mem.semantic ?? []).flatMap((m: any) => {
          const sourceId = m.source_extraction_id ?? "unknown";
          const createdAt = Date.now();

          if (m.key === "skills" && m.value?.skills) {
            const skills: string[] = Array.isArray(m.value.skills) ? m.value.skills : [];
            return skills.map((skill) => ({
              id: `skill:${sourceId}:${skill}`,
              tag: skill,
              category: "skill" as any,
              createdAt
            }));
          }

          if (m.key === "domain" || m.key === "role" || m.key === "name") {
            const val = m.value?.[m.key] ?? m.value ?? "unknown";
            return [
              {
                id: `${m.key}:${sourceId}:${val}`,
                tag: String(val),
                category: "entity" as any,
                createdAt
              }
            ];
          }

          return [
            {
              id: `${m.key}:${sourceId}`,
              tag: String(m.key),
              category: "other" as any,
              createdAt
            }
          ];
        });

        upsertSemanticInsights(semantic);

        const rel = await getRelationalContext();
        setRelationalContext(rel.context);
      } catch {
        // Fail open.
      }
    }
  }

  function handleStart(input: { text?: string; fileName?: string }) {
    addUserMessage(activeSession.id, {
      role: "user",
      input: {
        text: input.text,
        attachment: input.fileName ? { kind: "file", fileName: input.fileName } : { kind: "none" }
      }
    });
  }

  function handleError(message: string) {
    addAssistantMessage(activeSession.id, {
      role: "assistant",
      error: message
    });
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex h-screen overflow-hidden">
        <div className="hidden md:block">
          <Sidebar
            sessions={sessions}
            currentSessionId={activeSession.id}
            onDeleteSession={handleDeleteChat}
            onSelectSession={(id) => {
              setCurrentSessionId(String(id));
                void (async () => {
                  try {
                    const sess = sessions.find((s) => s.id === id);
                    const backendId = sess?.backendConversationId ?? id;
                    if (!backendId) return;
                    
                    const conv = await getConversation(String(backendId));
                    const messages = (conv.messages ?? []).map((m) => {
                      if (m.role === "user") {
                        return {
                          id: m.id,
                          role: "user" as const,
                          createdAt: Date.parse(m.created_at),
                          input: { text: m.content, attachment: { kind: "none" as const } }
                        };
                      }

                      let parsed: any = {};
                      try {
                        parsed = JSON.parse(m.content);
                      } catch {
                        parsed = {};
                      }
                      const extracted = parsed?.result ?? parsed;

                      return {
                        id: m.id,
                        role: "assistant" as const,
                        createdAt: Date.parse(m.created_at),
                        output: {
                          mode: "simple" as any,
                          result: {
                            data: extracted?.data ?? extracted ?? {},
                            confidence: extracted?.confidence,
                            valid: extracted?.valid,
                            issues: extracted?.issues
                          }
                        }
                      };
                    });

                    hydrateSessionMessages({ sessionId: id, title: conv.title, messages });
                  } catch {
                    // Fail open.
                  }
                })();
            }}
            onNewChat={createSession}
            onOpenSettings={openSettings}
            memoryEnabled={memoryEnabled}
            semanticInsights={semanticInsights}
            relationalContext={relationalContext}
          />
        </div>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white/60 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/40">
            <div className="flex items-center gap-3">
              <Button
                className="md:hidden"
                variant="secondary"
                onClick={() => setMobileSidebarOpen(true)}
              >
                History
              </Button>

              <div className="hidden sm:block">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Extraction mode
                </div>
                <div className="mt-1">
                  <Select value={selectedMode} onValueChange={(v) => setSelectedMode(v as ExtractionMode)}>
                    <SelectTrigger className="w-[280px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {modeOptions.map((o) => (
                        <SelectItem key={o.value} value={o.value}>
                          {o.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" onClick={openSettings}>
                Settings
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  const next = themeChoice === "dark" ? "light" : "dark";
                  useAppStore.getState().setTheme(next);
                  setNextTheme(next);
                }}
                className="hidden sm:inline-flex"
              >
                {themeChoice === "dark" ? "Dark" : "Light"}
              </Button>
            </div>
          </header>

          {extractStatus.extracting && typeof extractStatus.progress === "number" ? (
            <div className="px-4 py-2">
              <Progress value={extractStatus.progress} />
            </div>
          ) : null}

          <div className="flex-1">
            <ChatArea
              session={activeSession}
              mode={selectedMode}
              outputFormat={settings.outputFormat}
              memoryEnabled={memoryEnabled}
              onStartExtraction={handleStart}
              onCompleteExtraction={handleComplete}
              onErrorExtraction={handleError}
              onStatusChange={(s) => setExtractStatus(s)}
            />
          </div>
        </div>
      </div>

      <SettingsDialog />
      <LoginDialog />

      <Dialog open={mobileSidebarOpen} onOpenChange={(v) => setMobileSidebarOpen(v)}>
        <DialogContent className="max-w-[90vw] p-0">
          <DialogHeader className="p-4">
            <DialogTitle>Conversations</DialogTitle>
          </DialogHeader>
          <div className="px-4 pb-4">
            <Sidebar
              sessions={sessions}
              currentSessionId={activeSession.id}
              onDeleteSession={handleDeleteChat}
              onSelectSession={(id) => {
                const sid = String(id);
                setCurrentSessionId(sid);
                  void (async () => {
                    try {
                      const sess = sessions.find((s) => s.id === sid);
                      const backendId = sess?.backendConversationId ?? sid;
                      const conv = await getConversation(String(backendId));
                      const messages = (conv.messages ?? []).map((m) => {
                        if (m.role === "user") {
                          return {
                            id: m.id,
                            role: "user" as const,
                            createdAt: Date.parse(m.created_at),
                            input: { text: m.content, attachment: { kind: "none" as const } }
                          };
                        }

                        let parsed: any = {};
                        try {
                          parsed = JSON.parse(m.content);
                        } catch {
                          parsed = {};
                        }
                        const extracted = parsed?.result ?? parsed;

                        return {
                          id: m.id,
                          role: "assistant" as const,
                          createdAt: Date.parse(m.created_at),
                          output: {
                            mode: parsed?.mode ?? "simple",
                            result: {
                              data: extracted?.data ?? extracted ?? {},
                              confidence: extracted?.confidence ?? 0.8,
                              valid: extracted?.valid ?? true,
                              issues: extracted?.issues ?? []
                            }
                          }
                        };
                      });

                      hydrateSessionMessages({ sessionId: sid, title: conv.title, messages });
                    } catch {
                      // Fail open.
                    }
                  })();
                setMobileSidebarOpen(false);
              }}
              onNewChat={() => {
                createSession();
                setMobileSidebarOpen(false);
              }}
              onOpenSettings={() => {
                openSettings();
                setMobileSidebarOpen(false);
              }}
              memoryEnabled={memoryEnabled}
              semanticInsights={semanticInsights}
              relationalContext={relationalContext}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

