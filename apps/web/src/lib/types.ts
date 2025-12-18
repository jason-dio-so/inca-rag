// API Request/Response Types

export interface CompareRequest {
  insurers: string[];
  query: string;
  age?: number;
  gender?: "M" | "F";
  top_k_per_insurer?: number;
  coverage_codes?: string[];
  policy_keywords?: string[];
}

export interface Evidence {
  document_id: string;
  page_start: number;
  page_end?: number;
  doc_type: string;
  snippet?: string;
  score?: number;
  source_path?: string;
  coverage_code?: string;
}

export interface CompareAxisItem {
  insurer_code: string;
  coverage_code?: string;
  evidence: Evidence[];
}

export interface PolicyAxisItem {
  insurer_code: string;
  evidence: Evidence[];
}

export interface CoverageCompareItem {
  coverage_code: string;
  coverage_name?: string;
  insurers: {
    [key: string]: {
      resolved_amount?: string;
      condition_snippet?: string;
      best_evidence?: Evidence[];
    };
  };
}

export interface DiffSummaryItem {
  diff_type: string;
  description: string;
  insurers_affected?: string[];
  evidence_refs?: string[];
}

export interface DebugInfo {
  selected_plan?: Array<{
    insurer_code: string;
    plan_id?: string;
    plan_name?: string;
  }>;
  timing_ms?: number;
  [key: string]: unknown;
}

export interface CompareResponse {
  compare_axis: CompareAxisItem[];
  policy_axis: PolicyAxisItem[];
  coverage_compare_result: CoverageCompareItem[];
  diff_summary: DiffSummaryItem[];
  debug: DebugInfo;
}

// Chat UI Types

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  error?: string;
}
