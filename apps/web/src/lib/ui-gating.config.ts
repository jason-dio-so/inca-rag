/**
 * STEP 3.7-β: UI Gating Configuration
 *
 * Coverage Resolution 상태에 따른 UI 렌더링 제어 규칙을 정의합니다.
 * Results Panel은 대표 담보가 EXACT일 때만 렌더링됩니다.
 */

import { CoverageResolution } from "./types";

// =============================================================================
// Coverage Resolution State Mapping
// =============================================================================

/**
 * API status → UI display state 매핑
 * - resolved → EXACT (비교 결과 표시)
 * - suggest, clarify → AMBIGUOUS (선택 필요)
 * - failed → NOT_FOUND (매핑 실패)
 */
export type UIResolutionState = "EXACT" | "AMBIGUOUS" | "NOT_FOUND";

export const RESOLUTION_STATUS_MAP: Record<string, UIResolutionState> = {
  resolved: "EXACT",
  suggest: "AMBIGUOUS",
  clarify: "AMBIGUOUS",
  failed: "NOT_FOUND",
};

// =============================================================================
// UI Gating Rules
// =============================================================================

/**
 * Results Panel 렌더링 허용 상태
 * EXACT 상태에서만 Results Panel 활성화
 */
export const RESULTS_PANEL_ALLOWED_STATES: UIResolutionState[] = ["EXACT"];

/**
 * 각 상태별 UI 메시지
 */
export const RESOLUTION_STATE_MESSAGES: Record<UIResolutionState, string> = {
  EXACT: "",
  AMBIGUOUS: "담보를 선택해 주세요. 선택 후 비교 결과가 표시됩니다.",
  NOT_FOUND: "담보가 확정되면 비교 결과가 표시됩니다.",
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * CoverageResolution에서 UI 상태 추출
 */
export function getUIResolutionState(
  resolution: CoverageResolution | null | undefined
): UIResolutionState {
  if (!resolution || !resolution.status) {
    // resolution이 없으면 기본적으로 EXACT 처리 (backward compatibility)
    return "EXACT";
  }
  return RESOLUTION_STATUS_MAP[resolution.status] || "NOT_FOUND";
}

/**
 * Results Panel 렌더링 가능 여부 확인
 */
export function canRenderResultsPanel(
  resolution: CoverageResolution | null | undefined
): boolean {
  const state = getUIResolutionState(resolution);
  return RESULTS_PANEL_ALLOWED_STATES.includes(state);
}

/**
 * 현재 상태에 맞는 메시지 반환
 */
export function getResolutionMessage(
  resolution: CoverageResolution | null | undefined
): string {
  const state = getUIResolutionState(resolution);
  return RESOLUTION_STATE_MESSAGES[state];
}

/**
 * Coverage Resolution이 "resolved" 상태인지 확인 (STEP 3.7)
 */
export function isCoverageResolved(
  resolution: CoverageResolution | null | undefined
): boolean {
  return resolution?.status === "resolved";
}
