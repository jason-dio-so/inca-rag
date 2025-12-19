/**
 * STEP 3.8: State Isolation Configuration
 *
 * Query State와 View State의 명시적 분리 규칙을 정의합니다.
 * 이 설정은 코드가 아닌 설정으로 관리되어, 비즈니스 규칙 변경 시 코드 수정 없이 대응 가능합니다.
 */

// =============================================================================
// State 분류 정의
// =============================================================================

/**
 * Query State: 질의 실행에 의해서만 변경되는 상태
 * - 이 상태들은 Query 실행(handleSendMessage) 외의 경로로 변경 불가
 */
export const QUERY_STATE_KEYS = [
  "messages",           // 채팅 메시지 목록
  "currentResponse",    // 현재 비교 결과
  "currentAnchor",      // Query Anchor (coverage, intent)
  "isLoading",          // 질의 실행 중 여부
] as const;

/**
 * View State: Read-only UI 이벤트에 의해 변경되는 상태
 * - Query State에 영향을 주지 않음
 * - 문서 열람, 탭 전환, 스크롤 등 순수 UI 동작
 */
export const VIEW_STATE_KEYS = [
  "viewingDocument",    // 현재 보고 있는 문서 (document_id, page, zoom)
  "activeTab",          // 현재 활성 탭 (slots, compare, diff, evidence, policy)
  "scrollPosition",     // 스크롤 위치
  "expandedSections",   // 펼쳐진 섹션들 (debug, additional evidence 등)
] as const;

// =============================================================================
// View 이벤트 분류
// =============================================================================

/**
 * Read-only View Events: Query State를 절대 변경하지 않는 이벤트
 */
export const READ_ONLY_VIEW_EVENTS = [
  "evidence_view",              // Evidence 상세보기 클릭
  "policy_view",                // Policy 상세보기 클릭
  "document_view",              // 문서 상세보기 클릭
  "document_page_change",       // 문서 페이지 이동
  "document_zoom_change",       // 문서 확대/축소
  "document_scroll",            // 문서 스크롤
  "document_close",             // 문서 닫기
  "tab_change",                 // 탭 전환
  "accordion_toggle",           // 아코디언 펼침/접음
  "collapsible_toggle",         // Collapsible 펼침/접음
  "copy_reference",             // 참조 복사
  "debug_toggle",               // 디버그 섹션 토글
] as const;

/**
 * Query Mutation Events: Query State를 변경할 수 있는 이벤트
 * - 이 이벤트들만 Query State 변경을 허용
 */
export const QUERY_MUTATION_EVENTS = [
  "send_message",               // 메시지 전송
  "coverage_button_click",      // 담보 버튼 클릭 (STEP 3.6: UI 이벤트로 처리)
  "related_coverage_select",    // 연관 담보 선택
  "insurer_toggle",             // 보험사 선택/해제
] as const;

// =============================================================================
// 격리 규칙 (Isolation Rules)
// =============================================================================

export interface IsolationRule {
  event: string;
  allowedStateChanges: readonly string[];
  blockedStateChanges: readonly string[];
}

/**
 * 이벤트별 상태 변경 허용/차단 규칙
 */
export const ISOLATION_RULES: IsolationRule[] = [
  // Read-only events: View State만 변경 가능
  ...READ_ONLY_VIEW_EVENTS.map((event) => ({
    event,
    allowedStateChanges: VIEW_STATE_KEYS as unknown as readonly string[],
    blockedStateChanges: QUERY_STATE_KEYS as unknown as readonly string[],
  })),
  // Query mutation events: Query State 변경 가능
  ...QUERY_MUTATION_EVENTS.map((event) => ({
    event,
    allowedStateChanges: [...QUERY_STATE_KEYS, ...VIEW_STATE_KEYS] as readonly string[],
    blockedStateChanges: [] as readonly string[],
  })),
];

// =============================================================================
// 유틸리티 함수
// =============================================================================

/**
 * 이벤트가 Read-only인지 확인
 */
export function isReadOnlyEvent(eventType: string): boolean {
  return READ_ONLY_VIEW_EVENTS.includes(eventType as typeof READ_ONLY_VIEW_EVENTS[number]);
}

/**
 * 이벤트가 Query State 변경을 허용하는지 확인
 */
export function canMutateQueryState(eventType: string): boolean {
  return QUERY_MUTATION_EVENTS.includes(eventType as typeof QUERY_MUTATION_EVENTS[number]);
}

/**
 * 상태 변경 시도가 규칙을 위반하는지 확인
 * @returns 위반 시 에러 메시지, 정상이면 null
 */
export function validateStateChange(
  eventType: string,
  targetState: string
): string | null {
  const rule = ISOLATION_RULES.find((r) => r.event === eventType);

  if (!rule) {
    // 알 수 없는 이벤트는 기본적으로 View State만 허용
    if (QUERY_STATE_KEYS.includes(targetState as typeof QUERY_STATE_KEYS[number])) {
      return `Unknown event "${eventType}" cannot modify Query State "${targetState}"`;
    }
    return null;
  }

  if (rule.blockedStateChanges.includes(targetState)) {
    return `Event "${eventType}" is blocked from modifying "${targetState}"`;
  }

  return null;
}

// =============================================================================
// Type Definitions
// =============================================================================

export type QueryStateKey = typeof QUERY_STATE_KEYS[number];
export type ViewStateKey = typeof VIEW_STATE_KEYS[number];
export type ReadOnlyViewEvent = typeof READ_ONLY_VIEW_EVENTS[number];
export type QueryMutationEvent = typeof QUERY_MUTATION_EVENTS[number];
