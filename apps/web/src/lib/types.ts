/**
 * ⚠️ API 타입 Re-export
 *
 * 이 파일은 types.generated.ts에서 생성된 타입을 re-export합니다.
 * API 계약 타입은 직접 수정하지 마세요.
 *
 * Source of Truth: FastAPI Pydantic 모델 → OpenAPI → types.generated.ts
 */

import { components } from "./types.generated";

// =============================================================================
// API Contract Types (from types.generated.ts)
// =============================================================================

// Request - API has defaults for some fields, make them optional for UI
type ApiCompareRequest = components["schemas"]["CompareRequest"];
export type CompareRequest = Pick<ApiCompareRequest, "insurers" | "query"> &
  Partial<Omit<ApiCompareRequest, "insurers" | "query">>;

// Response
export type CompareResponse = components["schemas"]["CompareResponseModel"];
export type CompareAxisItem = components["schemas"]["CompareAxisItemResponse"];
export type PolicyAxisItem = components["schemas"]["PolicyAxisItemResponse"];
export type CoverageCompareItem = components["schemas"]["CoverageCompareRowResponse"];
export type DiffSummaryItem = components["schemas"]["DiffSummaryItemResponse"];

// Evidence & Related
export type Evidence = components["schemas"]["EvidenceResponse"];
export type AmountInfo = components["schemas"]["AmountInfoResponse"];
export type ConditionInfo = components["schemas"]["ConditionInfoResponse"];

// Compare Table Cell
export type InsurerCompareCell = components["schemas"]["InsurerCompareCellResponse"];

// Diff Summary
export type DiffBullet = components["schemas"]["DiffBulletResponse"];
export type EvidenceRef = components["schemas"]["EvidenceRefResponse"];

// =============================================================================
// U-4.8: Comparison Slots Types
// =============================================================================

export interface SlotEvidenceRef {
  document_id: number;
  page_start: number | null;
  chunk_id?: number | null;
}

export interface LLMTrace {
  method: "rule" | "llm" | "hybrid";
  llm_used: boolean;
  llm_reason?: "flag_off" | "ambiguity_high" | "parse_fail" | "cost_guard" | "not_needed" | null;
  model?: string | null;
}

export interface SlotInsurerValue {
  insurer_code: string;
  value: string | null;
  confidence: "high" | "medium" | "low" | "not_found";
  reason?: string | null;
  evidence_refs: SlotEvidenceRef[];
  trace?: LLMTrace | null;
}

export interface ComparisonSlot {
  slot_key: string;
  label: string;
  comparable: boolean;
  insurers: SlotInsurerValue[];
  diff_summary?: string | null;
}

// Extend CompareResponse to include slots
// (Until types.generated.ts is regenerated)
export type CompareResponseWithSlots = CompareResponse & {
  slots?: ComparisonSlot[];
};

// =============================================================================
// UI-Only Types (not from API)
// =============================================================================

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  error?: string;
}

// DebugInfo는 API에서 { [key: string]: unknown } 으로 정의됨
export type DebugInfo = CompareResponse["debug"];
