"use client";

import * as React from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import type { ExtractionMode, OutputFormat } from "@/types/extraction";
import type { ThemeChoice } from "@/state/useAppStore";
import { useAppStore } from "@/state/useAppStore";
import { useTheme } from "next-themes";

const modeOptions: { value: ExtractionMode; label: string }[] = [
  { value: "simple", label: "Simple Extraction" },
  { value: "advanced", label: "Advanced Extraction" },
  { value: "reasoning", label: "Reasoning Mode (Premium)" }
];

const outputOptions: { value: OutputFormat; label: string }[] = [
  { value: "strict", label: "Strict JSON" },
  { value: "enriched", label: "Enriched JSON" }
];

const themeOptions: { value: ThemeChoice; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" }
];

export function SettingsDialog() {
  const { theme: nextTheme, setTheme: setNextTheme } = useTheme();
  const themeChoice = useAppStore((s) => s.theme);
  const settings = useAppStore((s) => s.settings);
  const open = useAppStore((s) => s.ui.settingsOpen);
  const closeSettings = useAppStore((s) => s.closeSettings);
  const updateSettings = useAppStore((s) => s.updateSettings);
  const setStoreTheme = useAppStore((s) => s.setTheme);

  React.useEffect(() => {
    if (!themeChoice) return;
    if (nextTheme !== themeChoice) {
      setNextTheme(themeChoice);
    }
  }, [nextTheme, setNextTheme, themeChoice]);

  return (
    <Dialog open={open} onOpenChange={(v) => (!v ? closeSettings() : null)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Configure extraction defaults and the experience.</DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">Model</div>
            <Input
              value={settings.modelName}
              onChange={(e) => updateSettings({ modelName: e.target.value })}
              placeholder="gemini-2.5-flash"
            />
          </div>

          <div className="space-y-2">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">Default extraction mode</div>
            <Select value={settings.defaultMode} onValueChange={(v) => updateSettings({ defaultMode: v as ExtractionMode })}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a mode" />
              </SelectTrigger>
              <SelectContent>
                {modeOptions.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">Output format</div>
            <Select value={settings.outputFormat} onValueChange={(v) => updateSettings({ outputFormat: v as OutputFormat })}>
              <SelectTrigger>
                <SelectValue placeholder="Choose output format" />
              </SelectTrigger>
              <SelectContent>
                {outputOptions.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950">
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">Memory</div>
              <div className="text-xs text-slate-600 dark:text-slate-300">Store episodic & semantic insights in this browser.</div>
            </div>
            <Switch checked={settings.memoryEnabled} onCheckedChange={(v) => updateSettings({ memoryEnabled: v })} />
          </div>

          <div className="space-y-2">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">Theme</div>
            <Select value={themeChoice} onValueChange={(v) => setStoreTheme(v as ThemeChoice)}>
              <SelectTrigger>
                <SelectValue placeholder="Theme" />
              </SelectTrigger>
              <SelectContent>
                {themeOptions.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={closeSettings}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

