"""
Amount Extractor - Rule-based extraction of insurance amounts

한국어 보험 문서에서 금액/한도 관련 표현을 regex 기반으로 추출
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AmountExtract:
    """금액 추출 결과"""
    amount_value: int | None  # 원 단위 정수 (예: 10000000)
    amount_text: str | None  # 원문 텍스트 (예: "1,000만원")
    currency: str  # 통화 (기본: "KRW")
    unit: str | None  # 단위 ("만원"|"원"|"천만원"|"억원"|None)
    confidence: str  # "high"|"medium"|"low"
    method: str  # 추출 방법 ("regex")
    matched_span: str | None  # 매칭된 원문 일부


# 금액 관련 키워드 (±30자 내 금액 우선) - 기존 호환용
AMOUNT_KEYWORDS = [
    "가입금액",
    "보험금",
    "보장",
    "지급",
    "한도",
    "보장금액",
    "진단비",
    "수술비",
    "입원비",
]

# POSITIVE 키워드: 보험금/가입금액 관련 (우선 선택)
POSITIVE_KEYWORDS = [
    "보험금",
    "가입금액",
    "보장금액",
    "지급금",
    "지급액",
    "진단비",
    "수술비",
    "입원비",
    "사망보험금",
    "한도",
]

# NEGATIVE 키워드: 보험료 관련 (제외)
NEGATIVE_KEYWORDS = [
    "보험료",
    "월납",
    "납입",
    "영업보험료",
    "적립보험료",
    "순보험료",
    "갱신보험료",
    "추가보험료",
    "납입보험료",
    "보험료(원)",
]

# Premium block header tokens (표에서 보험료 컬럼 식별)
# 순서: 더 구체적인 것 먼저, 일반적인 것은 마지막 (매칭 시 우선순위)
PREMIUM_HEADER_TOKENS = [
    "보험료(원)",
    "보험료 (원)",
    "월납보험료",
    "월보험료",
    "납입보험료",
    "영업보험료",
    "적립보험료",
    # "보험료" 단독은 제외 (너무 일반적이라 오탐 유발)
]

# Coverage block header tokens (표에서 보험금/가입금액 컬럼 식별)
COVERAGE_HEADER_TOKENS = [
    "가입금액(만원)",
    "가입금액 (만원)",
    "가입금액(원)",
    "보험금액(만원)",
    "보험금액",
    "보장내용",
    "보장금액",
    "가입금액",
    "담보명",
]

# 단위별 원화 환산 배수
UNIT_MULTIPLIERS = {
    "원": 1,
    "만원": 10_000,
    "만 원": 10_000,
    "천만원": 10_000_000,
    "천만 원": 10_000_000,
    "억원": 100_000_000,
    "억 원": 100_000_000,
}


def _parse_korean_number(num_str: str) -> int | None:
    """
    한국어 숫자 표현을 정수로 변환

    예: "1,000" -> 1000, "3억 5천" -> 350000000
    """
    # 콤마 제거
    num_str = num_str.replace(",", "").replace(" ", "")

    # 순수 숫자인 경우
    if num_str.isdigit():
        return int(num_str)

    # 억/천/백 등 한국어 단위 포함
    result = 0
    current = 0

    # 억 처리
    if "억" in num_str:
        parts = num_str.split("억")
        if parts[0]:
            try:
                current = int(parts[0].replace(",", ""))
            except ValueError:
                return None
            result += current * 100_000_000
        num_str = parts[1] if len(parts) > 1 else ""
        current = 0

    # 천 처리 (천만원의 천이 아닌 경우)
    if "천" in num_str and "천만" not in num_str:
        parts = num_str.split("천")
        if parts[0]:
            try:
                current = int(parts[0].replace(",", ""))
            except ValueError:
                current = 1  # "천"만 있으면 1천
            result += current * 1_000
        num_str = parts[1] if len(parts) > 1 else ""
        current = 0

    # 남은 숫자
    remaining = re.sub(r"[^\d]", "", num_str)
    if remaining:
        try:
            result += int(remaining)
        except ValueError:
            pass

    return result if result > 0 else None


def _find_amounts_with_positions(text: str) -> list[tuple[int, str, str, int | None]]:
    """
    텍스트에서 모든 금액 표현을 찾아 위치와 함께 반환

    Returns:
        [(position, matched_text, unit, value_in_won), ...]
    """
    results = []

    # 패턴 1: 숫자 + 만원/천만원/억원 (띄어쓰기 변형 포함)
    # 예: 1,000만원, 500만 원, 2천만원, 1억원, 3억 5천만원
    pattern_main = r"(\d{1,3}(?:,\d{3})*|\d+)(?:\s*)(억\s*)?(\d{1,3}(?:,\d{3})*|\d+)?(?:\s*)(천만|천|만)?\s*(원)"

    for match in re.finditer(pattern_main, text):
        pos = match.start()
        matched_text = match.group(0).strip()

        # 파싱
        try:
            # 전체 매칭에서 금액 추출
            value = _calculate_amount_value(matched_text)
            unit = _extract_unit(matched_text)
            results.append((pos, matched_text, unit, value))
        except (ValueError, TypeError):
            continue

    # 패턴 2: 간단한 형태 - "X만원", "X천만원", "X억원"
    pattern_simple = r"(\d{1,3}(?:,\d{3})*)\s*(만\s*원|천만\s*원|억\s*원)"
    for match in re.finditer(pattern_simple, text):
        pos = match.start()
        matched_text = match.group(0).strip()

        # 이미 찾은 것과 중복 체크
        if any(abs(pos - p) < 5 for p, _, _, _ in results):
            continue

        try:
            num_part = match.group(1).replace(",", "")
            unit_part = match.group(2).replace(" ", "")
            num = int(num_part)

            if "억" in unit_part:
                value = num * 100_000_000
                unit = "억원"
            elif "천만" in unit_part:
                value = num * 10_000_000
                unit = "천만원"
            elif "만" in unit_part:
                value = num * 10_000
                unit = "만원"
            else:
                value = num
                unit = "원"

            results.append((pos, matched_text, unit, value))
        except (ValueError, TypeError):
            continue

    # 패턴 3: "X억 Y천만원" 복합 형태
    pattern_complex = r"(\d+)\s*억\s*(\d+)?\s*(천만|천)?\s*만?\s*원"
    for match in re.finditer(pattern_complex, text):
        pos = match.start()
        matched_text = match.group(0).strip()

        # 이미 찾은 것과 중복 체크
        if any(abs(pos - p) < 5 for p, _, _, _ in results):
            continue

        try:
            eok = int(match.group(1)) * 100_000_000
            rest = 0
            if match.group(2):
                rest_num = int(match.group(2))
                if match.group(3) == "천만":
                    rest = rest_num * 10_000_000
                elif match.group(3) == "천":
                    rest = rest_num * 10_000_000  # 억 다음 천은 천만원
                else:
                    rest = rest_num * 10_000  # 만원

            value = eok + rest
            unit = "억원"
            results.append((pos, matched_text, unit, value))
        except (ValueError, TypeError):
            continue

    return results


def _calculate_amount_value(text: str) -> int | None:
    """금액 텍스트에서 원화 값 계산"""
    # 콤마, 공백 정규화
    normalized = text.replace(",", "").replace(" ", "")

    # 억원
    if "억" in normalized:
        match = re.match(r"(\d+)억(\d+)?(천만|천|만)?원?", normalized)
        if match:
            eok = int(match.group(1)) * 100_000_000
            rest = 0
            if match.group(2):
                rest_num = int(match.group(2))
                unit = match.group(3)
                if unit == "천만":
                    rest = rest_num * 10_000_000
                elif unit == "천":
                    rest = rest_num * 10_000_000
                elif unit == "만":
                    rest = rest_num * 10_000
                else:
                    rest = rest_num * 10_000  # 기본 만원
            return eok + rest

    # 천만원
    if "천만" in normalized:
        match = re.match(r"(\d+)천만원?", normalized)
        if match:
            return int(match.group(1)) * 10_000_000

    # 만원
    if "만" in normalized:
        match = re.match(r"(\d+)만원?", normalized)
        if match:
            return int(match.group(1)) * 10_000

    # 순수 숫자 + 원
    match = re.match(r"(\d+)원?", normalized)
    if match:
        return int(match.group(1))

    return None


def _extract_unit(text: str) -> str | None:
    """텍스트에서 단위 추출"""
    normalized = text.replace(" ", "")
    if "억원" in normalized or "억" in normalized:
        return "억원"
    if "천만원" in normalized:
        return "천만원"
    if "만원" in normalized:
        return "만원"
    if "원" in normalized:
        return "원"
    return None


def _has_keyword_nearby(text: str, position: int, window: int = 30) -> bool:
    """
    금액 위치 주변(±window 자)에 금액 관련 키워드가 있는지 확인
    """
    start = max(0, position - window)
    end = min(len(text), position + window)
    context = text[start:end]

    for keyword in AMOUNT_KEYWORDS:
        if keyword in context:
            return True
    return False


def _has_positive_keyword_nearby(text: str, position: int, window: int = 40) -> bool:
    """
    금액 위치 주변(±window 자)에 POSITIVE 키워드(보험금 관련)가 있는지 확인
    """
    start = max(0, position - window)
    end = min(len(text), position + window)
    context = text[start:end]

    for keyword in POSITIVE_KEYWORDS:
        if keyword in context:
            return True
    return False


def _has_negative_keyword_nearby(text: str, position: int, window: int = 40) -> bool:
    """
    금액 위치 주변(±window 자)에 NEGATIVE 키워드(보험료 관련)가 있는지 확인
    """
    start = max(0, position - window)
    end = min(len(text), position + window)
    context = text[start:end]

    for keyword in NEGATIVE_KEYWORDS:
        if keyword in context:
            return True
    return False


def _get_line_context(text: str, position: int) -> str:
    """
    금액이 위치한 라인 전체를 반환 (표 컬럼 구분용)
    """
    # 이전 줄바꿈 찾기
    line_start = text.rfind("\n", 0, position)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1  # 줄바꿈 다음부터

    # 다음 줄바꿈 찾기
    line_end = text.find("\n", position)
    if line_end == -1:
        line_end = len(text)

    return text[line_start:line_end]


def _is_premium_line(text: str, position: int) -> bool:
    """
    금액이 보험료 컬럼 라인에 있는지 확인
    '보험료(원)' 등이 같은 라인에 있으면 보험료 금액으로 판단
    """
    line = _get_line_context(text, position)

    # 라인에 보험료 컬럼 헤더가 있으면 보험료 금액
    if "보험료(원)" in line or "보험료 (원)" in line:
        return True

    return False


def _get_line_index(text: str, position: int) -> int:
    """
    position이 몇 번째 라인에 있는지 반환 (0-based)
    """
    return text[:position].count("\n")


def _find_premium_block_lines(lines: list[str]) -> set[int]:
    """
    Premium header 토큰이 포함된 라인 기준으로 premium block (i-1 ~ i+3) 인덱스 반환

    Returns:
        set of line indices that are in premium blocks
    """
    premium_lines = set()

    for i, line in enumerate(lines):
        # 라인에 premium header token이 있는지 확인
        has_premium_header = False
        for token in PREMIUM_HEADER_TOKENS:
            if token in line:
                has_premium_header = True
                break

        if has_premium_header:
            # window: i-1 ~ i+3
            for offset in range(-1, 4):  # -1, 0, 1, 2, 3
                idx = i + offset
                if 0 <= idx < len(lines):
                    premium_lines.add(idx)

    return premium_lines


def _find_coverage_block_lines(lines: list[str]) -> set[int]:
    """
    Coverage header 토큰이 포함된 라인 기준으로 coverage block (i ~ i+5) 인덱스 반환

    Returns:
        set of line indices that are in coverage blocks
    """
    coverage_lines = set()

    for i, line in enumerate(lines):
        # 라인에 coverage header token이 있는지 확인
        has_coverage_header = False
        for token in COVERAGE_HEADER_TOKENS:
            if token in line:
                has_coverage_header = True
                break

        if has_coverage_header:
            # window: i ~ i+5 (헤더 라인 포함 아래로 더 넓게)
            for offset in range(0, 6):  # 0, 1, 2, 3, 4, 5
                idx = i + offset
                if 0 <= idx < len(lines):
                    coverage_lines.add(idx)

    return coverage_lines


def _is_in_premium_block(text: str, position: int, premium_lines: set[int]) -> bool:
    """
    position이 premium block 내에 있는지 확인
    """
    line_idx = _get_line_index(text, position)
    return line_idx in premium_lines


def _is_in_coverage_block(text: str, position: int, coverage_lines: set[int]) -> bool:
    """
    position이 coverage block 내에 있는지 확인
    """
    line_idx = _get_line_index(text, position)
    return line_idx in coverage_lines


def extract_amount(text: str, doc_type: str | None = None) -> AmountExtract:
    """
    한국어 보험 문서에서 금액/한도 관련 표현을 1차 rule-based로 추출

    Args:
        text: 추출 대상 텍스트
        doc_type: 문서 유형 (가입설계서일 경우 더 엄격한 필터링 적용)

    Returns:
        AmountExtract 결과
    """
    if not text or len(text.strip()) == 0:
        return AmountExtract(
            amount_value=None,
            amount_text=None,
            currency="KRW",
            unit=None,
            confidence="low",
            method="regex",
            matched_span=None,
        )

    # 모든 금액 표현 찾기
    amounts = _find_amounts_with_positions(text)

    if not amounts:
        return AmountExtract(
            amount_value=None,
            amount_text=None,
            currency="KRW",
            unit=None,
            confidence="low",
            method="regex",
            matched_span=None,
        )

    # 가입설계서: 더 엄격한 필터링 (보험료 오탐 방지)
    if doc_type == "가입설계서":
        return _extract_amount_strict(text, amounts)

    # 기타 doc_type: 기존 로직 유지
    return _extract_amount_default(text, amounts)


def _has_close_negative_keyword(text: str, position: int, window: int = 15) -> bool:
    """
    금액 위치 주변(±window 자)에 NEGATIVE 키워드가 매우 가까이 있는지 확인
    좁은 범위로 체크하여 확실한 보험료 금액만 제외
    """
    start = max(0, position - window)
    end = min(len(text), position + window)
    context = text[start:end]

    for keyword in NEGATIVE_KEYWORDS:
        if keyword in context:
            return True
    return False


def _extract_amount_strict(text: str, amounts: list) -> AmountExtract:
    """
    가입설계서용 엄격한 추출 로직 (H-1.7: premium_block 휴리스틱 추가)

    우선순위:
    1. coverage_block 내의 금액 (premium_block에 없는 것)
    2. POSITIVE 키워드 근처이면서 premium_block에 없는 금액
    3. 둘 다 없으면 None (정답성 우선)

    제외:
    - premium_block 내의 금액
    - NEGATIVE 키워드가 매우 가까운 금액
    - 보험료 라인의 금액
    """
    # 라인 단위 분할 및 block 감지
    lines = text.split("\n")

    # 단일 라인이면 block 휴리스틱 미적용 (인라인 텍스트)
    # 최소 3줄 이상일 때만 표 구조로 간주
    is_table_structure = len(lines) >= 3

    if is_table_structure:
        premium_lines = _find_premium_block_lines(lines)
        coverage_lines = _find_coverage_block_lines(lines)
    else:
        # 단일/짧은 텍스트: block 감지 안함
        premium_lines = set()
        coverage_lines = set()

    # Step 1: coverage_block 내 금액 중 premium_block에 없는 것 우선
    if is_table_structure:
        coverage_block_amounts = [
            (pos, matched, unit, value)
            for pos, matched, unit, value in amounts
            if _is_in_coverage_block(text, pos, coverage_lines)
            and not _is_in_premium_block(text, pos, premium_lines)
            and not _has_close_negative_keyword(text, pos)
            and not _is_premium_line(text, pos)
        ]

        if coverage_block_amounts:
            pos, matched_text, unit, value = coverage_block_amounts[0]
            confidence = "high" if unit else "medium"
            return AmountExtract(
                amount_value=value,
                amount_text=matched_text,
                currency="KRW",
                unit=unit,
                confidence=confidence,
                method="regex",
                matched_span=matched_text,
            )

    # Step 2: POSITIVE 키워드 근처이면서 premium_block에 없는 금액
    positive_amounts = [
        (pos, matched, unit, value)
        for pos, matched, unit, value in amounts
        if _has_positive_keyword_nearby(text, pos)
        and not _is_in_premium_block(text, pos, premium_lines)
        and not _has_close_negative_keyword(text, pos)
        and not _is_premium_line(text, pos)
    ]

    if positive_amounts:
        pos, matched_text, unit, value = positive_amounts[0]
        confidence = "high" if unit else "medium"
        return AmountExtract(
            amount_value=value,
            amount_text=matched_text,
            currency="KRW",
            unit=unit,
            confidence=confidence,
            method="regex",
            matched_span=matched_text,
        )

    # Step 3: 둘 다 없으면 None 반환 (정답성 우선)
    return AmountExtract(
        amount_value=None,
        amount_text=None,
        currency="KRW",
        unit=None,
        confidence="low",
        method="regex",
        matched_span=None,
    )


def _extract_amount_default(text: str, amounts: list) -> AmountExtract:
    """
    기본 추출 로직 (상품요약서, 사업방법서 등)

    기존 동작 유지하되, NEGATIVE 키워드 근처 금액은 제외
    """
    # NEGATIVE 키워드 근처 금액 제외
    filtered_amounts = [
        (pos, matched, unit, value)
        for pos, matched, unit, value in amounts
        if not _has_negative_keyword_nearby(text, pos)
    ]

    # 필터링 후 금액이 없으면 원본에서 선택 (하위 호환)
    if not filtered_amounts:
        filtered_amounts = amounts

    # 키워드 근처 금액 우선 선택
    keyword_nearby_amounts = [
        (pos, matched, unit, value)
        for pos, matched, unit, value in filtered_amounts
        if _has_keyword_nearby(text, pos)
    ]

    if keyword_nearby_amounts:
        # 키워드 근처 중 가장 먼저 등장한 것 선택
        pos, matched_text, unit, value = keyword_nearby_amounts[0]
        confidence = "high" if unit else "medium"
    else:
        # 키워드 근처 없으면 가장 먼저 등장한 것 선택
        pos, matched_text, unit, value = filtered_amounts[0]
        confidence = "medium" if unit else "low"

    # 단위가 불명확하면 value를 None으로 (오탐 방지)
    if confidence == "low":
        value = None

    return AmountExtract(
        amount_value=value,
        amount_text=matched_text,
        currency="KRW",
        unit=unit,
        confidence=confidence,
        method="regex",
        matched_span=matched_text,
    )
