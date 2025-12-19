/**
 * STEP 3.7-β: UI Gating Unit Tests
 *
 * Coverage Resolution 상태에 따른 Results Panel 렌더링 제어 검증
 */

import {
  getUIResolutionState,
  canRenderResultsPanel,
  getResolutionMessage,
  isCoverageResolved,
  RESOLUTION_STATUS_MAP,
  RESULTS_PANEL_ALLOWED_STATES,
} from "../lib/ui-gating.config";
import { CoverageResolution } from "../lib/types";

describe("STEP 3.7-β: UI Gating Config", () => {
  describe("Resolution Status Mapping", () => {
    test("resolved → EXACT", () => {
      expect(RESOLUTION_STATUS_MAP["resolved"]).toBe("EXACT");
    });

    test("suggest → AMBIGUOUS", () => {
      expect(RESOLUTION_STATUS_MAP["suggest"]).toBe("AMBIGUOUS");
    });

    test("clarify → AMBIGUOUS", () => {
      expect(RESOLUTION_STATUS_MAP["clarify"]).toBe("AMBIGUOUS");
    });

    test("failed → NOT_FOUND", () => {
      expect(RESOLUTION_STATUS_MAP["failed"]).toBe("NOT_FOUND");
    });
  });

  describe("getUIResolutionState", () => {
    test("resolved status returns EXACT", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(getUIResolutionState(resolution)).toBe("EXACT");
    });

    test("suggest status returns AMBIGUOUS", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [
          { coverage_code: "C001", coverage_name: "암진단비", similarity: 0.9 },
        ],
      };
      expect(getUIResolutionState(resolution)).toBe("AMBIGUOUS");
    });

    test("clarify status returns AMBIGUOUS", () => {
      const resolution: CoverageResolution = {
        status: "clarify",
        detected_domain: "cancer",
        suggested_coverages: [],
      };
      expect(getUIResolutionState(resolution)).toBe("AMBIGUOUS");
    });

    test("failed status returns NOT_FOUND", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        message: "담보를 찾을 수 없습니다",
        suggested_coverages: [],
      };
      expect(getUIResolutionState(resolution)).toBe("NOT_FOUND");
    });

    test("null resolution returns EXACT (backward compatibility)", () => {
      expect(getUIResolutionState(null)).toBe("EXACT");
      expect(getUIResolutionState(undefined)).toBe("EXACT");
    });
  });

  describe("canRenderResultsPanel", () => {
    test("EXACT state allows rendering", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(canRenderResultsPanel(resolution)).toBe(true);
    });

    test("AMBIGUOUS state blocks rendering", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };
      expect(canRenderResultsPanel(resolution)).toBe(false);
    });

    test("NOT_FOUND state blocks rendering", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        suggested_coverages: [],
      };
      expect(canRenderResultsPanel(resolution)).toBe(false);
    });

    test("null resolution allows rendering (backward compatibility)", () => {
      expect(canRenderResultsPanel(null)).toBe(true);
    });
  });

  describe("getResolutionMessage", () => {
    test("EXACT returns empty message", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(getResolutionMessage(resolution)).toBe("");
    });

    test("AMBIGUOUS returns selection message", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        suggested_coverages: [],
      };
      const message = getResolutionMessage(resolution);
      expect(message).toContain("선택");
    });

    test("NOT_FOUND returns confirmation message", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        suggested_coverages: [],
      };
      const message = getResolutionMessage(resolution);
      expect(message).toContain("확정");
    });
  });

  describe("isCoverageResolved", () => {
    test("resolved status returns true", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(isCoverageResolved(resolution)).toBe(true);
    });

    test("non-resolved status returns false", () => {
      expect(
        isCoverageResolved({ status: "suggest", suggested_coverages: [] })
      ).toBe(false);
      expect(
        isCoverageResolved({ status: "failed", suggested_coverages: [] })
      ).toBe(false);
      expect(
        isCoverageResolved({ status: "clarify", suggested_coverages: [] })
      ).toBe(false);
    });

    test("null/undefined returns false", () => {
      expect(isCoverageResolved(null)).toBe(false);
      expect(isCoverageResolved(undefined)).toBe(false);
    });
  });

  describe("Verification Scenarios", () => {
    /**
     * 시나리오 1: "삼성 암"
     * - 상태: AMBIGUOUS (suggest)
     * - Results Panel: 차단
     */
    test("Scenario 1: 삼성 암 → AMBIGUOUS → Panel blocked", () => {
      const resolution: CoverageResolution = {
        status: "suggest",
        message: "여러 담보가 검색되었습니다",
        suggested_coverages: [
          { coverage_code: "C001", coverage_name: "암진단비", similarity: 0.95 },
          { coverage_code: "C002", coverage_name: "유사암진단비", similarity: 0.8 },
        ],
      };
      expect(getUIResolutionState(resolution)).toBe("AMBIGUOUS");
      expect(canRenderResultsPanel(resolution)).toBe(false);
    });

    /**
     * 시나리오 2: "삼성 암진단비"
     * - 상태: EXACT (resolved)
     * - Results Panel: 정상 표시
     */
    test("Scenario 2: 삼성 암진단비 → EXACT → Panel rendered", () => {
      const resolution: CoverageResolution = {
        status: "resolved",
        suggested_coverages: [],
      };
      expect(getUIResolutionState(resolution)).toBe("EXACT");
      expect(canRenderResultsPanel(resolution)).toBe(true);
    });

    /**
     * 시나리오 3: "삼성 암zz"
     * - 상태: NOT_FOUND (failed)
     * - Results Panel: 차단
     */
    test("Scenario 3: 삼성 암zz → NOT_FOUND → Panel blocked", () => {
      const resolution: CoverageResolution = {
        status: "failed",
        message: "담보명을 인식하지 못했습니다",
        suggested_coverages: [],
      };
      expect(getUIResolutionState(resolution)).toBe("NOT_FOUND");
      expect(canRenderResultsPanel(resolution)).toBe(false);
    });
  });

  describe("Only EXACT allows Results Panel", () => {
    test("RESULTS_PANEL_ALLOWED_STATES only contains EXACT", () => {
      expect(RESULTS_PANEL_ALLOWED_STATES).toEqual(["EXACT"]);
      expect(RESULTS_PANEL_ALLOWED_STATES).not.toContain("AMBIGUOUS");
      expect(RESULTS_PANEL_ALLOWED_STATES).not.toContain("NOT_FOUND");
    });
  });
});
