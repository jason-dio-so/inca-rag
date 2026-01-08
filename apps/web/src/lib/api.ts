import {
  CompareRequestWithIntent,
  CompareResponseWithSlots,
  QueryAssistRequest,
  QueryAssistResponse,
  EvidenceSummaryRequest,
  EvidenceSummaryResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const TIMEOUT_MS = 20000;

// U-4.18: Sanitize error messages to remove HTML/nginx responses
function sanitizeErrorMessage(message: string): string {
  // Check if message contains HTML
  if (message.includes("<html") || message.includes("<!DOCTYPE") || message.includes("<body")) {
    return "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
  }
  // Remove any remaining HTML tags
  const stripped = message.replace(/<[^>]*>/g, "").trim();
  if (stripped.length === 0) {
    return "서버 오류가 발생했습니다.";
  }
  return stripped;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number
  ) {
    // U-4.18: Sanitize message to remove HTML
    super(sanitizeErrorMessage(message));
    this.name = "ApiError";
  }
}

export async function compare(request: CompareRequestWithIntent): Promise<CompareResponseWithSlots> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    // Build request body, excluding undefined/empty values
    const body: Record<string, unknown> = {
      insurers: request.insurers,
      query: request.query,
    };

    if (request.age !== undefined) {
      body.age = request.age;
    }
    if (request.gender) {
      body.gender = request.gender;
    }
    if (request.top_k_per_insurer !== undefined) {
      body.top_k_per_insurer = request.top_k_per_insurer;
    }
    if (request.coverage_codes && request.coverage_codes.length > 0) {
      body.coverage_codes = request.coverage_codes;
    }
    if (request.policy_keywords && request.policy_keywords.length > 0) {
      body.policy_keywords = request.policy_keywords;
    }
    // STEP 2.9 + 3.6: anchor with intent
    if (request.anchor) {
      body.anchor = request.anchor;
    }
    // STEP 3.6: UI event type (for intent locking)
    if (request.ui_event_type) {
      body.ui_event_type = request.ui_event_type;
    }
    // STEP 3.9: locked_coverage_code for anchor persistence
    if (request.locked_coverage_code) {
      body.locked_coverage_code = request.locked_coverage_code;
    }
    // STEP 4.5: locked_coverage_codes for multi-subtype support
    if (request.locked_coverage_codes && request.locked_coverage_codes.length > 0) {
      body.locked_coverage_codes = request.locked_coverage_codes;
    }

    const response = await fetch(`${API_BASE}/compare`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(
        `API error: ${response.status} - ${errorText}`,
        response.status
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error) {
      if (error.name === "AbortError") {
        throw new ApiError("요청 시간이 초과되었습니다 (20초)");
      }
      throw new ApiError(error.message);
    }
    throw new ApiError("알 수 없는 오류가 발생했습니다");
  } finally {
    clearTimeout(timeoutId);
  }
}

// Helper to format evidence reference for clipboard
// document_id is number from API, pageStart can be null
export function formatEvidenceRef(documentId: number | string, pageStart: number | null): string {
  return `${documentId}:${pageStart ?? 0}`;
}

// Copy text to clipboard
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

// =============================================================================
// STEP 5: LLM Assist API
// =============================================================================

const ASSIST_TIMEOUT_MS = 10000;

/**
 * Query Assist - 질의 정규화/힌트 제공
 *
 * 핵심 원칙:
 * - 자동 반영 금지 (사용자 Apply 필수)
 * - soft-fail: 실패해도 undefined 반환, 시스템 정상 동작
 */
export async function queryAssist(
  request: QueryAssistRequest
): Promise<QueryAssistResponse | undefined> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ASSIST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}/assist/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!response.ok) {
      console.warn(`Query assist failed: ${response.status}`);
      return undefined;
    }

    return await response.json();
  } catch (error) {
    // Soft-fail: 에러 시 undefined 반환
    console.warn("Query assist error:", error);
    return undefined;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Evidence Summary - 비판단 요약
 *
 * 핵심 원칙:
 * - 판단 없는 요약만 제공
 * - soft-fail: 실패해도 undefined 반환, 시스템 정상 동작
 */
export async function evidenceSummary(
  request: EvidenceSummaryRequest
): Promise<EvidenceSummaryResponse | undefined> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ASSIST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}/assist/summary`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!response.ok) {
      console.warn(`Evidence summary failed: ${response.status}`);
      return undefined;
    }

    return await response.json();
  } catch (error) {
    // Soft-fail: 에러 시 undefined 반환
    console.warn("Evidence summary error:", error);
    return undefined;
  } finally {
    clearTimeout(timeoutId);
  }
}
