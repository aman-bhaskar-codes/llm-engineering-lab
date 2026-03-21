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

async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const url = endpoint.startsWith("http") ? endpoint : `${getBaseUrl()}${endpoint}`;
  
  let res = await fetch(url, {
    ...options,
    headers: { ...getAuthHeader(), ...options.headers }
  });

  if (res.status === 401) {
    const state = useAppStore.getState();
    const refreshToken = state.auth.refreshToken;
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${getBaseUrl()}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (refreshRes.ok) {
          const body = await refreshRes.json();
          state.setAuthToken({
            token: body.access_token,
            refreshToken: body.refresh_token,
            userId: body.user_id,
            name: state.auth.user?.name || "User",
            email: state.auth.user?.email
          });
          
          res = await fetch(url, {
            ...options,
            headers: { ...getAuthHeader(), ...options.headers }
          });
        } else {
          state.logout();
        }
      } catch (e) {
        state.logout();
      }
    } else {
      state.logout();
    }
  }
  return res;
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
    let settled = false;
    let currentProgress = 30;

    const timeout = setTimeout(() => {
      if (!settled) {
        settled = true;
        eventSource.close();
        reject(new Error("Extraction timed out. Please try again."));
      }
    }, 3 * 60 * 1000);

    const settle = (fn: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      eventSource.close();
      fn();
    };

    eventSource.onmessage = (event) => {
      if (settled) return;
      const data: string = event.data;

      // Heartbeat — ignore silently
      if (data === "[HB]") return;

      // Terminal: success
      if (data.startsWith("[DONE]")) {
        const json = data.slice(6);
        settle(() => {
          try {
            const parsed = JSON.parse(json);
            onProgress?.(100);
            resolve({
              result: parsed.result,
              conversation_id: parsed.conversation_id,
              extraction_id: parsed.extraction_id,
              cached: false,
              metadata: { processing_time: "async queue", model_used: modelName, source: "stream" }
            });
          } catch (e: any) {
            reject(new Error("Failed to parse result: " + e.message));
          }
        });
        return;
      }

      // Terminal: error
      if (data.startsWith("[ERROR]")) {
        const json = data.slice(7);
        settle(() => {
          try {
            const parsed = JSON.parse(json);
            reject(new Error(`Extraction failed: ${parsed.error || "Unknown error"}`));
          } catch {
            reject(new Error(`Extraction failed: ${json}`));
          }
        });
        return;
      }

      // Streaming token
      onStreamToken?.(data);
      currentProgress = Math.min(95, currentProgress + 1);
      onProgress?.(currentProgress);
    };

    // Do NOT reject on onerror — EventSource reconnects automatically.
    // We rely on [DONE]/[ERROR] protocol + 3-min timeout instead.
    eventSource.onerror = () => {
      // no-op — connection drops are handled by EventSource auto-reconnect
    };
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
  const modelName = useAppStore.getState().settings.modelName || "phi3:mini";
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

  const modelName = useAppStore.getState().settings.modelName || "phi3:mini";
  const res = await apiFetch(`/extract`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
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
  const res = await apiFetch(`/conversations`);
  if (!res.ok) throw new Error("Failed to load conversations");
  return (await res.json()) as BackendConversation[];
}

export async function getConversation(conversationId: string): Promise<BackendConversationDetail> {
  const res = await apiFetch(`/conversation/${conversationId}`);
  if (!res.ok) throw new Error("Failed to load conversation");
  return (await res.json()) as BackendConversationDetail;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await apiFetch(`/conversation/${conversationId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete conversation");
}

export type BackendMemoryResponse = {
  semantic: any[];
  relationships: any[];
};

export async function getMemory(): Promise<BackendMemoryResponse> {
  const res = await apiFetch(`/memory`);
  if (!res.ok) throw new Error("Failed to load memory");
  return (await res.json()) as BackendMemoryResponse;
}

export async function getRelationalContext(): Promise<{ context: any }> {
  const res = await apiFetch(`/user/relational-context`);
  if (!res.ok) throw new Error("Failed to load relational context");
  return (await res.json()) as { context: any };
}
