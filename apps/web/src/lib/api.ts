import { CompareRequest, CompareResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const TIMEOUT_MS = 20000;

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function compare(request: CompareRequest): Promise<CompareResponse> {
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
