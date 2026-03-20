"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import type { ExtractionApiResponse, ExtractionMode } from "@/types/extraction";
import type { ExtractProgress, ExtractStreamToken } from "@/lib/api";
import { extractPdf, extractText } from "@/lib/api";

export type ExtractMutationInput = {
  mode: ExtractionMode;
  text?: string;
  file?: File;
  conversationId?: string;
  onProgress?: ExtractProgress;
  onStreamToken?: ExtractStreamToken;
};

export function useExtractMutation() {
  return useMutation<ExtractionApiResponse, Error, ExtractMutationInput>({
    mutationFn: async (vars) => {
      if (vars.file) {
        return await extractPdf(vars.file, vars.onProgress, vars.conversationId, vars.onStreamToken);
      }
      if (vars.text === undefined) {
        throw new Error("Missing extract input text.");
      }
      return await extractText(vars.text, vars.mode, vars.onProgress, vars.conversationId, vars.onStreamToken);
    }
  });
}

