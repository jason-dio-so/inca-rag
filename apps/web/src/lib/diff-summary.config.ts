/**
 * STEP 4.0: Diff Summary Text Configuration
 *
 * Diff 요약 문구 생성 규칙
 * - 비교 결과 요약만 담당 (유리/불리/추천 표현 금지)
 * - 새로운 계산 로직 추가 금지
 * - 기존 Diff 계산 결과를 텍스트로 변환만 수행
 */

// 보험사 한글명 매핑
export const INSURER_NAMES: Record<string, string> = {
  SAMSUNG: "삼성",
  LOTTE: "롯데",
  DB: "DB",
  KB: "KB",
  MERITZ: "메리츠",
  HANWHA: "한화",
  HYUNDAI: "현대",
  HEUNGKUK: "흥국",
};

// 필드별 한글명 매핑
export const FIELD_NAMES: Record<string, string> = {
  amount: "지급금액",
  limit: "한도",
  condition: "지급조건",
  surgery_type: "수술유형",
  hospital_grade: "병원급",
  waiting_period: "면책기간",
  renewal_period: "갱신주기",
  coverage_term: "보장기간",
};

// 단위 매핑
export const UNITS: Record<string, string> = {
  amount: "원",
  percentage: "%",
  days: "일",
  months: "개월",
  years: "년",
};

/**
 * Diff 요약 문구 생성
 * - 기존 계산된 diff 데이터를 사용
 * - 새로운 계산/비교 로직 추가 금지
 */
export interface DiffSummaryText {
  type: "higher" | "lower" | "equal" | "different" | "missing";
  text: string;
  field?: string;
  insurers?: string[];
}

/**
 * 숫자 값에서 금액 추출 시도
 */
function extractNumericValue(text: string): number | null {
  // "500만원", "3,000만원", "1000원" 등의 패턴
  const patterns = [
    /(\d{1,3}(?:,\d{3})*)만\s*원/,  // N만원
    /(\d{1,3}(?:,\d{3})*)\s*원/,    // N원
    /(\d+(?:\.\d+)?)\s*%/,          // N%
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      const numStr = match[1].replace(/,/g, "");
      const num = parseFloat(numStr);
      if (!isNaN(num)) {
        // 만원 단위면 10000 곱하기
        if (text.includes("만원") || text.includes("만 원")) {
          return num * 10000;
        }
        return num;
      }
    }
  }
  return null;
}

/**
 * 금액 포맷팅 (예: 25000000 → "2,500만원")
 */
function formatAmount(value: number): string {
  if (value >= 10000) {
    const man = value / 10000;
    if (man >= 1) {
      return `${man.toLocaleString()}만원`;
    }
  }
  return `${value.toLocaleString()}원`;
}

/**
 * Diff bullet 텍스트에서 요약 생성
 * 주의: 기존 텍스트 분석만 수행, 새로운 비교 로직 추가 금지
 */
export function generateDiffSummaryTexts(
  bulletTexts: string[],
  insurerCodes: string[]
): DiffSummaryText[] {
  const summaries: DiffSummaryText[] = [];
  const insurerNames = insurerCodes.map(code => INSURER_NAMES[code] || code);

  for (const text of bulletTexts) {
    // 이미 요약 형태인 텍스트는 그대로 사용
    if (text.includes("동일") || text.includes("같습니다")) {
      summaries.push({
        type: "equal",
        text: text,
        insurers: insurerCodes,
      });
      continue;
    }

    // "높습니다", "낮습니다" 패턴 감지
    if (text.includes("높습니다") || text.includes("많습니다")) {
      summaries.push({
        type: "higher",
        text: text,
        insurers: insurerCodes,
      });
      continue;
    }

    if (text.includes("낮습니다") || text.includes("적습니다")) {
      summaries.push({
        type: "lower",
        text: text,
        insurers: insurerCodes,
      });
      continue;
    }

    // 조건 차이 패턴
    if (text.includes("조건") && (text.includes("다릅니다") || text.includes("상이"))) {
      summaries.push({
        type: "different",
        text: text,
        insurers: insurerCodes,
      });
      continue;
    }

    // 기본: 그대로 사용
    summaries.push({
      type: "different",
      text: text,
      insurers: insurerCodes,
    });
  }

  return summaries;
}

/**
 * 요약 타입별 스타일
 */
export const SUMMARY_STYLES: Record<DiffSummaryText["type"], {
  bgColor: string;
  textColor: string;
  icon?: string;
}> = {
  higher: {
    bgColor: "bg-blue-50",
    textColor: "text-blue-800",
  },
  lower: {
    bgColor: "bg-blue-50",
    textColor: "text-blue-800",
  },
  equal: {
    bgColor: "bg-green-50",
    textColor: "text-green-800",
  },
  different: {
    bgColor: "bg-amber-50",
    textColor: "text-amber-800",
  },
  missing: {
    bgColor: "bg-gray-50",
    textColor: "text-gray-600",
  },
};
