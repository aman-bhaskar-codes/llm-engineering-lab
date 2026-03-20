"use client";

import { jsPDF } from "jspdf";
import type { ExtractionMode, ExtractionApiResponse } from "@/types/extraction";
import { useAppStore } from "@/state/useAppStore";

const DEFAULT_BASE_URL = "http://localhost:8000/api/v1";
const DEFAULT_SCHEMA = {
  name: "string",
  role: "string",
  skills: "list[string]",
  experience_years: "int",
  education: "string",
  summary: "string"
};

function getBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;
}

function getAuthHeader(): Record<string, string> {
  const token = useAppStore.getState().auth.token;
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export async function healthCheck() {
  const res = await fetch(`${getBaseUrl().replace(/\/api\/v1$/, "")}/health`);
  if (!res.ok) throw new Error(`Health check failed (${res.status})`);
  return res.json();
}

export type ExtractProgress = (progress: number) => void;

/**
 * PDF / File Extraction (Advanced/Reasoning Mode)
 */
export async function extractPdf(
  file: File,
  onProgress?: ExtractProgress,
  conversationId?: string
): Promise<ExtractionApiResponse> {
  return await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${getBaseUrl()}/extract-file`, true);
    const headers = getAuthHeader();
    const token = headers.Authorization;
    if (token) xhr.setRequestHeader("Authorization", token);

    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const pct = Math.round((e.loaded / e.total) * 100);
      onProgress?.(Math.max(0, Math.min(100, pct)));
    };

    xhr.onload = () => {
      try {
        if (xhr.status < 200 || xhr.status >= 300) {
          console.error(`File Upload failed: ${xhr.status} ${xhr.responseText}`);
          return reject(new Error(`Request failed (${xhr.status})`));
        }
        const body = JSON.parse(xhr.responseText);
        resolve(body as ExtractionApiResponse);
      } catch (err) {
        reject(err);
      }
    };

    xhr.onerror = () => reject(new Error("Network error during file extraction"));

    const formData = new FormData();
    formData.append("file", file, file.name);
    if (conversationId) {
      formData.append("conversation_id", conversationId);
    }
    xhr.send(formData);
  });
}

/**
 * Text Extraction (Simple Mode - Direct JSON)
 */
export async function extractTextViaJsonEndpoint(
  text: string,
  mode: ExtractionMode,
  conversationId?: string
): Promise<ExtractionApiResponse> {
  const res = await fetch(`${getBaseUrl()}/extract`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json", 
      ...(getAuthHeader() as any) 
    },
    body: JSON.stringify({
      text,
      mode,
      schema: DEFAULT_SCHEMA,
      conversation_id: conversationId
    })
  });

  if (!res.ok) {
    throw new Error(`Extraction failed (${res.status})`);
  }
  return (await res.json()) as ExtractionApiResponse;
}

/**
 * Unified Extraction Entry Point
 */
export async function extractText(
  text: string,
  mode: ExtractionMode,
  onProgress?: ExtractProgress,
  conversationId?: string
): Promise<ExtractionApiResponse> {
  onProgress?.(10);
  
  // Simple Mode is ALWAYS direct Text -> JSON
  if (mode === "simple") {
    const result = await extractTextViaJsonEndpoint(text, mode, conversationId);
    onProgress?.(100);
    return result;
  }

  // Fallback for Advanced/Reasoning (PDF-based for legacy/OCR support)
  onProgress?.(20);
  const file = createPdfFileFromText(text);
  const result = await extractPdf(
    file,
    (p) => onProgress?.(20 + Math.round(p * 0.8)),
    conversationId
  );
  return result;
}

function createPdfFileFromText(text: string): File {
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  const margin = 40;
  const lines = doc.splitTextToSize(text, doc.internal.pageSize.getWidth() - margin * 2);
  doc.text(lines, margin, margin);
  const blob = doc.output("blob");
  return new File([blob], "input.pdf", { type: "application/pdf" });
}

export type BackendConversation = {
  id: string;
  title: string;
  created_at: string;
};

export type BackendConversationDetail = {
  id: string;
  title: string;
  created_at: string;
  messages: Array<{ id: string; role: string; content: string; created_at: string }>;
  extractions: Array<any>;
};

export async function listConversations(): Promise<BackendConversation[]> {
  const res = await fetch(`${getBaseUrl()}/conversations`, {
    headers: getAuthHeader() as any
  });
  if (!res.ok) throw new Error("Failed to load conversations");
  return (await res.json()) as BackendConversation[];
}

export async function getConversation(conversationId: string): Promise<BackendConversationDetail> {
  const res = await fetch(`${getBaseUrl()}/conversation/${conversationId}`, {
    headers: getAuthHeader() as any
  });
  if (!res.ok) throw new Error("Failed to load conversation");
  return (await res.json()) as BackendConversationDetail;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${getBaseUrl()}/conversation/${conversationId}`, {
    method: "DELETE",
    headers: getAuthHeader() as any
  });
  if (!res.ok) throw new Error("Failed to delete conversation");
}

export type BackendMemoryResponse = {
  semantic: any[];
  relationships: any[];
};

export async function getMemory(): Promise<BackendMemoryResponse> {
  const res = await fetch(`${getBaseUrl()}/memory`, {
    headers: getAuthHeader() as any
  });
  if (!res.ok) throw new Error("Failed to load memory");
  return (await res.json()) as BackendMemoryResponse;
}

export async function getRelationalContext(): Promise<{ context: any }> {
  const res = await fetch(`${getBaseUrl()}/user/relational-context`, {
    headers: getAuthHeader() as any
  });
  if (!res.ok) throw new Error("Failed to load relational context");
  return (await res.json()) as { context: any };
}
