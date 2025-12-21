/**
 * STEP 3.7-δ-β: UI Gating Configuration
 *
 * Resolution State에 따른 UI 렌더링 제어 규칙을 정의합니다.
 * Results Panel은 resolution_state === "RESOLVED"일 때만 렌더링됩니다.
 */

import { CoverageResolution } from "./types";

// =============================================================================
// Resolution State Types
// =============================================================================

/**
 * STEP 3.7-δ-β: Resolution State
 * U-4.18-β: SUBTYPE_MULTI 제거 - Subtype은 Coverage 종속
 * - RESOLVED: 확정 (비교 결과 표시)
 * - UNRESOLVED: 후보 있음, 선택 필요 (Subtype-only 질의 포함)
 * - INVALID: 매핑 실패, 재입력 필요
 */
export type ResolutionState = "RESOLVED" | "UNRESOLVED" | "INVALID";

// =============================================================================
// UI Gating Rules
// =============================================================================

/**
 * Results Panel 렌더링 허용 상태
 * U-4.18-β: RESOLVED 상태에서만 Results Panel 활성화
 * (Subtype-only 질의는 UNRESOLVED → 차단됨)
 */
export const RESULTS_PANEL_ALLOWED_STATES: ResolutionState[] = ["RESOLVED"];

/**
 * 각 상태별 UI 메시지
 * U-4.18-β: UNRESOLVED 메시지는 coverage_resolution.message에서 동적으로 가져옴
 */
export const RESOLUTION_STATE_MESSAGES: Record<ResolutionState, string> = {
  RESOLVED: "",
  UNRESOLVED: "담보를 선택해 주세요. 선택 후 비교 결과가 표시됩니다.",
  INVALID: "담보가 확정되면 비교 결과가 표시됩니다.",
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * STEP 3.7-δ-β: resolution_state를 직접 사용
 * (legacy: CoverageResolution.status에서 추출)
 */
export function getUIResolutionState(
  resolution: CoverageResolution | null | undefined
): ResolutionState {
  if (!resolution || !resolution.status) {
    // resolution이 없으면 기본적으로 RESOLVED 처리 (backward compatibility)
    return "RESOLVED";
  }
  // STEP 3.7-δ-β: status는 이제 RESOLVED | UNRESOLVED | INVALID
  return resolution.status;
}

/**
 * Results Panel 렌더링 가능 여부 확인
 * resolution_state === "RESOLVED"일 때만 true
 */
export function canRenderResultsPanel(
  resolution: CoverageResolution | null | undefined
): boolean {
  const state = getUIResolutionState(resolution);
  return state === "RESOLVED";
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
 * Coverage Resolution이 "RESOLVED" 상태인지 확인
 */
export function isCoverageResolved(
  resolution: CoverageResolution | null | undefined
): boolean {
  return resolution?.status === "RESOLVED";
}
