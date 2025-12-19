/**
 * STEP 3.8: State Isolation Unit Tests
 *
 * Query State와 View State 분리가 올바르게 구현되었는지 검증
 */

import {
  QUERY_STATE_KEYS,
  VIEW_STATE_KEYS,
  READ_ONLY_VIEW_EVENTS,
  QUERY_MUTATION_EVENTS,
  isReadOnlyEvent,
  canMutateQueryState,
  validateStateChange,
} from "../lib/state-isolation.config";

describe("STEP 3.8: State Isolation Config", () => {
  describe("State Key Definitions", () => {
    test("Query State keys are defined", () => {
      expect(QUERY_STATE_KEYS).toContain("messages");
      expect(QUERY_STATE_KEYS).toContain("currentResponse");
      expect(QUERY_STATE_KEYS).toContain("currentAnchor");
      expect(QUERY_STATE_KEYS).toContain("isLoading");
    });

    test("View State keys are defined", () => {
      expect(VIEW_STATE_KEYS).toContain("viewingDocument");
      expect(VIEW_STATE_KEYS).toContain("activeTab");
      expect(VIEW_STATE_KEYS).toContain("scrollPosition");
      expect(VIEW_STATE_KEYS).toContain("expandedSections");
    });

    test("Query State and View State keys are mutually exclusive", () => {
      const queryKeys = new Set(QUERY_STATE_KEYS);
      const viewKeys = new Set(VIEW_STATE_KEYS);

      for (const key of queryKeys) {
        expect(viewKeys.has(key as string)).toBe(false);
      }
    });
  });

  describe("Event Classification", () => {
    test("Evidence view is read-only event", () => {
      expect(READ_ONLY_VIEW_EVENTS).toContain("evidence_view");
      expect(isReadOnlyEvent("evidence_view")).toBe(true);
    });

    test("Policy view is read-only event", () => {
      expect(READ_ONLY_VIEW_EVENTS).toContain("policy_view");
      expect(isReadOnlyEvent("policy_view")).toBe(true);
    });

    test("Document view is read-only event", () => {
      expect(READ_ONLY_VIEW_EVENTS).toContain("document_view");
      expect(isReadOnlyEvent("document_view")).toBe(true);
    });

    test("Document page change is read-only event", () => {
      expect(READ_ONLY_VIEW_EVENTS).toContain("document_page_change");
      expect(isReadOnlyEvent("document_page_change")).toBe(true);
    });

    test("Document close is read-only event", () => {
      expect(READ_ONLY_VIEW_EVENTS).toContain("document_close");
      expect(isReadOnlyEvent("document_close")).toBe(true);
    });

    test("Tab change is read-only event", () => {
      expect(READ_ONLY_VIEW_EVENTS).toContain("tab_change");
      expect(isReadOnlyEvent("tab_change")).toBe(true);
    });

    test("Send message is query mutation event", () => {
      expect(QUERY_MUTATION_EVENTS).toContain("send_message");
      expect(canMutateQueryState("send_message")).toBe(true);
    });

    test("Coverage button click is query mutation event", () => {
      expect(QUERY_MUTATION_EVENTS).toContain("coverage_button_click");
      expect(canMutateQueryState("coverage_button_click")).toBe(true);
    });
  });

  describe("State Change Validation", () => {
    test("Read-only events cannot change Query State", () => {
      const readOnlyEvents = [
        "evidence_view",
        "policy_view",
        "document_view",
        "document_page_change",
        "document_close",
        "tab_change",
      ];

      const queryStateKeys = ["messages", "currentResponse", "currentAnchor", "isLoading"];

      for (const event of readOnlyEvents) {
        for (const stateKey of queryStateKeys) {
          const violation = validateStateChange(event, stateKey);
          expect(violation).not.toBeNull();
          expect(violation).toContain("blocked");
        }
      }
    });

    test("Read-only events can change View State", () => {
      const readOnlyEvents = [
        "evidence_view",
        "policy_view",
        "document_view",
      ];

      const viewStateKeys = ["viewingDocument", "activeTab", "scrollPosition"];

      for (const event of readOnlyEvents) {
        for (const stateKey of viewStateKeys) {
          const violation = validateStateChange(event, stateKey);
          expect(violation).toBeNull();
        }
      }
    });

    test("Query mutation events can change Query State", () => {
      const mutationEvents = ["send_message", "coverage_button_click"];
      const queryStateKeys = ["messages", "currentResponse"];

      for (const event of mutationEvents) {
        for (const stateKey of queryStateKeys) {
          const violation = validateStateChange(event, stateKey);
          expect(violation).toBeNull();
        }
      }
    });
  });

  describe("Verification Scenarios", () => {
    /**
     * 시나리오 1: "삼성의 암진단비 알려줘"
     * - 좌측 요약 정상 표시
     * - send_message 이벤트로 Query State 변경 가능
     */
    test("Scenario 1: Query can modify Query State", () => {
      expect(canMutateQueryState("send_message")).toBe(true);
      expect(validateStateChange("send_message", "messages")).toBeNull();
      expect(validateStateChange("send_message", "currentResponse")).toBeNull();
    });

    /**
     * 시나리오 2: Evidence 탭 → 상품요약서 상세보기 클릭
     * - 문서 뷰어 열림
     * - 좌측 요약 내용 변경 없음
     */
    test("Scenario 2: Evidence view does not modify Query State", () => {
      expect(isReadOnlyEvent("evidence_view")).toBe(true);
      expect(validateStateChange("evidence_view", "messages")).not.toBeNull();
      expect(validateStateChange("evidence_view", "currentResponse")).not.toBeNull();
      expect(validateStateChange("evidence_view", "currentAnchor")).not.toBeNull();

      // But can modify View State
      expect(validateStateChange("evidence_view", "viewingDocument")).toBeNull();
    });

    /**
     * 시나리오 3: 문서 페이지 이동
     * - Query 결과 불변
     */
    test("Scenario 3: Page change does not modify Query State", () => {
      expect(isReadOnlyEvent("document_page_change")).toBe(true);
      expect(validateStateChange("document_page_change", "messages")).not.toBeNull();
      expect(validateStateChange("document_page_change", "currentResponse")).not.toBeNull();
    });

    /**
     * 시나리오 4: 문서 닫기
     * - 동일 Query 결과 유지
     */
    test("Scenario 4: Document close does not modify Query State", () => {
      expect(isReadOnlyEvent("document_close")).toBe(true);
      expect(validateStateChange("document_close", "messages")).not.toBeNull();
      expect(validateStateChange("document_close", "currentResponse")).not.toBeNull();
      expect(validateStateChange("document_close", "currentAnchor")).not.toBeNull();
    });
  });
});
