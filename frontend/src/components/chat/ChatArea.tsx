"use client";

import * as React from "react";
import type { ChatSession } from "@/types/chat";
import type { ExtractionApiResponse, ExtractionMode, OutputFormat } from "@/types/extraction";
import { ScrollArea } from "@/components/ui/scroll-area";
import { OutputTabs } from "@/components/output/OutputTabs";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500 [animation-delay:0.2s]" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-500 [animation-delay:0.4s]" />
    </span>
  );
}

function StreamingOutput({ text }: { text: string }) {
  if (!text) return null;
  const thinkMatch = text.match(/<think>([\s\S]*?)(?:<\/think>|$)/);
  if (thinkMatch) {
    const thinkContent = thinkMatch[1].trim();
    const afterThink = text.substring(thinkMatch.index! + thinkMatch[0].length).trim();
    return (
      <div className="mt-3 space-y-3">
        <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-3 text-xs text-indigo-700 font-mono whitespace-pre-wrap shadow-inner dark:border-indigo-900/50 dark:bg-indigo-900/20 dark:text-indigo-300">
          <div className="mb-2 font-bold uppercase tracking-wider text-[10px] text-indigo-500 dark:text-indigo-400">⚡ Engine Reasoning Log</div>
          {thinkContent}
        </div>
        {afterThink && <pre className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{afterThink}</pre>}
      </div>
    );
  }
  return <pre className="mt-3 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{text}</pre>;
}

const MemoizedMessageBubble = React.memo(function MemoizedMessageBubble({
  m,
  outputFormat,
  onRetry
}: {
  m: any;
  outputFormat: OutputFormat;
  onRetry: () => void;
}) {
  if (m.role === "user") {
    const text = m.input?.text ?? "";
    const fileName =
      m.input?.attachment?.kind === "file" ? m.input.attachment.fileName : undefined;
    return (
      <div className="flex justify-end">
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
      <div className="flex justify-start">
        <div className="max-w-[88%] rounded-2xl border border-red-200 bg-white px-4 py-3 text-sm text-red-800 dark:border-red-900/40 dark:bg-slate-950 dark:text-red-200">
          <div className="space-y-2">
            <div className="text-red-500 dark:text-red-400 font-medium">{m.error}</div>
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 dark:border-red-900/50 dark:text-red-400 dark:hover:bg-red-950/50"
              onClick={onRetry}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry Extraction
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const result = m.output?.result;
  const modeForMessage = m.output?.mode ?? "simple";
  if (!result) {
    return (
      <div className="flex justify-start">
        <div className="max-w-[88%] rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200">
          (No output)
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
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
});

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
  const [streamText, setStreamText] = React.useState("");
  const [reasoningStage, setReasoningStage] = React.useState(0);
  const bottomRef = React.useRef<HTMLDivElement | null>(null);

  const handleRetry = React.useCallback(() => {
    const lastUserMsg = [...session.messages].reverse().find(msg => msg.role === "user");
    if (lastUserMsg?.input) {
      onStartExtraction(lastUserMsg.input);
    }
  }, [session.messages, onStartExtraction]);

  const stages = [
    "Initial Extraction...",
    "Refining Relationships...",
    "Final Verification & Scoring..."
  ];

  React.useEffect(() => {
    let interval: NodeJS.Timeout;
    if (extracting && mode === "reasoning") {
      setReasoningStage(0);
      interval = setInterval(() => {
        setReasoningStage((prev) => (prev < 2 ? prev + 1 : prev));
      }, 2500);
    }
    return () => clearInterval(interval);
  }, [extracting, mode]);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [session.messages.length, extracting]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-4 scroll-smooth">
        <div className="mx-auto w-full max-w-3xl space-y-4">
          {session.messages.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center text-slate-600 dark:border-slate-800 dark:bg-slate-900/10 dark:text-slate-300">
              <div className="text-sm font-medium">Start an extraction</div>
              <div className="mt-2 text-xs">Paste text or upload a PDF to get structured JSON output.</div>
            </div>
          ) : null}

          {session.messages.map((m) => (
            <div key={m.id}>
              <MemoizedMessageBubble m={m} outputFormat={outputFormat} onRetry={handleRetry} />
            </div>
          ))}

          {extracting ? (
            <div className="flex justify-start">
              <div className="w-full max-w-[88%] rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-sm dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">System</span>
                  <TypingDots />
                </div>
                <div className="mt-2 text-xs font-medium text-slate-900 dark:text-slate-50">
                  {mode === "reasoning" ? stages[reasoningStage] : "Extracting and structuring your information..."}
                </div>
                {streamText && <StreamingOutput text={streamText} />}
                {mode === "reasoning" && (
                  <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                    <div 
                      className="h-full bg-blue-600 transition-all duration-1000" 
                      style={{ width: `${((reasoningStage + 1) / stages.length) * 100}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          ) : null}

          <div ref={bottomRef} className="h-4" />
        </div>
      </div>

      <div className="p-4">
        <ChatComposer
          mode={mode}
          conversationId={session.backendConversationId}
          onStreamToken={(token) => setStreamText(prev => prev + token)}
          onStart={(input) => {
            setExtracting(true);
            setStreamText("");
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

