"use client";

import * as React from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import type { ExtractionMode } from "@/types/extraction";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { Upload } from "lucide-react";
import { useExtractMutation } from "@/lib/useExtractMutation";
import type { ExtractionApiResponse } from "@/types/extraction";

export function ChatComposer({
  mode,
  conversationId,
  onStart,
  onComplete,
  onError,
  onStatusChange
}: {
  mode: ExtractionMode;
  conversationId?: string;
  onStart: (input: { text?: string; fileName?: string }) => void;
  onComplete: (payload: ExtractionApiResponse) => void;
  onError: (message: string) => void;
  onStatusChange?: (s: { extracting: boolean; progress?: number }) => void;
}) {
  const [text, setText] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [progress, setProgress] = React.useState<number | undefined>(undefined);

  const onDrop = React.useCallback((acceptedFiles: File[]) => {
    const f = acceptedFiles[0];
    if (!f) return;
    if (f.type && !f.type.includes("pdf") && !f.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Please upload a PDF file.");
      return;
    }
    setFile(f);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false
  });

  const extractMutation = useExtractMutation();
  const extractingRef = React.useRef(false);

  const submit = React.useCallback(async () => {
    const trimmed = text.trim();
    const hasText = trimmed.length > 0;
    const hasFile = !!file;

    if (!hasText && !hasFile) {
      toast.error("Add text or upload a PDF to extract.");
      return;
    }

    if (extractingRef.current) return;
    extractingRef.current = true;
    onStatusChange?.({ extracting: true, progress: undefined });
    setProgress(undefined);

    try {
      onStart({ text: hasText ? trimmed : undefined, fileName: file?.name });

      if (file) {
        setProgress(0);
        const payload = await extractMutation.mutateAsync({
          mode,
          file,
          onProgress: (p) => {
            setProgress(p);
            onStatusChange?.({ extracting: true, progress: p });
          },
          conversationId
        });
        onComplete(payload);
      } else {
        setProgress(0);
        const payload = await extractMutation.mutateAsync({
          mode,
          text: trimmed,
          onProgress: (p) => {
            setProgress(p);
            onStatusChange?.({ extracting: true, progress: p });
          },
          conversationId
        });
        onComplete(payload);
      }
      setText("");
      setFile(null);
    } catch (err: any) {
      const msg = err?.message ? String(err.message) : "Extraction failed";
      toast.error(msg);
      onError(msg);
    } finally {
      extractingRef.current = false;
      onStatusChange?.({ extracting: false, progress: undefined });
      setProgress(undefined);
    }
  }, [extractMutation, file, mode, conversationId, onComplete, onError, onStart, onStatusChange, text]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="grid gap-3 md:grid-cols-[1fr_220px]">
        <div className="space-y-3">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste text (optional) or upload a PDF. The engine will return structured JSON."
            className="min-h-[110px]"
          />

          <div
            {...getRootProps()}
            className={cn(
              "flex cursor-pointer items-center justify-between gap-3 rounded-xl border-2 border-dashed p-3 transition-colors",
              isDragActive
                ? "border-slate-900 bg-slate-50 dark:border-slate-100 dark:bg-slate-900/50"
                : "border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/20"
            )}
          >
            <div className="flex items-center gap-2">
              <Upload className="h-4 w-4 text-slate-600 dark:text-slate-300" />
              <div className="text-sm text-slate-700 dark:text-slate-200">
                Drag & drop PDF here, or click to browse
              </div>
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400">{file ? "PDF selected" : "Max: TBD"}</div>
            <input {...getInputProps()} />
          </div>

          {file ? (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-900 dark:text-slate-50">{file.name}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{Math.round(file.size / 1024)} KB</div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setFile(null)} disabled={extractingRef.current}>
                Remove
              </Button>
            </div>
          ) : null}

          {typeof progress === "number" ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
                <span>Extraction progress</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} />
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 text-sm dark:border-slate-800 dark:bg-slate-900/20">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Mode
            </div>
            <div className="mt-1 font-medium text-slate-900 dark:text-slate-50 capitalize">{mode}</div>
          </div>

          <Button
            onClick={submit}
            disabled={extractingRef.current}
            className="h-11"
          >
            {extractingRef.current ? "Extracting..." : "Extract"}
          </Button>

          <Input disabled value={file ? "PDF input" : text.trim() ? "Text input (converted to PDF)" : "Ready"} />
        </div>
      </div>
    </div>
  );
}

