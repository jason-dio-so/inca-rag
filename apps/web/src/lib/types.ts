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
