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
// STEP 2.9 + 3.6: Query Anchor with Intent
// =============================================================================

export interface QueryAnchor {
  coverage_code: string;
  coverage_name?: string | null;
  domain?: string | null;
  original_query: string;
  // STEP 3.6: Intent Locking
  intent: "lookup" | "compare";
}

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

// =============================================================================
// STEP 3.7: Coverage Resolution Types
// =============================================================================

export interface SuggestedCoverage {
  coverage_code: string;
  coverage_name: string | null;
  similarity: number;
  insurer_code?: string | null;
}

export interface CoverageResolution {
  /**
   * STEP 3.7-δ-β: status (resolution_state)
   * - RESOLVED: 확정된 coverage_code 존재 (candidates == 1 && similarity >= confident)
   * - UNRESOLVED: 후보는 있지만 확정 불가 (candidates >= 1, 유저 선택 필요)
   * - INVALID: 매핑 불가 (candidates == 0, 재입력 필요)
   */
  status: "RESOLVED" | "UNRESOLVED" | "INVALID";
  resolved_coverage_code?: string | null;
  message?: string | null;
  suggested_coverages: SuggestedCoverage[];
  detected_domain?: string | null;
}

// Extend CompareResponse to include slots and STEP 2.5 fields
// (Until types.generated.ts is regenerated)
export type CompareResponseWithSlots = CompareResponse & {
  // STEP 3.7-δ-β: Resolution State (최상위 게이트 필드)
  resolution_state: "RESOLVED" | "UNRESOLVED" | "INVALID";
  resolved_coverage_code?: string | null;
  slots?: ComparisonSlot[] | null;
  // STEP 2.5: 대표 담보 / 연관 담보 / 사용자 요약
  primary_coverage_code?: string | null;
  primary_coverage_name?: string | null;
  related_coverage_codes?: string[];
  user_summary?: string | null;
  // STEP 3.5: Insurer Auto-Recovery 메시지
  recovery_message?: string | null;
  // STEP 2.9 + 3.6: Query Anchor with Intent
  anchor?: QueryAnchor | null;
  // STEP 3.7: Coverage Resolution (상세 정보)
  coverage_resolution?: CoverageResolution | null;
};

// STEP 3.6: Extended CompareRequest with ui_event_type
// STEP 3.9: Added locked_coverage_code for anchor persistence
// STEP 4.5: Extended to locked_coverage_codes for multi-subtype support
export interface CompareRequestWithIntent extends CompareRequest {
  anchor?: QueryAnchor | null;
  ui_event_type?: string | null;
  // STEP 3.9: 담보 고정 코드 (제공 시 backend에서 resolver 스킵) - deprecated, use locked_coverage_codes
  locked_coverage_code?: string | null;
  // STEP 4.5: 복수 담보 고정 코드 (멀티 subtype 지원)
  locked_coverage_codes?: string[] | null;
}

// =============================================================================
// STEP 4.1: Subtype Comparison Types
// =============================================================================

export interface SubtypeComparisonItem {
  subtype_code: string;
  subtype_name: string;
  info_type: string;  // definition, coverage, conditions, boundary (STEP 4.7)
  info_label: string;  // 정의, 보장 여부, 지급 조건, 경계/감액/제한
  insurer_code: string;
  value: string | null;
  confidence: "high" | "medium" | "low" | "not_found";
  // STEP 4.7: 강화된 evidence 필드
  evidence_ref?: {
    document_id?: number | null;
    page_start?: number | null;
    doc_type?: string | null;  // 약관, 사업방법서, 상품요약서
    excerpt?: string | null;   // 원문 발췌 (1-2문장)
  } | null;
  // STEP 4.7: 불명확 시 사유
  unknown_reason?: string | null;
}

export interface SubtypeComparison {
  subtypes: string[];
  comparison_items: SubtypeComparisonItem[];
  is_multi_subtype: boolean;
}

// Extend CompareResponseWithSlots to include subtype_comparison
export type CompareResponseWithSubtype = CompareResponseWithSlots & {
  subtype_comparison?: SubtypeComparison | null;
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
