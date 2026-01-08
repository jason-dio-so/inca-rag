"""
STEP 5: Evidence Summary

Evidence(약관/사업방법서 발췌)를 비판단 요약 형태로 정리

핵심 원칙:
- 판단 없는 요약만 허용
- 결론/추천/지급 판단 절대 금지
- 원문 evidence와 함께 노출
"""

from __future__ import annotations

import logging
import re

from .schemas import (
    EvidenceSummaryRequest,
    EvidenceSummaryResponse,
    EvidenceItem,
    AssistStatus,
)
from .guardrails import validate_assist_output
from .client import get_assist_llm_client, is_assist_llm_enabled

logger = logging.getLogger(__name__)


# =============================================================================
# Rule-based Fallback
# =============================================================================

def _summarize_excerpt_rule_based(excerpt: str, doc_type: str) -> str:
    """규칙 기반 단일 excerpt 요약"""
    # 첫 문장 또는 핵심 부분 추출
    # 160자 제한 준수

    # 마침표로 문장 분리
    sentences = re.split(r'[.。]', excerpt)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return f"{doc_type}에 관련 내용이 있음."

    # 첫 문장 사용
    first_sentence = sentences[0]

    # 길이 제한
    if len(first_sentence) > 150:
        first_sentence = first_sentence[:147] + "..."

    return first_sentence + "."


def _evidence_summary_rule_based(
    request: EvidenceSummaryRequest,
) -> EvidenceSummaryResponse:
    """규칙 기반 Evidence Summary"""
    bullets = []

    for evidence in request.evidence[:6]:  # 최대 6개
        summary = _summarize_excerpt_rule_based(
            evidence.excerpt,
            evidence.doc_type,
        )
        bullets.append(f"[{evidence.insurer_code}] {summary}")

    # 검증
    validated, result = validate_assist_output("evidence_summary", {"summary_bullets": bullets})

    return EvidenceSummaryResponse(
        summary_bullets=validated.get("summary_bullets", bullets),
        limitations=validated.get("limitations", [
            "본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음."
        ]),
        assist_status=AssistStatus(status="SUCCESS"),
    )


# =============================================================================
# LLM-based Evidence Summary
# =============================================================================

EVIDENCE_SUMMARY_SYSTEM_PROMPT = """당신은 보험 약관 문서 요약 보조자입니다.

주어진 약관/사업방법서 발췌를 분석하여 비판단적 요약을 제공합니다.

규칙:
1. summary_bullets: 3~6개의 요약 bullet 제공
   - 각 bullet은 160자 이내
   - 사실만 기술, 판단/결론 금지

2. 절대 금지 표현:
   - "지급된다", "지급됩니다", "보장된다"
   - "유리하다", "불리하다", "더 좋다"
   - "결론적으로", "따라서", "추천"
   - 금액 비교 ("더 많이", "더 적게")

3. 허용되는 표현:
   - "~로 정의됨", "~에 해당함"
   - "약관에 따르면", "조항에 의하면"
   - "~의 경우 ~로 규정됨"

JSON 응답 형식:
{
  "summary_bullets": [
    "제자리암은 약관 정의상 특정 조건에서 보장 대상에 포함됨.",
    "경계성 종양은 별도 정의 조항에서 보장 범위가 규정됨."
  ]
}"""


async def _evidence_summary_llm(
    request: EvidenceSummaryRequest,
) -> EvidenceSummaryResponse:
    """LLM 기반 Evidence Summary"""
    client = get_assist_llm_client()

    # Evidence 항목들을 프롬프트로 구성
    evidence_texts = []
    for i, ev in enumerate(request.evidence[:6], 1):
        evidence_texts.append(
            f"[{i}] 보험사: {ev.insurer_code}\n"
            f"    문서: {ev.doc_type} (p.{ev.page or '?'})\n"
            f"    내용: {ev.excerpt[:500]}"  # 길이 제한
        )

    user_prompt = f"""다음 약관/사업방법서 발췌를 비판단적으로 요약해주세요.

{chr(10).join(evidence_texts)}

주의:
- 지급 여부, 유불리 판단 절대 금지
- 사실 기술만 허용
- 3~6개 bullet으로 요약"""

    # LLM 호출
    response = await client.call(
        system_prompt=EVIDENCE_SUMMARY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        endpoint="evidence_summary",
    )

    if not response.success or not response.data:
        logger.info("LLM failed, using rule-based fallback")
        return _evidence_summary_rule_based(request)

    # 응답 검증
    validated, result = validate_assist_output("evidence_summary", response.data)

    if not result.is_valid or not validated.get("summary_bullets"):
        logger.warning(f"LLM output validation failed: {result.violations}")
        return _evidence_summary_rule_based(request)

    return EvidenceSummaryResponse(
        summary_bullets=validated["summary_bullets"],
        limitations=validated.get("limitations", [
            "본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음."
        ]),
        assist_status=AssistStatus(status="SUCCESS"),
    )


# =============================================================================
# Public API
# =============================================================================

async def evidence_summary(
    request: EvidenceSummaryRequest,
) -> EvidenceSummaryResponse:
    """
    Evidence Summary 메인 함수

    LLM 활성화 시 LLM 사용, 비활성화 시 규칙 기반

    Args:
        request: EvidenceSummaryRequest

    Returns:
        EvidenceSummaryResponse (항상 성공, soft-fail)
    """
    try:
        # Evidence가 없으면 빈 결과
        if not request.evidence:
            return EvidenceSummaryResponse(
                summary_bullets=["제공된 근거가 없습니다."],
                limitations=[
                    "본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음."
                ],
                assist_status=AssistStatus(status="SUCCESS"),
            )

        if is_assist_llm_enabled():
            return await _evidence_summary_llm(request)
        else:
            return _evidence_summary_rule_based(request)

    except Exception as e:
        logger.error(f"Evidence summary error: {e}")
        # 예외 발생해도 soft-fail
        return EvidenceSummaryResponse(
            summary_bullets=["요약 처리 중 오류가 발생했습니다."],
            limitations=[
                "본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음.",
                f"처리 오류: 상세 정보는 원문을 참조하세요.",
            ],
            assist_status=AssistStatus(
                status="FAILED",
                error_code="INTERNAL_ERROR",
                error_message=str(e)[:100],
            ),
        )
