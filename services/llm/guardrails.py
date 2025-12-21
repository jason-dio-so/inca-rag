"""
STEP 5: LLM Assist Guardrails

출력 검증 및 금지어 탐지

핵심 원칙:
- 금지어 포함 시 해당 출력 제거
- 길이 제한 초과 시 truncate
- schema validation 적용
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# 금지어 패턴 (4.1 금지어 예시 기반)
# =============================================================================

FORBIDDEN_PATTERNS: list[str] = [
    # 지급 판단
    r"지급된다",
    r"지급됩니다",
    r"지급 가능",
    r"지급 불가",
    r"지급되지 않",
    r"지급받을 수 있",
    r"지급받을 수 없",
    r"보장된다",
    r"보장됩니다",
    r"보장받을 수 있",
    r"보장받을 수 없",
    r"보상받을 수 있",
    r"보상받을 수 없",
    # 유불리 판단
    r"유리하다",
    r"유리합니다",
    r"불리하다",
    r"불리합니다",
    r"더 좋",
    r"더 나",
    r"더 낫",
    r"가장 좋",
    r"가장 낫",
    r"최고",
    r"최선",
    r"최악",
    # 결론/추천
    r"결론적으로",
    r"따라서",
    r"그러므로",
    r"추천",
    r"권장",
    r"선택하",
    r"선택해야",
    r"가입해야",
    r"가입하",
    # coverage_code 확정 표현
    r"담보 코드는",
    r"coverage_code",
    r"A\d{4}_\d",  # coverage code 패턴 (A4200_1 등)
    # 금액 비교
    r"더 많이",
    r"더 적게",
    r"가 더 크",
    r"가 더 작",
]


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool = True
    removed_items: list[str] = field(default_factory=list)
    truncated: bool = False
    violations: list[str] = field(default_factory=list)


def _compile_patterns() -> list[re.Pattern]:
    """금지어 패턴 컴파일"""
    return [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]


_COMPILED_PATTERNS = _compile_patterns()


def check_forbidden_patterns(text: str) -> list[str]:
    """
    텍스트에서 금지어 패턴 검사

    Returns:
        발견된 금지어 패턴 리스트
    """
    violations = []
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            violations.append(pattern.pattern)
    return violations


def sanitize_text(text: str, max_length: int | None = None) -> tuple[str, ValidationResult]:
    """
    텍스트 정제

    - 금지어 포함 시 해당 문장 제거
    - 길이 제한 적용

    Args:
        text: 원본 텍스트
        max_length: 최대 길이 (None이면 제한 없음)

    Returns:
        (정제된 텍스트, 검증 결과)
    """
    result = ValidationResult()

    # 금지어 검사
    violations = check_forbidden_patterns(text)
    if violations:
        result.violations = violations
        result.is_valid = False
        logger.warning(f"Forbidden patterns detected: {violations}")
        # 금지어 포함 시 빈 문자열 반환
        return "", result

    # 길이 제한 적용
    if max_length and len(text) > max_length:
        result.truncated = True
        text = text[:max_length]
        logger.info(f"Text truncated to {max_length} chars")

    return text, result


def validate_query_assist_output(
    normalized_query: str,
    detected_intents: list[str],
    detected_subtypes: list[str],
    keywords: list[str],
) -> tuple[dict, ValidationResult]:
    """
    Query Assist 출력 검증

    검증 항목:
    - normalized_query ≤ 120자
    - 금지어 미포함

    Returns:
        (검증된 출력 dict, 검증 결과)
    """
    result = ValidationResult()

    # normalized_query 검증
    sanitized_query, query_result = sanitize_text(normalized_query, max_length=120)
    if not query_result.is_valid:
        result.is_valid = False
        result.violations.extend(query_result.violations)

    if query_result.truncated:
        result.truncated = True

    # keywords 검증 (각 키워드에서 금지어 확인)
    valid_keywords = []
    for kw in keywords:
        violations = check_forbidden_patterns(kw)
        if not violations:
            valid_keywords.append(kw)
        else:
            result.removed_items.append(kw)

    # confidence 계산 (검증 통과 여부 기반)
    confidence = 1.0 if result.is_valid else 0.0

    return {
        "normalized_query": sanitized_query if result.is_valid else "",
        "detected_intents": detected_intents,
        "detected_subtypes": detected_subtypes,
        "keywords": valid_keywords,
        "confidence": confidence,
    }, result


def validate_evidence_summary_output(
    summary_bullets: list[str],
) -> tuple[list[str], list[str], ValidationResult]:
    """
    Evidence Summary 출력 검증

    검증 항목:
    - bullet 1개 ≤ 160자
    - 금지어 미포함
    - bullet 3~6개 (부족 시 그대로, 초과 시 truncate)

    Returns:
        (검증된 bullets, limitations, 검증 결과)
    """
    result = ValidationResult()
    valid_bullets = []
    limitations = []

    for bullet in summary_bullets:
        # 금지어 검사
        violations = check_forbidden_patterns(bullet)
        if violations:
            result.removed_items.append(bullet)
            result.violations.extend(violations)
            limitations.append(f"일부 내용이 판단 표현 포함으로 제거됨: {', '.join(violations)}")
            continue

        # 길이 제한 (160자)
        if len(bullet) > 160:
            bullet = bullet[:157] + "..."
            result.truncated = True

        valid_bullets.append(bullet)

    # bullet 개수 제한 (최대 6개)
    if len(valid_bullets) > 6:
        valid_bullets = valid_bullets[:6]

    # 최소 1개는 있어야 함
    if not valid_bullets:
        result.is_valid = False

    # 기본 limitation 추가
    if "본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음." not in limitations:
        limitations.append("본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음.")

    return valid_bullets, limitations, result


def validate_assist_output(
    output_type: str,
    data: dict,
) -> tuple[dict, ValidationResult]:
    """
    통합 출력 검증 함수

    Args:
        output_type: "query_assist" 또는 "evidence_summary"
        data: 검증할 데이터

    Returns:
        (검증된 데이터, 검증 결과)
    """
    if output_type == "query_assist":
        validated, result = validate_query_assist_output(
            normalized_query=data.get("normalized_query", ""),
            detected_intents=data.get("detected_intents", []),
            detected_subtypes=data.get("detected_subtypes", []),
            keywords=data.get("keywords", []),
        )
        validated["notes"] = "판단/결론 금지. 정규화 힌트만 제공."
        return validated, result

    elif output_type == "evidence_summary":
        bullets, limitations, result = validate_evidence_summary_output(
            summary_bullets=data.get("summary_bullets", []),
        )
        return {
            "summary_bullets": bullets,
            "limitations": limitations,
        }, result

    else:
        return data, ValidationResult(is_valid=False, violations=["unknown output_type"])
