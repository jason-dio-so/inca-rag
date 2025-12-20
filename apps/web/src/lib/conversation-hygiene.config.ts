/**
 * STEP 3.7-δ-β: Conversation Hygiene Configuration
 * STEP 3.7-δ-γ: Frontend derives UI only from resolution_state
 *
 * 담보 미확정 상태에서 가이드 메시지가 대화 로그에 누적되는 문제를 방지하고,
 * 담보 선택 안내를 단일 상태 패널(UI State)로 격리합니다.
 *
 * 원칙:
 * 1. 상태와 대화의 분리 - 담보 가이드 ≠ ChatMessage
 * 2. 가이드 단일성 원칙 - 가이드는 항상 1개만 존재 (교체, 누적 금지)
 * 3. RESOLVED 상태 우선 원칙 - RESOLVED일 때만 Chat 로그에 정상 응답 추가
 * 4. resolution_state만 사용 - coverage_resolution.status에서 재계산 금지
 */

import { SuggestedCoverage } from "./types";
import { ResolutionState } from "./ui-gating.config";

// =============================================================================
// Coverage Guide State (UI State, NOT Chat State)
// =============================================================================

export interface CoverageGuideState {
  /** 현재 가이드 상태 (UNRESOLVED / INVALID / null) */
  resolutionState: ResolutionState | null;
  /** 표시할 메시지 */
  message: string;
  /** 선택 가능한 담보 목록 (UNRESOLVED 상태에서만) */
  suggestedCoverages: SuggestedCoverage[];
  /** 감지된 도메인 (있는 경우) */
  detectedDomain?: string;
  /** 원본 쿼리 (어떤 질의에 대한 가이드인지) */
  originalQuery: string;
}

// =============================================================================
// Chat Message Eligibility Rules
// =============================================================================

/**
 * ChatMessage로 추가 가능한 상태 (RESOLVED만 허용)
 */
export const CHAT_MESSAGE_ALLOWED_STATES: ResolutionState[] = ["RESOLVED"];

/**
 * STEP 3.7-δ-γ: 응답이 ChatMessage로 추가될 수 있는지 확인
 * resolution_state를 직접 사용 (coverage_resolution에서 재계산 금지)
 */
export function canAddToChatLog(resolutionState: ResolutionState | null | undefined): boolean {
  if (!resolutionState) return true; // backward compatibility
  return CHAT_MESSAGE_ALLOWED_STATES.includes(resolutionState);
}

/**
 * STEP 3.7-δ-γ: Coverage Guide Panel 표시 필요 여부 확인
 * resolution_state를 직접 사용
 */
export function shouldShowCoverageGuide(
  resolutionState: ResolutionState | null | undefined
): boolean {
  if (!resolutionState) return false;
  return resolutionState === "UNRESOLVED" || resolutionState === "INVALID";
}

// =============================================================================
// Coverage Guide State Factory
// =============================================================================

/**
 * STEP 3.7-δ-γ: CoverageGuideState 생성을 위한 입력 파라미터
 * API 응답에서 직접 추출한 값들을 사용
 */
export interface CreateGuideParams {
  resolutionState: ResolutionState | null | undefined;
  message?: string | null;
  suggestedCoverages?: SuggestedCoverage[];
  detectedDomain?: string | null;
  originalQuery: string;
}

/**
 * STEP 3.7-δ-γ: CoverageGuideState 생성
 * resolution_state를 직접 사용 (coverage_resolution.status에서 재계산 금지)
 * - RESOLVED: null 반환 (가이드 불필요)
 * - UNRESOLVED / INVALID: 가이드 상태 생성
 */
export function createCoverageGuideState(
  params: CreateGuideParams
): CoverageGuideState | null {
  const { resolutionState, message, suggestedCoverages, detectedDomain, originalQuery } = params;

  if (!resolutionState) return null;

  // RESOLVED 상태에서는 가이드 불필요
  if (resolutionState === "RESOLVED") return null;

  // UNRESOLVED: 담보 선택 필요
  if (resolutionState === "UNRESOLVED") {
    return {
      resolutionState: "UNRESOLVED",
      message: message || "여러 담보가 검색되었습니다. 아래에서 선택해 주세요.",
      suggestedCoverages: suggestedCoverages || [],
      detectedDomain: detectedDomain ?? undefined,
      originalQuery,
    };
  }

  // INVALID: 담보 미확정
  return {
    resolutionState: "INVALID",
    message: message || "담보명을 인식하지 못했습니다. 좀 더 구체적으로 입력해 주세요.",
    suggestedCoverages: suggestedCoverages || [],
    originalQuery,
  };
}

// =============================================================================
// Guide Message Templates
// =============================================================================

export const GUIDE_MESSAGES = {
  UNRESOLVED: {
    title: "담보 선택 필요",
    description: "여러 담보가 검색되었습니다. 아래에서 하나를 선택해 주세요.",
    hint: "선택하시면 비교 결과가 표시됩니다.",
  },
  INVALID: {
    title: "담보 미확정",
    description: "담보명을 인식하지 못했습니다.",
    hint: "좀 더 구체적인 담보명을 입력해 주세요.",
  },
} as const;

// =============================================================================
// Validation Helpers
// =============================================================================

/**
 * 가이드가 유효한지 확인 (같은 쿼리에 대한 가이드인지)
 */
export function isGuideValidForQuery(
  guide: CoverageGuideState | null,
  query: string
): boolean {
  if (!guide) return false;
  return guide.originalQuery === query;
}

/**
 * 새로운 쿼리로 가이드 교체가 필요한지 확인
 */
export function shouldReplaceGuide(
  currentGuide: CoverageGuideState | null,
  newQuery: string
): boolean {
  // 현재 가이드가 없으면 교체 불필요
  if (!currentGuide) return false;
  // 다른 쿼리면 교체 필요
  return currentGuide.originalQuery !== newQuery;
}
