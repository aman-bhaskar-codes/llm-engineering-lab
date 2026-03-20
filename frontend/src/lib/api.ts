"use client";

import { jsPDF } from "jspdf";
import type { ExtractionMode } from "@/types/extraction";
import type { ExtractionApiResponse } from "@/types/extraction";
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

function getAuthHeader() {
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

export async function extractPdf(
  file: File,
  onProgress?: ExtractProgress,
  conversationId?: string
): Promise<ExtractionApiResponse> {
  return await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${getBaseUrl()}/extract-file`, true);
    const headers = getAuthHeader();
    const token = (headers as any).Authorization;
    if (token) xhr.setRequestHeader("Authorization", token);

    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const pct = Math.round((e.loaded / e.total) * 100);
      onProgress?.(Math.max(0, Math.min(100, pct)));
    };

    xhr.onload = () => {
      try {
        if (xhr.status < 200 || xhr.status >= 300) {
          logger.error(`PDF Upload failed: ${xhr.status} ${xhr.responseText}`);
          return reject(new Error(`Request failed (${xhr.status})`));
        }
        const body = JSON.parse(xhr.responseText);
        // Correctly return the full wrapper
        resolve(body as ExtractionApiResponse);
      } catch (err) {
        reject(err);
      }
    };

    xhr.onerror = () => reject(new Error("Network error while extracting PDF"));

    const formData = new FormData();
    formData.append("file", file, file.name);
    if (conversationId) {
      formData.append("conversation_id", conversationId);
    }
    xhr.send(formData);
  });
}

async function extractTextViaJsonEndpoint(
  text: string,
  mode: ExtractionMode,
  conversationId?: string
): Promise<ExtractionApiResponse | null> {
  // Backend currently may or may not implement POST /extract.
  // We attempt it for better compliance with the API contract.
  const res = await fetch(`${getBaseUrl()}/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify({
      text,
      schema: DEFAULT_SCHEMA,
      conversation_id: conversationId
    })
  }).catch(() => null);

  if (!res) return null;
  if (!res.ok) return null;

  const body = await res.json().catch(() => null);
  if (!body) return null;

  // We expect { result: {...}, conversation_id: "...", ... }
  if (body.result) {
    return body as ExtractionApiResponse;
  }
  return null;
}

function createPdfFileFromText(text: string): File {
  // Generate a single-blob PDF containing the text as selectable lines.
  // pypdf can extract text from this generated document.
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 40;
  const fontSize = 11;
  doc.setFontSize(fontSize);

  const lines = doc.splitTextToSize(text, pageWidth - margin * 2);
  let y = margin;

  for (let i = 0; i < lines.length; i++) {
    if (y > pageHeight - margin) {
      doc.addPage();
      y = margin;
    }
    doc.text(String(lines[i]), margin, y);
    y += fontSize * 1.25;
  }

  const blob = doc.output("blob");
  return new File([blob], "text_input.pdf", { type: "application/pdf" });
}

export async function extractText(
  text: string,
  mode: ExtractionMode,
  onProgress?: ExtractProgress,
  conversationId?: string
): Promise<ExtractionApiResponse> {
  // Preferred path: JSON endpoint if backend supports it.
  onProgress?.(10);
  const jsonResult = await extractTextViaJsonEndpoint(text, mode, conversationId);
  if (jsonResult) {
    onProgress?.(92);
    return jsonResult;
  }

  // Fallback: backend currently expects a PDF.
  // We convert text -> a temporary PDF on the client.
  onProgress?.(20);
  const file = createPdfFileFromText(text);
  onProgress?.(25);
  const result = await extractPdf(
    file,
    (p) => onProgress?.(25 + Math.round(p * 0.75)),
    conversationId
  );
  return result;
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

export type BackendMemoryResponse = {
  semantic: Array<{ id: string; key: string; value: any; source_extraction_id: string | null; created_at: string }>;
  relationships: Array<any>;
};

export async function listConversations(): Promise<BackendConversation[]> {
  const res = await fetch(`${getBaseUrl()}/conversations`, {
    headers: getAuthHeader()
  });
  if (!res.ok) throw new Error(`Failed to load conversations (${res.status})`);
  return (await res.json()) as BackendConversation[];
}

export async function getConversation(conversationId: string): Promise<BackendConversationDetail> {
  const res = await fetch(`${getBaseUrl()}/conversation/${conversationId}`, {
    headers: getAuthHeader()
  });
  if (!res.ok) throw new Error(`Failed to load conversation (${res.status})`);
  return (await res.json()) as BackendConversationDetail;
}

export async function getMemory(): Promise<BackendMemoryResponse> {
  const res = await fetch(`${getBaseUrl()}/memory`, {
    headers: getAuthHeader()
  });
  if (!res.ok) throw new Error(`Failed to load memory (${res.status})`);
  return (await res.json()) as BackendMemoryResponse;
}

