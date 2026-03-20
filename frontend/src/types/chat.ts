import type { ExtractionMode, ExtractionResult } from "@/types/extraction";

export type ChatRole = "user" | "assistant";

export type Attachment =
  | { kind: "file"; file?: File; fileName: string }
  | { kind: "none" };

export type ChatInput = {
  text?: string;
  attachment?: Attachment;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  createdAt: number;
  input?: ChatInput;
  output?: {
    mode: ExtractionMode;
    result: ExtractionResult;
  };
  error?: string;
};

export type ChatSession = {
  id: string;
  title: string;
  backendConversationId?: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
};

