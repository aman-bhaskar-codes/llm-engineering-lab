import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ChatMessage, ChatSession } from "@/types/chat";
import type { ExtractionMode, OutputFormat } from "@/types/extraction";

export type ThemeChoice = "light" | "dark" | "system";

export type AppSettings = {
  modelName: string;
  defaultMode: ExtractionMode;
  outputFormat: OutputFormat;
  memoryEnabled: boolean;
};

export type AuthState = {
  user?: {
    name: string;
    email?: string;
  };
  token?: string;
  userId?: string;
};

export type MemoryInsight = {
  id: string;
  tag: string;
  category: "entity" | "skill" | "other";
  confidenceHint?: number;
  createdAt: number;
};

export type AppState = {
  theme: ThemeChoice;
  settings: AppSettings;
  auth: AuthState;

  sessions: ChatSession[];
  currentSessionId?: string;

  memory: {
    episodic: {
      // Saved as sessions list (history). Semantic is derived separately.
    };
    semanticInsights: MemoryInsight[];
    relationalContext: {
      name?: string;
      role?: string;
      skills?: string[];
    };
  };

  ui: {
    settingsOpen: boolean;
    loginOpen: boolean;
  };

  // Actions
  setTheme: (theme: ThemeChoice) => void;
  updateSettings: (next: Partial<AppSettings>) => void;
  openSettings: () => void;
  closeSettings: () => void;
  openLogin: () => void;
  closeLogin: () => void;

  login: (name: string) => void;
  logout: () => void;

  createSession: () => void;
  deleteSession: (id: string) => void;
  setCurrentSessionId: (id: string | undefined) => void;

  addUserMessage: (sessionId: string, message: Omit<ChatMessage, "id" | "createdAt">) => void;
  addAssistantMessage: (
    sessionId: string,
    message: Omit<ChatMessage, "id" | "createdAt">
  ) => void;

  upsertSemanticInsights: (insights: MemoryInsight[]) => void;
  setRelationalContext: (context: { name?: string; role?: string; skills?: string[] }) => void;
  clearAllMemory: () => void;

  setAuthToken: (payload: {
    token: string;
    userId: string;
    name: string;
    email?: string;
  }) => void;
  hydrateFromBackendConversations: (conversations: Array<{
    id: string;
    title: string;
    created_at: string;
  }>) => void;
  hydrateSessionMessages: (params: {
    sessionId: string;
    title: string;
    messages: ChatMessage[];
  }) => void;

  setSessionBackendConversationId: (sessionId: string, backendConversationId: string) => void;
};

function now() {
  return Date.now();
}

function makeId(prefix: string) {
  return `${prefix}_${crypto.randomUUID()}`;
}

function createEmptySession(): ChatSession {
  const id = makeId("sess");
  return {
    id,
    title: "New chat",
    backendConversationId: undefined,
    createdAt: now(),
    updatedAt: now(),
    messages: []
  };
}

const defaultSettings: AppSettings = {
  modelName: "qwen2.5:3b",
  defaultMode: "simple",
  outputFormat: "strict",
  memoryEnabled: true
};

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: "system",
      settings: defaultSettings,
      auth: {},

      sessions: [], // Initialize empty to prevent hydration mismatch
      currentSessionId: undefined,

      memory: {
        episodic: {},
        semanticInsights: [],
        relationalContext: {}
      },

      ui: {
        settingsOpen: false,
        loginOpen: false
      },

      setTheme: (theme) => set({ theme }),
      updateSettings: (next) => set((s) => ({ settings: { ...s.settings, ...next } })),
      openSettings: () => set((s) => ({ ui: { ...s.ui, settingsOpen: true } })),
      closeSettings: () => set((s) => ({ ui: { ...s.ui, settingsOpen: false } })),
      openLogin: () => set((s) => ({ ui: { ...s.ui, loginOpen: true } })),
      closeLogin: () => set((s) => ({ ui: { ...s.ui, loginOpen: false } })),

      login: (name) => set({ auth: { user: { name } }, ui: { ...get().ui, loginOpen: false } }),
      logout: () =>
        set({
          auth: {},
          ui: { ...get().ui, loginOpen: true }
        }),

      setAuthToken: ({ token, userId, name, email }) =>
        set({
          auth: { token, userId, user: { name, email } },
          ui: { ...get().ui, loginOpen: false }
        }),

      hydrateFromBackendConversations: (conversations) =>
        set((s) => {
          const sessions: ChatSession[] =
            conversations.length > 0
              ? conversations.map((c) => ({
                  id: c.id,
                  backendConversationId: c.id,
                  title: c.title,
                  createdAt: Date.parse(c.created_at),
                  updatedAt: Date.parse(c.created_at),
                  messages: []
                }))
              : [createEmptySession()];

          return { sessions, currentSessionId: sessions[0].id };
        }),

      hydrateSessionMessages: ({ sessionId, title, messages }) =>
        set((s) => ({
          sessions: s.sessions.map((sess) => {
            if (sess.id !== sessionId) return sess;
            return {
              ...sess,
              backendConversationId: sess.backendConversationId ?? sessionId,
              title,
              messages,
              updatedAt: now()
            };
          })
        })),

      setSessionBackendConversationId: (sessionId, backendConversationId) =>
        set((s) => ({
          sessions: s.sessions.map((sess) =>
            sess.id === sessionId ? { ...sess, backendConversationId } : sess
          )
        })),

      createSession: () => {
        const session = createEmptySession();
        set((s) => ({
          sessions: [session, ...s.sessions],
          currentSessionId: session.id
        }));
      },

      deleteSession: (id) =>
        set((s) => {
          const sessions = s.sessions.filter((sess) => sess.id !== id);
          let currentId = s.currentSessionId;
          if (currentId === id) {
            currentId = sessions.length > 0 ? sessions[0].id : undefined;
          }
          if (sessions.length === 0) {
            const newSess = createEmptySession();
            return { sessions: [newSess], currentSessionId: newSess.id };
          }
          return { sessions, currentSessionId: currentId };
        }),

      setCurrentSessionId: (id) => set({ currentSessionId: id }),

      addUserMessage: (sessionId, message) => {
        set((s) => ({
          sessions: s.sessions.map((sess) => {
            if (sess.id !== sessionId) return sess;
            const updated: ChatSession = {
              ...sess,
              updatedAt: now(),
              title:
                sess.messages.length === 0
                  ? message.input?.text?.slice(0, 40) || "New chat"
                  : sess.title,
              messages: [
                ...sess.messages,
                {
                  id: makeId("msg"),
                  createdAt: now(),
                  ...message
                }
              ]
            };
            return updated;
          })
        }));
      },

      addAssistantMessage: (sessionId, message) => {
        set((s) => ({
          sessions: s.sessions.map((sess) => {
            if (sess.id !== sessionId) return sess;
            const updated: ChatSession = {
              ...sess,
              updatedAt: now(),
              messages: [
                ...sess.messages,
                {
                  id: makeId("msg"),
                  createdAt: now(),
                  ...message
                }
              ]
            };
            return updated;
          })
        }));
      },

      upsertSemanticInsights: (insights) =>
        set((s) => {
          const existing = new Map(s.memory.semanticInsights.map((i) => [i.id, i]));
          for (const i of insights) existing.set(i.id, i);
          return {
            memory: {
              ...s.memory,
              semanticInsights: Array.from(existing.values()).slice(0, 500)
            }
          };
        }),

      setRelationalContext: (context) =>
        set((s) => ({
          memory: { ...s.memory, relationalContext: context }
        })),

      clearAllMemory: () =>
        set((s) => ({
          memory: { ...s.memory, semanticInsights: [], relationalContext: {} }
        }))
    }),
    {
      name: "structuredExtractionIntelligence",
      storage: createJSONStorage(() => {
        if (typeof window === "undefined") {
          return {
            getItem: () => null,
            setItem: () => {},
            removeItem: () => {}
          };
        }
        return localStorage;
      }),
      partialize: (state) => ({
        theme: state.theme,
        settings: state.settings,
        auth: state.auth,
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
        memory: state.memory,
        ui: { settingsOpen: false, loginOpen: false }
      })
    }
  )
);

