/**
 * STEP 4.0: Evidence Priority Configuration
 *
 * Evidence 우선순위 분류 규칙
 * - Evidence 내용을 수정/요약/재작성 금지
 * - 분류만 수행하여 UI 정렬에 활용
 */

import { Evidence } from "./types";

/**
 * 우선순위 레벨
 */
export type EvidencePriority = "P1" | "P2" | "P3";

/**
 * 우선순위 정의
 */
export const PRIORITY_DEFINITIONS: Record<EvidencePriority, {
  name: string;
  description: string;
  icon: string;
  stars: number;
  expanded: boolean;
}> = {
  P1: {
    name: "결정 근거",
    description: "비교 값이 직접 추출된 문장",
    icon: "star-filled",
    stars: 3,
    expanded: true,  // 기본 펼침
  },
  P2: {
    name: "해석 근거",
    description: "정의/조건 설명 문장",
    icon: "star-half",
    stars: 2,
    expanded: false,  // 기본 접힘
  },
  P3: {
    name: "보조 근거",
    description: "요약/설명성 문장",
    icon: "star-outline",
    stars: 1,
    expanded: false,  // 기본 접힘
  },
};

/**
 * doc_type별 기본 우선순위
 */
const DOC_TYPE_PRIORITY: Record<string, EvidencePriority> = {
  가입설계서: "P1",
  상품요약서: "P2",
  사업방법서: "P2",
  약관: "P2",
};

/**
 * P1 판별: 금액/값이 직접 포함된 패턴
 */
const AMOUNT_PATTERNS = [
  /\d+[만천백]?\s*원/,
  /\d+%/,
  /\d+일/,
  /\d+개월/,
  /\d+년/,
];

/**
 * P2 판별: 정의/조건 설명 패턴
 */
const DEFINITION_PATTERNS = [
  /정의/,
  /말합니다/,
  /의미합니다/,
  /적용됩니다/,
  /해당합니다/,
  /규정/,
  /조항/,
];

/**
 * Evidence 우선순위 결정
 * - 기존 evidence 데이터만 분석
 * - 새로운 계산/추론 로직 추가 금지
 */
export function determineEvidencePriority(evidence: Evidence): EvidencePriority {
  const preview = evidence.preview || "";
  const docType = evidence.doc_type || "";

  // Rule 1: 가입설계서에서 추출된 것은 P1
  if (docType === "가입설계서") {
    return "P1";
  }

  // Rule 2: preview에 금액/수치 패턴이 있으면 P1
  for (const pattern of AMOUNT_PATTERNS) {
    if (pattern.test(preview)) {
      return "P1";
    }
  }

  // Rule 3: 약관/사업방법서에서 정의 패턴이 있으면 P2
  if (docType === "약관" || docType === "사업방법서") {
    for (const pattern of DEFINITION_PATTERNS) {
      if (pattern.test(preview)) {
        return "P2";
      }
    }
  }

  // Rule 4: doc_type 기반 기본 우선순위
  if (DOC_TYPE_PRIORITY[docType]) {
    return DOC_TYPE_PRIORITY[docType];
  }

  // Default: P3
  return "P3";
}

/**
 * Evidence 배열을 우선순위로 정렬
 */
export function sortEvidenceByPriority(evidences: Evidence[]): Evidence[] {
  const priorityOrder: Record<EvidencePriority, number> = {
    P1: 1,
    P2: 2,
    P3: 3,
  };

  return [...evidences].sort((a, b) => {
    const priorityA = determineEvidencePriority(a);
    const priorityB = determineEvidencePriority(b);
    return priorityOrder[priorityA] - priorityOrder[priorityB];
  });
}

/**
 * Evidence 배열을 우선순위별로 그룹화
 */
export function groupEvidenceByPriority(evidences: Evidence[]): {
  P1: Evidence[];
  P2: Evidence[];
  P3: Evidence[];
} {
  const groups: { P1: Evidence[]; P2: Evidence[]; P3: Evidence[] } = {
    P1: [],
    P2: [],
    P3: [],
  };

  for (const ev of evidences) {
    const priority = determineEvidencePriority(ev);
    groups[priority].push(ev);
  }

  return groups;
}

/**
 * 우선순위 스타일
 */
export const PRIORITY_STYLES: Record<EvidencePriority, {
  bgColor: string;
  textColor: string;
  borderColor: string;
}> = {
  P1: {
    bgColor: "bg-amber-50",
    textColor: "text-amber-800",
    borderColor: "border-amber-300",
  },
  P2: {
    bgColor: "bg-blue-50",
    textColor: "text-blue-700",
    borderColor: "border-blue-200",
  },
  P3: {
    bgColor: "bg-gray-50",
    textColor: "text-gray-600",
    borderColor: "border-gray-200",
  },
};
