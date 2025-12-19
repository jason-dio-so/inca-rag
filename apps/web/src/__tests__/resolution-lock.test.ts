/**
 * STEP 3.7-δ: Resolution Lock Unit Tests
 *
 * Resolution 상태 전이 규칙 및 Lock 동작 검증
 * - EXACT 상태 퇴행 방지
 * - 리셋 조건 감지
 * - anchor 업데이트 로직
 */

import { describe, test, expect } from "vitest";
import {
  isTransitionAllowed,
  isResolutionLocked,
  isLockViolation,
  isNewCoverageQuery,
  detectResetCondition,
  resolveAnchorUpdate,
  resolveResolutionState,
} from "../lib/resolution-lock.config";
import { QueryAnchor, CoverageResolution } from "../lib/types";

describe("STEP 3.7-δ: Resolution Lock Config", () => {
  describe("State Transition Rules", () => {
    test("NULL → EXACT is allowed", () => {
      expect(isTransitionAllowed(null, "EXACT")).toBe(true);
    });

    test("NULL → AMBIGUOUS is allowed", () => {
      expect(isTransitionAllowed(null, "AMBIGUOUS")).toBe(true);
    });

    test("NULL → NOT_FOUND is allowed", () => {
      expect(isTransitionAllowed(null, "NOT_FOUND")).toBe(true);
    });

    test("AMBIGUOUS → EXACT is allowed", () => {
      expect(isTransitionAllowed("AMBIGUOUS", "EXACT")).toBe(true);
    });

    test("NOT_FOUND → EXACT is allowed", () => {
      expect(isTransitionAllowed("NOT_FOUND", "EXACT")).toBe(true);
    });

    test("EXACT → EXACT is allowed (same state)", () => {
      expect(isTransitionAllowed("EXACT", "EXACT")).toBe(true);
    });

    test("EXACT → AMBIGUOUS is FORBIDDEN", () => {
      expect(isTransitionAllowed("EXACT", "AMBIGUOUS")).toBe(false);
    });

    test("EXACT → NOT_FOUND is FORBIDDEN", () => {
      expect(isTransitionAllowed("EXACT", "NOT_FOUND")).toBe(false);
    });
  });

  describe("Resolution Lock Detection", () => {
    test("isResolutionLocked returns false for null anchor", () => {
      expect(isResolutionLocked(null)).toBe(false);
    });

    test("isResolutionLocked returns true for anchor with coverage_code", () => {
      const anchor: QueryAnchor = {
        coverage_code: "A4200_1",
        coverage_name: "암진단비",
        original_query: "삼성 암진단비",
        intent: "compare",
      };
      expect(isResolutionLocked(anchor)).toBe(true);
    });
  });

  describe("Lock Violation Detection", () => {
    const lockedAnchor: QueryAnchor = {
      coverage_code: "A4200_1",
      coverage_name: "암진단비",
      original_query: "삼성 암진단비",
      intent: "compare",
    };

    test("No violation when not locked", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };
      expect(isLockViolation(null, resolution)).toBe(false);
    });

    test("No violation when new resolution is EXACT", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(isLockViolation(lockedAnchor, resolution)).toBe(false);
    });

    test("Violation when locked and new resolution is AMBIGUOUS", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };
      expect(isLockViolation(lockedAnchor, resolution)).toBe(true);
    });

    test("Violation when locked and new resolution is NOT_FOUND", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        suggested_coverages: [],
      };
      expect(isLockViolation(lockedAnchor, resolution)).toBe(true);
    });
  });

  describe("Reset Condition Detection", () => {
    const currentAnchor: QueryAnchor = {
      coverage_code: "A4200_1",
      coverage_name: "암진단비",
      original_query: "삼성 암진단비",
      intent: "compare",
    };

    test("isNewCoverageQuery returns false when anchor is null", () => {
      expect(isNewCoverageQuery("뇌졸중진단비", null)).toBe(false);
    });

    test("isNewCoverageQuery returns false when query contains current coverage", () => {
      expect(isNewCoverageQuery("삼성 암진단비 비교", currentAnchor)).toBe(false);
    });

    test("isNewCoverageQuery returns true for different coverage keyword", () => {
      expect(isNewCoverageQuery("뇌졸중진단비", currentAnchor)).toBe(true);
    });

    test("detectResetCondition returns RESET_ANCHOR_EVENT for explicit reset", () => {
      expect(detectResetCondition("any query", currentAnchor, true)).toBe(
        "RESET_ANCHOR_EVENT"
      );
    });

    test("detectResetCondition returns NEW_COVERAGE_QUERY for new coverage", () => {
      expect(detectResetCondition("뇌졸중진단비", currentAnchor, false)).toBe(
        "NEW_COVERAGE_QUERY"
      );
    });

    test("detectResetCondition returns null for same coverage query", () => {
      expect(detectResetCondition("삼성 암진단비", currentAnchor, false)).toBeNull();
    });
  });

  describe("Anchor Update Resolution", () => {
    const currentAnchor: QueryAnchor = {
      coverage_code: "A4200_1",
      coverage_name: "암진단비",
      original_query: "삼성 암진단비",
      intent: "compare",
    };

    const newAnchor: QueryAnchor = {
      coverage_code: "B1000_1",
      coverage_name: "뇌졸중진단비",
      original_query: "뇌졸중진단비",
      intent: "compare",
    };

    const ambiguousResolution: CoverageResolution = {
      status: "suggest",
      suggested_coverages: [],
    };

    const exactResolution: CoverageResolution = {
      status: "resolved",
      suggested_coverages: [],
    };

    test("On reset condition, use new anchor", () => {
      const result = resolveAnchorUpdate(
        currentAnchor,
        newAnchor,
        ambiguousResolution,
        "NEW_COVERAGE_QUERY"
      );
      expect(result).toEqual(newAnchor);
    });

    test("On lock violation, keep current anchor", () => {
      const result = resolveAnchorUpdate(
        currentAnchor,
        null,
        ambiguousResolution,
        null
      );
      expect(result).toEqual(currentAnchor);
    });

    test("On normal EXACT transition, use new anchor", () => {
      const result = resolveAnchorUpdate(
        currentAnchor,
        newAnchor,
        exactResolution,
        null
      );
      expect(result).toEqual(newAnchor);
    });
  });

  describe("Resolution State Resolution", () => {
    const currentAnchor: QueryAnchor = {
      coverage_code: "A4200_1",
      coverage_name: "암진단비",
      original_query: "삼성 암진단비",
      intent: "compare",
    };

    test("On reset condition, use new resolution state", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };
      const result = resolveResolutionState(
        currentAnchor,
        resolution,
        "NEW_COVERAGE_QUERY"
      );
      expect(result).toBe("AMBIGUOUS");
    });

    test("On lock violation, maintain EXACT state", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };
      const result = resolveResolutionState(currentAnchor, resolution, null);
      expect(result).toBe("EXACT");
    });

    test("Normal EXACT transition returns EXACT", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      const result = resolveResolutionState(currentAnchor, resolution, null);
      expect(result).toBe("EXACT");
    });
  });

  describe("Verification Scenarios", () => {
    /**
     * 시나리오 1: EXACT → 후속 질의 AMBIGUOUS → Lock 유지
     * - "삼성 암진단비" → EXACT (anchor 설정)
     * - "보험료 얼마?" → AMBIGUOUS 응답 (담보 키워드 없음)
     * - Lock: 기존 anchor 유지, EXACT 상태 유지
     */
    test("Scenario 1: EXACT → AMBIGUOUS query → Lock maintained", () => {
      const anchor: QueryAnchor = {
        coverage_code: "A4200_1",
        coverage_name: "암진단비",
        original_query: "삼성 암진단비",
        intent: "compare",
      };

      const ambiguousResolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };

      // 담보 키워드 없는 질의 → 리셋 조건 아님
      const resetCondition = detectResetCondition("보험료 얼마?", anchor, false);
      expect(resetCondition).toBeNull();

      // Lock 위반 감지
      expect(isLockViolation(anchor, ambiguousResolution)).toBe(true);

      // anchor 유지
      const resolvedAnchor = resolveAnchorUpdate(
        anchor,
        null,
        ambiguousResolution,
        null
      );
      expect(resolvedAnchor).toEqual(anchor);

      // EXACT 상태 유지
      const state = resolveResolutionState(anchor, ambiguousResolution, null);
      expect(state).toBe("EXACT");
    });

    /**
     * 시나리오 2: EXACT → 새 담보 키워드 → Reset
     * - "삼성 암진단비" → EXACT (anchor: 암진단비)
     * - "뇌졸중진단비" → 새 담보 키워드 감지
     * - Reset: anchor 초기화, 새 응답 사용
     */
    test("Scenario 2: EXACT → New coverage query → Reset", () => {
      const anchor: QueryAnchor = {
        coverage_code: "A4200_1",
        coverage_name: "암진단비",
        original_query: "삼성 암진단비",
        intent: "compare",
      };

      const ambiguousResolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };

      // 새 담보 키워드 → 리셋 조건
      const resetCondition = detectResetCondition("뇌졸중진단비", anchor, false);
      expect(resetCondition).toBe("NEW_COVERAGE_QUERY");

      // 리셋이므로 새 상태 사용
      const state = resolveResolutionState(anchor, ambiguousResolution, resetCondition);
      expect(state).toBe("AMBIGUOUS");
    });

    /**
     * 시나리오 3: AMBIGUOUS → EXACT (정상 전이)
     * - "삼성 암" → AMBIGUOUS (선택 필요)
     * - 사용자가 "암진단비" 선택 → EXACT
     * - 정상 전이
     */
    test("Scenario 3: AMBIGUOUS → EXACT (normal transition)", () => {
      // AMBIGUOUS 상태 (anchor 없음)
      const exactResolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };

      const newAnchor: QueryAnchor = {
        coverage_code: "A4200_1",
        coverage_name: "암진단비",
        original_query: "암진단비",
        intent: "compare",
      };

      // 전이 허용
      expect(isTransitionAllowed("AMBIGUOUS", "EXACT")).toBe(true);

      // Lock 없음 → 위반 없음
      expect(isLockViolation(null, exactResolution)).toBe(false);

      // 새 anchor 사용
      const resolvedAnchor = resolveAnchorUpdate(
        null,
        newAnchor,
        exactResolution,
        null
      );
      expect(resolvedAnchor).toEqual(newAnchor);
    });
  });
});
