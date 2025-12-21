"""
STEP 5: LLM Assist Schemas

Pydantic 스키마 정의
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class AssistStatus(BaseModel):
    """Assist 결과 상태"""
    status: Literal["SUCCESS", "FAILED"] = "SUCCESS"
    error_code: str | None = None
    error_message: str | None = None


# =============================================================================
# Query Assist Schemas
# =============================================================================

class QueryAssistContext(BaseModel):
    """Query Assist 요청 컨텍스트"""
    has_anchor: bool = False
    locked_coverage_codes: list[str] | None = None


class QueryAssistRequest(BaseModel):
    """
    Query Assist 요청

    입력:
    - query: 사용자 원본 질의
    - insurers: 선택된 보험사 코드 리스트
    - context: 추가 컨텍스트 (anchor 존재 여부, locked 담보 등)
    """
    query: str = Field(..., description="사용자 질의", min_length=1)
    insurers: list[str] = Field(default=[], description="선택된 보험사 코드")
    context: QueryAssistContext = Field(
        default_factory=QueryAssistContext,
        description="추가 컨텍스트 정보"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "경계성 종양과 제자리암 비교",
                    "insurers": ["SAMSUNG", "MERITZ"],
                    "context": {
                        "has_anchor": False,
                        "locked_coverage_codes": None
                    }
                }
            ]
        }
    }


class QueryAssistResponse(BaseModel):
    """
    Query Assist 응답

    출력:
    - normalized_query: 정규화된 질의 (≤120자)
    - detected_intents: 감지된 의도 목록
    - detected_subtypes: 감지된 subtype 코드 목록
    - keywords: 추출된 키워드 목록
    - confidence: 검증 통과 여부 기반 신뢰도 (0.0 ~ 1.0)
    - notes: 참고 사항 (판단/결론 금지 명시)

    핵심 원칙:
    - JSON 파싱 실패 = FAIL
    - normalized_query ≤ 120자
    - confidence는 모델 점수가 아니라 검증 통과 여부 기반
    """
    normalized_query: str = Field(
        ...,
        description="정규화된 질의",
        max_length=120
    )
    detected_intents: list[str] = Field(
        default=[],
        description="감지된 의도 (compare, lookup, coverage_lookup 등)"
    )
    detected_subtypes: list[str] = Field(
        default=[],
        description="감지된 subtype 코드 (CIS_CARCINOMA, BORDERLINE_TUMOR 등)"
    )
    keywords: list[str] = Field(
        default=[],
        description="추출된 키워드"
    )
    confidence: float = Field(
        default=0.0,
        description="검증 통과 여부 기반 신뢰도 (0.0 ~ 1.0)",
        ge=0.0,
        le=1.0
    )
    notes: str = Field(
        default="판단/결론 금지. 정규화 힌트만 제공.",
        description="참고 사항"
    )
    # Assist 상태
    assist_status: AssistStatus = Field(
        default_factory=AssistStatus,
        description="Assist 처리 상태"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "normalized_query": "암진단비 (제자리암, 경계성 종양) 비교",
                    "detected_intents": ["compare", "coverage_lookup"],
                    "detected_subtypes": ["CIS_CARCINOMA", "BORDERLINE_TUMOR"],
                    "keywords": ["암진단비", "제자리암", "경계성종양"],
                    "confidence": 0.8,
                    "notes": "판단/결론 금지. 정규화 힌트만 제공.",
                    "assist_status": {"status": "SUCCESS"}
                }
            ]
        }
    }


# =============================================================================
# Evidence Summary Schemas
# =============================================================================

class EvidenceItem(BaseModel):
    """개별 Evidence 항목"""
    insurer_code: str = Field(..., description="보험사 코드")
    doc_type: str = Field(..., description="문서 유형 (약관, 사업방법서 등)")
    page: int | None = Field(None, description="페이지 번호")
    excerpt: str = Field(..., description="발췌 원문", max_length=2000)


class EvidenceSummaryRequest(BaseModel):
    """
    Evidence Summary 요청

    입력:
    - evidence: Evidence 항목 리스트
    - task: 작업 유형 (summarize_without_judgement 고정)
    """
    evidence: list[EvidenceItem] = Field(
        ...,
        description="Evidence 항목 리스트",
        min_length=1
    )
    task: Literal["summarize_without_judgement"] = Field(
        default="summarize_without_judgement",
        description="작업 유형 (판단 없는 요약만 허용)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "evidence": [
                        {
                            "insurer_code": "SAMSUNG",
                            "doc_type": "약관",
                            "page": 12,
                            "excerpt": "제자리암은 다음 각 호의 어느 하나에 해당하는 경우에 보장합니다..."
                        }
                    ],
                    "task": "summarize_without_judgement"
                }
            ]
        }
    }


class EvidenceSummaryResponse(BaseModel):
    """
    Evidence Summary 응답

    출력:
    - summary_bullets: 요약 bullet 목록 (3~6개, 각 ≤160자)
    - limitations: 제한 사항 목록 (비판단 요약임을 명시)

    핵심 원칙:
    - bullet 3~6개
    - bullet 1개 ≤ 160자
    - 금지어 탐지 시 해당 bullet 제거 + limitations 기록
    """
    summary_bullets: list[str] = Field(
        ...,
        description="요약 bullet 목록 (3~6개, 각 ≤160자)",
        min_length=1,
        max_length=6
    )
    limitations: list[str] = Field(
        default=[],
        description="제한 사항 (비판단 요약 명시)"
    )
    # Assist 상태
    assist_status: AssistStatus = Field(
        default_factory=AssistStatus,
        description="Assist 처리 상태"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary_bullets": [
                        "제자리암은 약관 정의상 특정 조건에서 보장 대상에 포함됨.",
                        "경계성 종양은 별도 정의 조항에서 보장 범위가 제한됨."
                    ],
                    "limitations": [
                        "본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음."
                    ],
                    "assist_status": {"status": "SUCCESS"}
                }
            ]
        }
    }
