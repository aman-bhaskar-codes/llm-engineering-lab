export type ExtractionMode = "simple" | "advanced" | "reasoning";
export type OutputFormat = "strict" | "enriched";

export type Verification = {
  valid: boolean;
  confidence: number; // 0..1
  issues: string[];
};

export type ExtractionResult = {
  data: Record<string, any>;
  confidence?: number;
  valid?: boolean;
  issues?: string[];
  error?: string;
  raw?: string;
};

export type ExtractionApiResponse = {
  conversation_id?: string;
  extraction_id?: string;
  result: ExtractionResult;
};

