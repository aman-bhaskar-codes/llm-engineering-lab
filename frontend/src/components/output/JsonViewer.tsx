"use client";

import * as React from "react";
import { Prism as SyntaxHighlighterPrism } from "react-syntax-highlighter";
import { useTheme } from "next-themes";

export function JsonViewer({ value }: { value: unknown }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  const json = React.useMemo(() => {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }, [value]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950">
      <SyntaxHighlighterPrism
        language="json"
        style={{}}
        customStyle={{
          margin: 0,
          background: "transparent"
        }}
        codeTagProps={{ style: { fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" } }}
      >
        {json}
      </SyntaxHighlighterPrism>
    </div>
  );
}

