/**
 * STEP 3.7-δ-β: Resolution Lock & Single Source of Truth
 * STEP 3.7-δ-γ: Frontend derives UI only from resolution_state
 *
 * Resolution 상태 전이 규칙을 정의하고, RESOLVED 상태에서의 퇴행을 방지합니다.
 *
 * 핵심 원칙:
 * 1. Resolution Lock: RESOLVED 상태는 명시적 리셋 없이 UNRESOLVED/INVALID로 돌아갈 수 없음
 * 2. Single Source of Truth: QueryAnchor만 resolution 상태를 보유
 * 3. 모든 UI 컴포넌트는 anchor를 참조하여 렌더링
 * 4. resolution_state만 사용 - coverage_resolution.status에서 재계산 금지
 */

import { QueryAnchor } from "./types";
import { ResolutionState } from "./ui-gating.config";

// =============================================================================
// Resolution State Transition Rules
// =============================================================================

/**
 * 허용되는 상태 전이
 * - NULL → any: 초기 상태에서는 모든 전이 허용
 * - UNRESOLVED → RESOLVED: 담보 선택으로 확정
 * - INVALID → RESOLVED: 재질의로 담보 확정
 */
type TransitionKey = `${ResolutionState | "NULL"}->${ResolutionState}`;

const ALLOWED_TRANSITIONS: Set<TransitionKey> = new Set([
  // NULL → any
  "NULL->RESOLVED",
  "NULL->UNRESOLVED",
  "NULL->INVALID",
  // UNRESOLVED → RESOLVED (선택으로 확정)
  "UNRESOLVED->RESOLVED",
  // INVALID → RESOLVED (재질의로 확정)
  "INVALID->RESOLVED",
  // 동일 상태 유지 (no-op)
  "RESOLVED->RESOLVED",
  "UNRESOLVED->UNRESOLVED",
  "INVALID->INVALID",
]);

/**
 * 금지되는 상태 전이 (절대 금지)
 * - RESOLVED → UNRESOLVED: 확정 후 다시 모호해질 수 없음
 * - RESOLVED → INVALID: 확정 후 다시 미확정이 될 수 없음
 */
const FORBIDDEN_TRANSITIONS: Set<TransitionKey> = new Set([
  "RESOLVED->UNRESOLVED",
  "RESOLVED->INVALID",
]);

// =============================================================================
// Resolution Lock Validation
// =============================================================================

/**
 * 상태 전이가 허용되는지 확인
 */
export function isTransitionAllowed(
  fromState: ResolutionState | null,
  toState: ResolutionState
): boolean {
  const from = fromState ?? "NULL";
  const key: TransitionKey = `${from}->${toState}`;

  // 금지된 전이 체크
  if (FORBIDDEN_TRANSITIONS.has(key)) {
    return false;
  }

  // 허용된 전이 체크
  return ALLOWED_TRANSITIONS.has(key);
}

/**
 * Resolution Lock이 걸려있는지 확인
 * - anchor가 있고 resolution이 RESOLVED이면 Lock 상태
 */
export function isResolutionLocked(anchor: QueryAnchor | null): boolean {
  if (!anchor) return false;
  // anchor가 있다는 것은 RESOLVED 상태를 의미
  return !!anchor.coverage_code;
}

/**
 * STEP 3.7-δ-γ: 새 resolution_state가 현재 lock 상태를 위반하는지 확인
 * - Lock 상태에서 UNRESOLVED/INVALID 응답이 오면 위반
 * - resolution_state를 직접 사용 (coverage_resolution에서 재계산 금지)
 */
export function isLockViolation(
  currentAnchor: QueryAnchor | null,
  newState: ResolutionState | null | undefined
): boolean {
  // Lock이 없으면 위반 불가
  if (!isResolutionLocked(currentAnchor)) {
    return false;
  }

  // 새 resolution이 없으면 위반 아님 (backward compatibility: RESOLVED로 취급)
  if (!newState) {
    return false;
  }

  // Lock 상태에서 RESOLVED가 아닌 응답이 오면 위반
  return newState !== "RESOLVED";
}

// =============================================================================
// Reset Condition Detection
// =============================================================================

/**
 * 리셋 조건 타입
 */
export type ResetCondition =
  | "NEW_COVERAGE_QUERY" // 새로운 담보 키워드 질의
  | "RESET_ANCHOR_EVENT" // 명시적 앵커 리셋
  | "SESSION_END"; // 세션 종료

/**
 * STEP 3.9: 질의에 담보 키워드가 포함되어 있는지 확인
 * - 담보 관련 키워드: 진단비, 수술비, 담보, 보장, 특약
 */
export function hasCoverageKeyword(query: string): boolean {
  return /진단비|수술비|담보|보장|특약|보험금|한도/.test(query);
}

/**
 * STEP 3.9: 질의가 현재 anchor의 담보를 언급하는지 확인
 * - anchor의 coverage_name 또는 coverage_code가 질의에 포함되어 있으면 true
 */
export function mentionsCurrentCoverage(
  query: string,
  currentAnchor: QueryAnchor | null
): boolean {
  if (!currentAnchor) return false;

  const normalizedQuery = query.toLowerCase().trim();
  const coverageName = currentAnchor.coverage_name?.toLowerCase();
  const coverageCode = currentAnchor.coverage_code.toLowerCase();

  return (
    (!!coverageName && normalizedQuery.includes(coverageName)) ||
    normalizedQuery.includes(coverageCode)
  );
}

/**
 * 질의가 새로운 담보 키워드를 포함하는지 확인
 * - 현재 anchor의 coverage와 다른 담보를 언급하면 리셋 대상
 */
export function isNewCoverageQuery(
  query: string,
  currentAnchor: QueryAnchor | null
): boolean {
  if (!currentAnchor) return false;

  // 담보 관련 키워드가 없으면 새 담보 질의가 아님
  if (!hasCoverageKeyword(query)) {
    return false;
  }

  // 현재 담보가 질의에 포함되어 있으면 새 담보 질의가 아님
  if (mentionsCurrentCoverage(query, currentAnchor)) {
    return false;
  }

  // 담보 키워드가 있고 현재 담보가 아니면 새 담보 질의
  return true;
}

/**
 * STEP 3.9: 담보 고정(lock) 여부 결정
 * - 리셋 조건이 없고, anchor가 있으면 locked_coverage_code 전달
 *
 * Scenarios:
 * - A: 후속 질의에 담보 언급 없음 → lock
 * - B: 후속 질의에 동일 담보 언급 → lock
 * - C: 후속 질의에 다른 담보 언급 → no lock (reset)
 * - D: 새 담보 질의 → no lock (reset)
 */
export function shouldLockCoverage(
  currentAnchor: QueryAnchor | null,
  resetCondition: ResetCondition | null
): boolean {
  // 리셋 조건이면 lock하지 않음
  if (resetCondition) {
    return false;
  }

  // anchor가 없으면 lock할 것이 없음
  if (!currentAnchor || !currentAnchor.coverage_code) {
    return false;
  }

  // anchor가 있고 리셋 조건이 아니면 lock
  return true;
}

/**
 * 리셋이 필요한지 확인하고, 리셋 사유 반환
 */
export function detectResetCondition(
  query: string,
  currentAnchor: QueryAnchor | null,
  explicitReset: boolean = false
): ResetCondition | null {
  if (explicitReset) {
    return "RESET_ANCHOR_EVENT";
  }

  if (isNewCoverageQuery(query, currentAnchor)) {
    return "NEW_COVERAGE_QUERY";
  }

  return null;
}

// =============================================================================
// Resolution Lock Application
// =============================================================================

/**
 * STEP 3.7-δ-γ: Lock 위반 시 기존 anchor 유지 결정
 * - Lock 위반이면 기존 anchor 유지
 * - 정상 전이면 새 anchor로 업데이트
 * - resolution_state를 직접 사용 (coverage_resolution에서 재계산 금지)
 */
export function resolveAnchorUpdate(
  currentAnchor: QueryAnchor | null,
  newAnchor: QueryAnchor | null | undefined,
  newState: ResolutionState | null | undefined,
  resetCondition: ResetCondition | null
): QueryAnchor | null {
  // 리셋 조건이면 새 anchor 사용 (또는 null)
  if (resetCondition) {
    return newAnchor ?? null;
  }

  // Lock 위반 체크
  if (isLockViolation(currentAnchor, newState)) {
    // Lock 위반 시 기존 anchor 유지
    console.warn(
      "[Resolution Lock] Lock violation detected. Keeping current anchor:",
      currentAnchor?.coverage_code
    );
    return currentAnchor;
  }

  // 정상 전이: 새 anchor 사용
  return newAnchor ?? currentAnchor;
}

/**
 * STEP 3.7-δ-γ: Lock 위반 시 기존 resolution 상태 유지 결정
 * - resolution_state를 직접 사용 (coverage_resolution에서 재계산 금지)
 */
export function resolveResolutionState(
  currentAnchor: QueryAnchor | null,
  newState: ResolutionState | null | undefined,
  resetCondition: ResetCondition | null
): ResolutionState {
  // 리셋 조건이면 새 resolution 상태 사용
  if (resetCondition) {
    return newState || "RESOLVED";
  }

  // Lock 위반 체크
  if (isLockViolation(currentAnchor, newState)) {
    // Lock 위반 시 RESOLVED 상태 유지
    return "RESOLVED";
  }

  // 정상 전이: 새 resolution 상태 사용
  return newState || "RESOLVED";
}

// =============================================================================
// Debug Helpers
// =============================================================================

/**
 * 상태 전이 로그 (개발용)
 */
export function logTransition(
  from: ResolutionState | null,
  to: ResolutionState,
  allowed: boolean,
  reason?: string
): void {
  const fromStr = from ?? "NULL";
  const status = allowed ? "✓" : "✗";
  const reasonStr = reason ? ` (${reason})` : "";
  console.log(`[Resolution Lock] ${fromStr} → ${to} ${status}${reasonStr}`);
}
