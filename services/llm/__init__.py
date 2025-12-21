"""
STEP 5: LLM Assist Module

LLM을 보조(Assist) 역할로만 사용하는 모듈.

핵심 원칙:
- Query Assist: 질의 정규화/힌트 제공 (자동 반영 금지)
- Evidence Summary: 판단 없는 요약 (결론/추천 금지)
- /compare API는 LLM 없이도 100% 동일하게 동작해야 함

LLM 금지 역할:
- coverage_code 결정 또는 추천
- 지급 가능/불가능 판단
- 금액 비교, "어디가 더 유리"
- 최종 비교 결론 문장 생성
"""

from .schemas import (
    QueryAssistRequest,
    QueryAssistResponse,
    EvidenceSummaryRequest,
    EvidenceSummaryResponse,
    AssistStatus,
)
from .guardrails import validate_assist_output, FORBIDDEN_PATTERNS
from .query_assist import query_assist
from .evidence_summary import evidence_summary

__all__ = [
    # Schemas
    "QueryAssistRequest",
    "QueryAssistResponse",
    "EvidenceSummaryRequest",
    "EvidenceSummaryResponse",
    "AssistStatus",
    # Functions
    "query_assist",
    "evidence_summary",
    # Guardrails
    "validate_assist_output",
    "FORBIDDEN_PATTERNS",
]
