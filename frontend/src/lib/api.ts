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
export type ExtractStreamToken = (token: string) => void;

function listenToExtractionStream(
  jobId: string, 
  modelName: string, 
  onProgress?: ExtractProgress, 
  onStreamToken?: ExtractStreamToken
): Promise<ExtractionApiResponse> {
  return new Promise((resolve, reject) => {
    const sseUrl = `${getBaseUrl()}/extract/${jobId}/stream`;
    const eventSource = new EventSource(sseUrl);

    let currentProgress = 30;
    eventSource.onmessage = (event) => {
       onStreamToken?.(event.data);
       currentProgress = Math.min(99, currentProgress + 1);
       onProgress?.(currentProgress);
    };

    eventSource.addEventListener("done", (event) => {
       try {
         const parsed = JSON.parse(event.data);
         const response: ExtractionApiResponse = {
           result: parsed.result,
           conversation_id: parsed.conversation_id,
           extraction_id: parsed.extraction_id,
           cached: false,
           metadata: { processing_time: "async queue", model_used: modelName, source: "stream" }
         };
         eventSource.close();
         onProgress?.(100);
         resolve(response);
       } catch(e: any) {
         eventSource.close();
         reject(new Error("Failed to parse final JSON payload from stream: " + e.message));
       }
    });

    eventSource.addEventListener("error", (event) => {
       eventSource.close();
       const errData = (event as any).data ? String((event as any).data) : "Stream closed unexpectedly or LLM failed.";
       reject(new Error(`Extraction stream error: ${errData}`));
    });
  });
}

/**
 * PDF / File Extraction (real file uploads only)
 */
export async function extractPdf(
  file: File,
  onProgress?: ExtractProgress,
  conversationId?: string,
  onStreamToken?: ExtractStreamToken
): Promise<ExtractionApiResponse> {
  const modelName = useAppStore.getState().settings.modelName || "qwen2.5:3b";
  const jobId = await new Promise<string>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${getBaseUrl()}/extract-file`, true);
    const headers = getAuthHeader();
    const token = headers.Authorization;
    if (token) xhr.setRequestHeader("Authorization", token);

    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const pct = Math.round((e.loaded / e.total) * 30); // 0-30% for upload
      onProgress?.(pct);
    };

    xhr.onload = () => {
      try {
        if (xhr.status < 200 || xhr.status >= 300) {
          return reject(new Error(`Request failed (${xhr.status})`));
        }
        const body = JSON.parse(xhr.responseText);
        resolve(body.job_id);
      } catch (err) {
        reject(err);
      }
    };

    xhr.onerror = () => reject(new Error("Network error during file extraction"));

    const formData = new FormData();
    formData.append("file", file, file.name);
    formData.append("model", modelName);
    if (conversationId) formData.append("conversation_id", conversationId);
    
    xhr.send(formData);
  });

  return listenToExtractionStream(jobId, modelName, onProgress, onStreamToken);
}

/**
 * Unified Text Extraction
 */
export async function extractText(
  text: string,
  mode: ExtractionMode,
  onProgress?: ExtractProgress,
  conversationId?: string,
  onStreamToken?: ExtractStreamToken
): Promise<ExtractionApiResponse> {
  onProgress?.(10);

  const modelName = useAppStore.getState().settings.modelName || "qwen2.5:3b";
  const res = await fetch(`${getBaseUrl()}/extract`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(getAuthHeader() as any)
    },
    body: JSON.stringify({
      text,
      mode,
      model: modelName,
      schema: DEFAULT_SCHEMA,
      conversation_id: conversationId
    })
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Extraction enqueue failed (${res.status}): ${detail}`);
  }

  const { job_id } = await res.json();
  if (!job_id) {
    throw new Error("No job ID returned from server.");
  }

  onProgress?.(30);
  return listenToExtractionStream(job_id, modelName, onProgress, onStreamToken);
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
