"""
Step H-2: LLM 프롬프트 템플릿

System/User 프롬프트 정의
"""

from __future__ import annotations

from .llm_schemas import LLM_SCHEMA_SUMMARY


# System prompt (짧고 강하게)
SYSTEM_PROMPT = """You extract insurance benefit amounts and payment-condition snippets from Korean insurance text.
Return ONLY valid JSON that matches the provided schema.
Do NOT guess. If you are not sure, set fields to null and confidence to "low".
All spans must be copied verbatim from the input text (no paraphrasing).
Classify the amount as benefit_amount vs premium_amount vs unknown."""


# User prompt template
USER_PROMPT_TEMPLATE = """Schema: {schema}

Context:
- insurer_code: {insurer_code}
- coverage_code: {coverage_code}
- doc_type: 가입설계서
- document_id: {document_id}
- page_start: {page_start}
- chunk_id: {chunk_id}

Task:
1) Find the most likely "보험금/가입금액/보장금액" for this coverage from the text.
2) If the amount is actually "보험료/월납/납입보험료", label it as premium_amount.
3) Extract ONE condition sentence if present (진단확정/최초1회/면책/감액/경계성/유사암/제자리암 etc).
4) Provide evidence spans copied verbatim from the text. If missing, set span to null.

Text:
<<<
{chunk_text}
>>>"""


def build_user_prompt(
    insurer_code: str,
    coverage_code: str,
    document_id: int,
    page_start: int | None,
    chunk_id: int,
    chunk_text: str,
) -> str:
    """
    User 프롬프트 생성

    Args:
        insurer_code: 보험사 코드
        coverage_code: 담보 코드
        document_id: 문서 ID
        page_start: 페이지 번호 (None이면 "unknown")
        chunk_id: Chunk ID
        chunk_text: Chunk 텍스트

    Returns:
        완성된 user prompt
    """
    return USER_PROMPT_TEMPLATE.format(
        schema=LLM_SCHEMA_SUMMARY,
        insurer_code=insurer_code,
        coverage_code=coverage_code,
        document_id=document_id,
        page_start=page_start if page_start is not None else "unknown",
        chunk_id=chunk_id,
        chunk_text=chunk_text,
    )


# 금액 의도 키워드 (query에 포함 시 LLM 호출 허용)
AMOUNT_INTENT_KEYWORDS = [
    "얼마",
    "한도",
    "금액",
    "지급",
    "보험금",
    "가입금액",
    "보장금액",
    "만원",
    "억원",
]


def has_amount_intent(query: str) -> bool:
    """
    query가 금액 의도를 포함하는지 확인

    Args:
        query: 검색 쿼리

    Returns:
        금액 의도 포함 여부
    """
    if not query:
        return False

    for keyword in AMOUNT_INTENT_KEYWORDS:
        if keyword in query:
            return True

    return False
