/**
 * STEP 3.7-δ-β: Conversation Hygiene Configuration
 *
 * 담보 미확정 상태에서 가이드 메시지가 대화 로그에 누적되는 문제를 방지하고,
 * 담보 선택 안내를 단일 상태 패널(UI State)로 격리합니다.
 *
 * 원칙:
 * 1. 상태와 대화의 분리 - 담보 가이드 ≠ ChatMessage
 * 2. 가이드 단일성 원칙 - 가이드는 항상 1개만 존재 (교체, 누적 금지)
 * 3. RESOLVED 상태 우선 원칙 - RESOLVED일 때만 Chat 로그에 정상 응답 추가
 */

import { CoverageResolution, SuggestedCoverage } from "./types";
import { ResolutionState, getUIResolutionState } from "./ui-gating.config";

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
 * 응답이 ChatMessage로 추가될 수 있는지 확인
 */
export function canAddToChatLog(resolution: CoverageResolution | null | undefined): boolean {
  const state = getUIResolutionState(resolution);
  return CHAT_MESSAGE_ALLOWED_STATES.includes(state);
}

/**
 * Coverage Guide Panel 표시 필요 여부 확인
 */
export function shouldShowCoverageGuide(
  resolution: CoverageResolution | null | undefined
): boolean {
  if (!resolution) return false;
  const state = getUIResolutionState(resolution);
  return state === "UNRESOLVED" || state === "INVALID";
}

// =============================================================================
// Coverage Guide State Factory
// =============================================================================

/**
 * CoverageResolution에서 CoverageGuideState 생성
 * - RESOLVED: null 반환 (가이드 불필요)
 * - UNRESOLVED / INVALID: 가이드 상태 생성
 */
export function createCoverageGuideState(
  resolution: CoverageResolution | null | undefined,
  originalQuery: string
): CoverageGuideState | null {
  if (!resolution) return null;

  const state = getUIResolutionState(resolution);

  // RESOLVED 상태에서는 가이드 불필요
  if (state === "RESOLVED") return null;

  // UNRESOLVED: 담보 선택 필요
  if (state === "UNRESOLVED") {
    return {
      resolutionState: "UNRESOLVED",
      message: resolution.message || "여러 담보가 검색되었습니다. 아래에서 선택해 주세요.",
      suggestedCoverages: resolution.suggested_coverages || [],
      detectedDomain: resolution.detected_domain ?? undefined,
      originalQuery,
    };
  }

  // INVALID: 담보 미확정
  return {
    resolutionState: "INVALID",
    message: resolution.message || "담보명을 인식하지 못했습니다. 좀 더 구체적으로 입력해 주세요.",
    suggestedCoverages: resolution.suggested_coverages || [],
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
