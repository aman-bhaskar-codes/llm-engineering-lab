"use client";

import * as React from "react";
import type { ChatSession } from "@/types/chat";
import type { ExtractionApiResponse, ExtractionMode, OutputFormat } from "@/types/extraction";
import { ScrollArea } from "@/components/ui/scroll-area";
import { OutputTabs } from "@/components/output/OutputTabs";
import { ChatComposer } from "@/components/chat/ChatComposer";

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500 [animation-delay:0.2s]" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500 [animation-delay:0.4s]" />
    </span>
  );
}

export function ChatArea({
  session,
  mode,
  outputFormat,
  memoryEnabled,
  onStartExtraction,
  onCompleteExtraction,
  onErrorExtraction,
  onStatusChange
}: {
  session: ChatSession;
  mode: ExtractionMode;
  outputFormat: OutputFormat;
  memoryEnabled: boolean;
  onStartExtraction: (input: { text?: string; fileName?: string }) => void;
  onCompleteExtraction: (payload: ExtractionApiResponse) => void;
  onErrorExtraction: (message: string) => void;
  onStatusChange: (s: { extracting: boolean; progress?: number }) => void;
}) {
  const [extracting, setExtracting] = React.useState(false);
  const bottomRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [session.messages.length, extracting]);

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 px-4 py-4">
        <div className="mx-auto w-full max-w-3xl space-y-4">
          {session.messages.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center text-slate-600 dark:border-slate-800 dark:bg-slate-900/10 dark:text-slate-300">
              <div className="text-sm font-medium">Start an extraction</div>
              <div className="mt-2 text-xs">Paste text or upload a PDF to get structured JSON output.</div>
            </div>
          ) : null}

          {session.messages.map((m) => {
            if (m.role === "user") {
              const text = m.input?.text ?? "";
              const fileName =
                m.input?.attachment?.kind === "file" ? m.input.attachment.fileName : undefined;
              return (
                <div key={m.id} className="flex justify-end">
                  <div className="max-w-[88%] rounded-2xl bg-slate-900 px-4 py-3 text-slate-50 shadow-sm">
                    {fileName ? (
                      <div className="text-xs text-slate-200">{fileName}</div>
                    ) : null}
                    {text ? (
                      <pre className="mt-1 whitespace-pre-wrap break-words text-sm">{text}</pre>
                    ) : null}
                  </div>
                </div>
              );
            }

            if (m.error) {
              return (
                <div key={m.id} className="flex justify-start">
                  <div className="max-w-[88%] rounded-2xl border border-red-200 bg-white px-4 py-3 text-sm text-red-800 dark:border-red-900/40 dark:bg-slate-950 dark:text-red-200">
                    {m.error}
                  </div>
                </div>
              );
            }

            const result = m.output?.result;
            const modeForMessage = m.output?.mode ?? "simple";
            if (!result) {
              return (
                <div key={m.id} className="flex justify-start">
                  <div className="max-w-[88%] rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200">
                    (No output)
                  </div>
                </div>
              );
            }

            return (
              <div key={m.id} className="flex justify-start">
                <div className="w-full max-w-[88%] rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-950">
                  <div className="mb-2 flex items-center justify-between">
                    <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">System</div>
                    {typeof result.confidence === "number" ? (
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        Confidence: {Math.round(result.confidence * 100)}%
                      </div>
                    ) : null}
                  </div>
                  <OutputTabs mode={modeForMessage} result={result} outputFormat={outputFormat} />
                </div>
              </div>
            );
          })}

          {extracting ? (
            <div className="flex justify-start">
              <div className="w-full max-w-[88%] rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-sm dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">System</span>
                  <TypingDots />
                </div>
                <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">Extracting and structuring your information...</div>
              </div>
            </div>
          ) : null}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <div className="p-4">
        <ChatComposer
          mode={mode}
          conversationId={session.backendConversationId}
          onStart={(input) => {
            setExtracting(true);
            onStatusChange({ extracting: true });
            onStartExtraction(input);
          }}
          onComplete={(result) => {
            setExtracting(false);
            onStatusChange({ extracting: false });
            onCompleteExtraction(result);
          }}
          onError={(msg) => {
            setExtracting(false);
            onStatusChange({ extracting: false });
            onErrorExtraction(msg);
          }}
          onStatusChange={(s) => {
            if (typeof s.extracting === "boolean") setExtracting(s.extracting);
            onStatusChange(s);
          }}
        />
      </div>
    </div>
  );
}

