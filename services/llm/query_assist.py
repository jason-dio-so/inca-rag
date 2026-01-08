"""
STEP 5: Query Assist

사용자 질의를 구조화/정규화하고 intent, subtype 힌트 제공

핵심 원칙:
- LLM 사용은 선택적 (fallback은 규칙 기반)
- 자동 반영 금지 (사용자 Apply 필수)
- 판단/결론 금지
"""

from __future__ import annotations

import logging
import re
from api.config_loader import (
    get_domain_keywords,
    get_compare_trigger_keywords,
    get_lookup_force_keywords,
)
from services.extraction.subtype_extractor import (
    extract_subtypes_from_query,
    is_multi_subtype_query,
)

from .schemas import (
    QueryAssistRequest,
    QueryAssistResponse,
    AssistStatus,
)
from .guardrails import validate_assist_output
from .client import get_assist_llm_client, is_assist_llm_enabled

logger = logging.getLogger(__name__)


# =============================================================================
# Rule-based Fallback
# =============================================================================

# 주요 담보 키워드
COVERAGE_KEYWORDS = [
    "암진단비",
    "암 진단비",
    "제자리암",
    "유사암",
    "경계성종양",
    "경계성 종양",
    "뇌졸중",
    "급성심근경색",
    "심근경색",
    "수술비",
    "입원비",
    "사망보험금",
    "진단금",
    "진단비",
    "실손",
    "실비",
]

# Subtype 코드 매핑
SUBTYPE_KEYWORDS = {
    "제자리암": "CIS_CARCINOMA",
    "제자리 암": "CIS_CARCINOMA",
    "경계성종양": "BORDERLINE_TUMOR",
    "경계성 종양": "BORDERLINE_TUMOR",
    "유사암": "SIMILAR_CANCER",
    "갑상선암": "THYROID_CANCER",
    "소액암": "MINOR_CANCER",
    "기타피부암": "SKIN_CANCER",
}


def _extract_keywords_rule_based(query: str) -> list[str]:
    """규칙 기반 키워드 추출"""
    found = []
    query_lower = query.lower()

    for kw in COVERAGE_KEYWORDS:
        if kw.lower() in query_lower:
            # 공백 제거된 버전
            normalized = kw.replace(" ", "")
            if normalized not in found:
                found.append(normalized)

    return found


def _extract_subtypes_rule_based(query: str) -> list[str]:
    """규칙 기반 subtype 추출"""
    found = []
    query_lower = query.lower()

    for kw, code in SUBTYPE_KEYWORDS.items():
        if kw.lower() in query_lower:
            if code not in found:
                found.append(code)

    return found


def _detect_intent_rule_based(query: str) -> list[str]:
    """규칙 기반 intent 감지"""
    intents = []
    query_lower = query.lower()

    # 비교 의도
    compare_keywords = get_compare_trigger_keywords()
    for kw in compare_keywords:
        if kw in query_lower:
            intents.append("compare")
            break

    # 조회 의도 (기본값)
    lookup_keywords = get_lookup_force_keywords()
    has_lookup = any(kw in query_lower for kw in lookup_keywords)

    # 담보 관련 키워드가 있으면 coverage_lookup
    if any(kw.lower() in query_lower for kw in COVERAGE_KEYWORDS):
        intents.append("coverage_lookup")

    # 기본 intent
    if not intents:
        intents.append("lookup")

    return intents


def _normalize_query_rule_based(query: str, keywords: list[str]) -> str:
    """규칙 기반 질의 정규화"""
    # 기본: 원본 유지
    normalized = query.strip()

    # 불필요한 공백 정리
    normalized = re.sub(r'\s+', ' ', normalized)

    # 120자 제한
    if len(normalized) > 120:
        normalized = normalized[:117] + "..."

    return normalized


def _query_assist_rule_based(request: QueryAssistRequest) -> QueryAssistResponse:
    """규칙 기반 Query Assist (LLM fallback)"""
    query = request.query

    # 키워드 추출
    keywords = _extract_keywords_rule_based(query)

    # Subtype 추출
    subtypes = _extract_subtypes_rule_based(query)

    # Intent 감지
    intents = _detect_intent_rule_based(query)

    # 정규화
    normalized = _normalize_query_rule_based(query, keywords)

    # 검증
    validated, result = validate_assist_output("query_assist", {
        "normalized_query": normalized,
        "detected_intents": intents,
        "detected_subtypes": subtypes,
        "keywords": keywords,
    })

    return QueryAssistResponse(
        normalized_query=validated.get("normalized_query", query),
        detected_intents=validated.get("detected_intents", []),
        detected_subtypes=validated.get("detected_subtypes", []),
        keywords=validated.get("keywords", []),
        confidence=0.5 if result.is_valid else 0.0,  # 규칙 기반은 0.5
        notes="판단/결론 금지. 정규화 힌트만 제공.",
        assist_status=AssistStatus(status="SUCCESS"),
    )


# =============================================================================
# LLM-based Query Assist
# =============================================================================

QUERY_ASSIST_SYSTEM_PROMPT = """당신은 보험 약관 비교 시스템의 질의 정규화 보조자입니다.

사용자 질의를 분석하여 다음 정보를 JSON으로 반환하세요:

1. normalized_query: 정규화된 질의 (120자 이내)
   - 오타 수정, 동의어 통일
   - 핵심 키워드 명확화

2. detected_intents: 감지된 의도 목록
   - "compare": 복수 보험사/담보 비교
   - "lookup": 단일 정보 조회
   - "coverage_lookup": 담보 정보 조회

3. detected_subtypes: 감지된 질병 하위유형 코드
   - CIS_CARCINOMA: 제자리암
   - BORDERLINE_TUMOR: 경계성종양
   - SIMILAR_CANCER: 유사암
   - THYROID_CANCER: 갑상선암
   - MINOR_CANCER: 소액암
   - SKIN_CANCER: 기타피부암

4. keywords: 추출된 핵심 키워드 목록

중요 규칙:
- 판단이나 결론을 내리지 마세요
- coverage_code를 확정하지 마세요
- "지급된다", "유리하다", "추천" 등의 표현 금지
- JSON 형식으로만 응답하세요

응답 예시:
{
  "normalized_query": "삼성화재 암진단비 (제자리암, 경계성종양) 비교",
  "detected_intents": ["compare", "coverage_lookup"],
  "detected_subtypes": ["CIS_CARCINOMA", "BORDERLINE_TUMOR"],
  "keywords": ["암진단비", "제자리암", "경계성종양"]
}"""


async def _query_assist_llm(request: QueryAssistRequest) -> QueryAssistResponse:
    """LLM 기반 Query Assist"""
    client = get_assist_llm_client()

    # 사용자 프롬프트 구성
    user_prompt = f"""질의: {request.query}

선택된 보험사: {', '.join(request.insurers) if request.insurers else '없음'}
기존 anchor 존재: {request.context.has_anchor}
고정된 담보: {request.context.locked_coverage_codes if request.context.locked_coverage_codes else '없음'}

위 질의를 분석해주세요."""

    # LLM 호출
    response = await client.call(
        system_prompt=QUERY_ASSIST_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        endpoint="query_assist",
    )

    if not response.success or not response.data:
        # LLM 실패 시 규칙 기반 fallback
        logger.info("LLM failed, using rule-based fallback")
        result = _query_assist_rule_based(request)
        result.assist_status = AssistStatus(
            status="SUCCESS",  # fallback은 성공으로 처리
        )
        result.notes = "LLM 미사용 (규칙 기반). 판단/결론 금지."
        return result

    # LLM 응답 검증
    validated, result = validate_assist_output("query_assist", response.data)

    if not result.is_valid:
        logger.warning(f"LLM output validation failed: {result.violations}")
        # 검증 실패 시에도 규칙 기반 fallback
        return _query_assist_rule_based(request)

    return QueryAssistResponse(
        normalized_query=validated.get("normalized_query", request.query),
        detected_intents=validated.get("detected_intents", []),
        detected_subtypes=validated.get("detected_subtypes", []),
        keywords=validated.get("keywords", []),
        confidence=validated.get("confidence", 0.8),
        notes=validated.get("notes", "판단/결론 금지. 정규화 힌트만 제공."),
        assist_status=AssistStatus(status="SUCCESS"),
    )


# =============================================================================
# Public API
# =============================================================================

async def query_assist(request: QueryAssistRequest) -> QueryAssistResponse:
    """
    Query Assist 메인 함수

    LLM 활성화 시 LLM 사용, 비활성화 시 규칙 기반

    Args:
        request: QueryAssistRequest

    Returns:
        QueryAssistResponse (항상 성공, soft-fail)
    """
    try:
        if is_assist_llm_enabled():
            return await _query_assist_llm(request)
        else:
            return _query_assist_rule_based(request)
    except Exception as e:
        logger.error(f"Query assist error: {e}")
        # 예외 발생해도 soft-fail
        return QueryAssistResponse(
            normalized_query=request.query,
            detected_intents=["lookup"],
            detected_subtypes=[],
            keywords=[],
            confidence=0.0,
            notes="처리 중 오류 발생. 판단/결론 금지.",
            assist_status=AssistStatus(
                status="FAILED",
                error_code="INTERNAL_ERROR",
                error_message=str(e)[:100],  # 에러 메시지 sanitize
            ),
        )
