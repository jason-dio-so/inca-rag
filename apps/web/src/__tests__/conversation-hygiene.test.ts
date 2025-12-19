/**
 * STEP 3.7-γ: Conversation Hygiene Unit Tests
 *
 * 담보 미확정 상태에서 가이드 메시지가 대화 로그에 누적되지 않고,
 * 단일 상태 패널(UI State)로 격리되는지 검증
 */

import { describe, test, expect } from "vitest";
import {
  CoverageGuideState,
  CHAT_MESSAGE_ALLOWED_STATES,
  canAddToChatLog,
  shouldShowCoverageGuide,
  createCoverageGuideState,
  isGuideValidForQuery,
  shouldReplaceGuide,
  GUIDE_MESSAGES,
} from "../lib/conversation-hygiene.config";
import { CoverageResolution } from "../lib/types";

describe("STEP 3.7-γ: Conversation Hygiene Config", () => {
  describe("Chat Message Eligibility", () => {
    test("Only EXACT state allows ChatMessage addition", () => {
      expect(CHAT_MESSAGE_ALLOWED_STATES).toEqual(["EXACT"]);
      expect(CHAT_MESSAGE_ALLOWED_STATES).not.toContain("AMBIGUOUS");
      expect(CHAT_MESSAGE_ALLOWED_STATES).not.toContain("NOT_FOUND");
    });

    test("canAddToChatLog returns true for resolved status", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(canAddToChatLog(resolution)).toBe(true);
    });

    test("canAddToChatLog returns false for suggest status", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };
      expect(canAddToChatLog(resolution)).toBe(false);
    });

    test("canAddToChatLog returns false for clarify status", () => {
      const resolution: CoverageResolution = {
        status: "clarify",
        suggested_coverages: [],
      };
      expect(canAddToChatLog(resolution)).toBe(false);
    });

    test("canAddToChatLog returns false for failed status", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        suggested_coverages: [],
      };
      expect(canAddToChatLog(resolution)).toBe(false);
    });

    test("canAddToChatLog returns true for null/undefined (backward compatibility)", () => {
      expect(canAddToChatLog(null)).toBe(true);
      expect(canAddToChatLog(undefined)).toBe(true);
    });
  });

  describe("Coverage Guide Display", () => {
    test("shouldShowCoverageGuide returns true for AMBIGUOUS", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };
      expect(shouldShowCoverageGuide(resolution)).toBe(true);
    });

    test("shouldShowCoverageGuide returns true for NOT_FOUND", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        suggested_coverages: [],
      };
      expect(shouldShowCoverageGuide(resolution)).toBe(true);
    });

    test("shouldShowCoverageGuide returns false for EXACT", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(shouldShowCoverageGuide(resolution)).toBe(false);
    });

    test("shouldShowCoverageGuide returns false for null", () => {
      expect(shouldShowCoverageGuide(null)).toBe(false);
    });
  });

  describe("Coverage Guide State Factory", () => {
    test("createCoverageGuideState returns null for EXACT", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(createCoverageGuideState(resolution, "삼성 암진단비")).toBeNull();
    });

    test("createCoverageGuideState returns AMBIGUOUS state for suggest", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        message: "여러 담보가 검색되었습니다",
        suggested_coverages: [
          { coverage_code: "C001", coverage_name: "암진단비", similarity: 0.9 },
        ],
      };
      const guide = createCoverageGuideState(resolution, "삼성 암");

      expect(guide).not.toBeNull();
      expect(guide?.resolutionState).toBe("AMBIGUOUS");
      expect(guide?.message).toBe("여러 담보가 검색되었습니다");
      expect(guide?.suggestedCoverages).toHaveLength(1);
      expect(guide?.originalQuery).toBe("삼성 암");
    });

    test("createCoverageGuideState returns NOT_FOUND state for failed", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        message: "담보명을 인식하지 못했습니다",
        suggested_coverages: [],
      };
      const guide = createCoverageGuideState(resolution, "삼성 암zz");

      expect(guide).not.toBeNull();
      expect(guide?.resolutionState).toBe("NOT_FOUND");
      expect(guide?.message).toBe("담보명을 인식하지 못했습니다");
      expect(guide?.originalQuery).toBe("삼성 암zz");
    });

    test("createCoverageGuideState preserves detected_domain for clarify", () => {
      const resolution: CoverageResolution = {
        status: "clarify",
        detected_domain: "cancer",
        suggested_coverages: [],
      };
      const guide = createCoverageGuideState(resolution, "삼성 암");

      expect(guide).not.toBeNull();
      expect(guide?.resolutionState).toBe("AMBIGUOUS");
      expect(guide?.detectedDomain).toBe("cancer");
    });
  });

  describe("Guide Validity", () => {
    test("isGuideValidForQuery returns true for matching query", () => {
      const guide: CoverageGuideState = {
        resolutionState: "AMBIGUOUS",
        message: "test",
        suggestedCoverages: [],
        originalQuery: "삼성 암",
      };
      expect(isGuideValidForQuery(guide, "삼성 암")).toBe(true);
    });

    test("isGuideValidForQuery returns false for different query", () => {
      const guide: CoverageGuideState = {
        resolutionState: "AMBIGUOUS",
        message: "test",
        suggestedCoverages: [],
        originalQuery: "삼성 암",
      };
      expect(isGuideValidForQuery(guide, "메리츠 암")).toBe(false);
    });

    test("isGuideValidForQuery returns false for null guide", () => {
      expect(isGuideValidForQuery(null, "삼성 암")).toBe(false);
    });
  });

  describe("Guide Replacement", () => {
    test("shouldReplaceGuide returns true for different query", () => {
      const guide: CoverageGuideState = {
        resolutionState: "AMBIGUOUS",
        message: "test",
        suggestedCoverages: [],
        originalQuery: "삼성 암",
      };
      expect(shouldReplaceGuide(guide, "메리츠 암")).toBe(true);
    });

    test("shouldReplaceGuide returns false for same query", () => {
      const guide: CoverageGuideState = {
        resolutionState: "AMBIGUOUS",
        message: "test",
        suggestedCoverages: [],
        originalQuery: "삼성 암",
      };
      expect(shouldReplaceGuide(guide, "삼성 암")).toBe(false);
    });

    test("shouldReplaceGuide returns false for null guide", () => {
      expect(shouldReplaceGuide(null, "삼성 암")).toBe(false);
    });
  });

  describe("Guide Messages", () => {
    test("AMBIGUOUS guide messages are defined", () => {
      expect(GUIDE_MESSAGES.AMBIGUOUS.title).toBe("담보 선택 필요");
      expect(GUIDE_MESSAGES.AMBIGUOUS.description).toContain("선택");
      expect(GUIDE_MESSAGES.AMBIGUOUS.hint).toBeDefined();
    });

    test("NOT_FOUND guide messages are defined", () => {
      expect(GUIDE_MESSAGES.NOT_FOUND.title).toBe("담보 미확정");
      expect(GUIDE_MESSAGES.NOT_FOUND.description).toContain("인식");
      expect(GUIDE_MESSAGES.NOT_FOUND.hint).toBeDefined();
    });
  });

  describe("Verification Scenarios", () => {
    /**
     * 시나리오 1: "삼성 암" → AMBIGUOUS
     * - Chat 로그에 사용자 질의만 추가
     * - Coverage Guide Panel 표시
     * - 가이드 메시지는 ChatMessage 아님
     */
    test("Scenario 1: 삼성 암 → AMBIGUOUS → Guide shown, no ChatMessage", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        message: "여러 담보가 검색되었습니다",
        suggested_coverages: [
          { coverage_code: "C001", coverage_name: "암진단비", similarity: 0.9 },
          { coverage_code: "C002", coverage_name: "유사암진단비", similarity: 0.8 },
        ],
      };

      // ChatMessage 추가 불가
      expect(canAddToChatLog(resolution)).toBe(false);
      // Guide Panel 표시 필요
      expect(shouldShowCoverageGuide(resolution)).toBe(true);
      // Guide 상태 생성
      const guide = createCoverageGuideState(resolution, "삼성 암");
      expect(guide).not.toBeNull();
      expect(guide?.resolutionState).toBe("AMBIGUOUS");
      expect(guide?.suggestedCoverages).toHaveLength(2);
    });

    /**
     * 시나리오 2: "삼성 암진단비" → EXACT
     * - Chat 로그에 사용자 질의 + 응답 추가
     * - Coverage Guide Panel 없음
     * - Results Panel 활성화
     */
    test("Scenario 2: 삼성 암진단비 → EXACT → ChatMessage added, no Guide", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };

      // ChatMessage 추가 가능
      expect(canAddToChatLog(resolution)).toBe(true);
      // Guide Panel 표시 불필요
      expect(shouldShowCoverageGuide(resolution)).toBe(false);
      // Guide 상태 생성 시 null
      const guide = createCoverageGuideState(resolution, "삼성 암진단비");
      expect(guide).toBeNull();
    });

    /**
     * 시나리오 3: "삼성 암zz" → NOT_FOUND
     * - Chat 로그에 사용자 질의만 추가
     * - Coverage Guide Panel 표시 (힌트 메시지)
     */
    test("Scenario 3: 삼성 암zz → NOT_FOUND → Guide shown, no ChatMessage", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        message: "담보명을 인식하지 못했습니다",
        suggested_coverages: [],
      };

      // ChatMessage 추가 불가
      expect(canAddToChatLog(resolution)).toBe(false);
      // Guide Panel 표시 필요
      expect(shouldShowCoverageGuide(resolution)).toBe(true);
      // Guide 상태 생성
      const guide = createCoverageGuideState(resolution, "삼성 암zz");
      expect(guide).not.toBeNull();
      expect(guide?.resolutionState).toBe("NOT_FOUND");
    });

    /**
     * 시나리오 4: 연속 질의 시 가이드 교체
     * - 새 질의가 들어오면 기존 가이드 제거
     * - 새 가이드로 교체 (누적 금지)
     */
    test("Scenario 4: Sequential queries replace guide (no accumulation)", () => {
      // 첫 번째 질의 가이드
      const guide1: CoverageGuideState = {
        resolutionState: "AMBIGUOUS",
        message: "test1",
        suggestedCoverages: [],
        originalQuery: "삼성 암",
      };

      // 새 질의가 들어옴
      expect(shouldReplaceGuide(guide1, "메리츠 암")).toBe(true);

      // 가이드는 새 질의로 교체됨
      const resolution2: CoverageResolution = {
        status: "suggest",
        message: "test2",
        suggested_coverages: [],
      };
      const guide2 = createCoverageGuideState(resolution2, "메리츠 암");

      expect(guide2?.originalQuery).toBe("메리츠 암");
      // 이전 가이드와 다름
      expect(guide2?.originalQuery).not.toBe(guide1.originalQuery);
    });
  });
});
