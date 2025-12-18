"""
Compare API Router

POST /compare - 2-Phase Retrieval 비교 검색
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.retrieval.compare_service import compare, CompareResponse

router = APIRouter(tags=["compare"])


class CompareRequest(BaseModel):
    """비교 검색 요청"""
    insurers: list[str] = Field(..., description="비교할 보험사 코드 리스트", min_length=1)
    query: str = Field(..., description="사용자 질의", min_length=1)
    coverage_codes: list[str] | None = Field(None, description="필터할 coverage_code 리스트")
    top_k_per_insurer: int = Field(10, description="보험사별 최대 결과 수", ge=1, le=100)
    compare_doc_types: list[str] = Field(
        default=["가입설계서", "상품요약서", "사업방법서"],
        description="Compare Axis 대상 doc_type",
    )
    policy_doc_types: list[str] = Field(
        default=["약관"],
        description="Policy Axis 대상 doc_type",
    )
    policy_keywords: list[str] = Field(
        default=[],
        description="약관 검색 키워드",
    )
    # Step I: Plan 자동 선택
    age: int | None = Field(None, description="피보험자 나이 (plan 자동 선택용)", ge=0, le=150)
    gender: Literal["M", "F"] | None = Field(None, description="피보험자 성별 (M/F)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "insurers": ["SAMSUNG", "MERITZ"],
                    "query": "경계성 종양 암진단비",
                    "coverage_codes": ["A4200_1", "A4210"],
                    "top_k_per_insurer": 10,
                    "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
                    "policy_doc_types": ["약관"],
                    "policy_keywords": ["경계성", "유사암", "제자리암"],
                    "age": 35,
                    "gender": "M",
                }
            ]
        }
    }


class AmountInfoResponse(BaseModel):
    """금액 정보"""
    amount_value: int | None
    amount_text: str | None
    unit: str | None
    confidence: str
    method: str


class ConditionInfoResponse(BaseModel):
    """지급조건 정보"""
    snippet: str | None
    matched_terms: list[str]


class EvidenceResponse(BaseModel):
    """검색 결과 근거"""
    document_id: int
    doc_type: str
    page_start: int | None
    preview: str
    score: float
    amount: AmountInfoResponse | None = None
    condition_snippet: ConditionInfoResponse | None = None


class CompareAxisItemResponse(BaseModel):
    """Compare Axis 결과 항목"""
    insurer_code: str
    coverage_code: str
    coverage_name: str | None
    doc_type_counts: dict[str, int]
    evidence: list[EvidenceResponse]


class PolicyAxisItemResponse(BaseModel):
    """Policy Axis 결과 항목"""
    insurer_code: str
    keyword: str
    evidence: list[EvidenceResponse]


class InsurerCompareCellResponse(BaseModel):
    """비교표 셀: 보험사별 결과"""
    insurer_code: str
    doc_type_counts: dict[str, int]
    best_evidence: list[EvidenceResponse]


class CoverageCompareRowResponse(BaseModel):
    """비교표 행: coverage_code 기준"""
    coverage_code: str
    coverage_name: str | None
    insurers: list[InsurerCompareCellResponse]


class EvidenceRefResponse(BaseModel):
    """근거 참조"""
    insurer_code: str
    document_id: int
    page_start: int | None


class DiffBulletResponse(BaseModel):
    """차이점 문장"""
    text: str
    evidence_refs: list[EvidenceRefResponse]


class DiffSummaryItemResponse(BaseModel):
    """coverage_code별 차이점 요약"""
    coverage_code: str
    coverage_name: str | None
    bullets: list[DiffBulletResponse]


# =============================================================================
# U-4.8: Comparison Slots
# =============================================================================

class SlotEvidenceRefResponse(BaseModel):
    """슬롯 근거 참조"""
    document_id: int
    page_start: int | None
    chunk_id: int | None = None


class LLMTraceResponse(BaseModel):
    """LLM 사용 추적 정보"""
    method: Literal["rule", "llm", "hybrid"]
    llm_used: bool
    llm_reason: Literal["flag_off", "ambiguity_high", "parse_fail", "cost_guard", "not_needed"] | None = None
    model: str | None = None


class SlotInsurerValueResponse(BaseModel):
    """슬롯 보험사별 값"""
    insurer_code: str
    value: str | None
    confidence: Literal["high", "medium", "low", "not_found"] = "medium"
    reason: str | None = None  # not_found일 때 이유
    evidence_refs: list[SlotEvidenceRefResponse] = []
    trace: LLMTraceResponse | None = None  # LLM usage trace


class ComparisonSlotResponse(BaseModel):
    """비교 슬롯 항목"""
    slot_key: str
    label: str
    comparable: bool
    insurers: list[SlotInsurerValueResponse]
    diff_summary: str | None = None  # 슬롯별 차이 요약


class CompareResponseModel(BaseModel):
    """비교 검색 응답"""
    compare_axis: list[CompareAxisItemResponse]
    policy_axis: list[PolicyAxisItemResponse]
    coverage_compare_result: list[CoverageCompareRowResponse]
    diff_summary: list[DiffSummaryItemResponse]
    # U-4.8: Comparison Slots
    slots: list[ComparisonSlotResponse] = []
    debug: dict[str, Any]


def _convert_evidence(e) -> EvidenceResponse:
    """Evidence를 EvidenceResponse로 변환 (amount/condition_snippet 포함)"""
    amount_resp = None
    if e.amount is not None:
        amount_resp = AmountInfoResponse(
            amount_value=e.amount.amount_value,
            amount_text=e.amount.amount_text,
            unit=e.amount.unit,
            confidence=e.amount.confidence,
            method=e.amount.method,
        )

    condition_resp = None
    if e.condition_snippet is not None:
        condition_resp = ConditionInfoResponse(
            snippet=e.condition_snippet.snippet,
            matched_terms=e.condition_snippet.matched_terms,
        )

    return EvidenceResponse(
        document_id=e.document_id,
        doc_type=e.doc_type,
        page_start=e.page_start,
        preview=e.preview,
        score=e.score,
        amount=amount_resp,
        condition_snippet=condition_resp,
    )


def _convert_slots(slots: list) -> list[ComparisonSlotResponse]:
    """슬롯 결과를 API 응답 모델로 변환"""
    return [
        ComparisonSlotResponse(
            slot_key=slot.slot_key,
            label=slot.label,
            comparable=slot.comparable,
            insurers=[
                SlotInsurerValueResponse(
                    insurer_code=iv.insurer_code,
                    value=iv.value,
                    confidence=iv.confidence,
                    reason=iv.reason,
                    evidence_refs=[
                        SlotEvidenceRefResponse(
                            document_id=ref.document_id,
                            page_start=ref.page_start,
                            chunk_id=getattr(ref, 'chunk_id', None),
                        )
                        for ref in iv.evidence_refs
                    ],
                    trace=LLMTraceResponse(
                        method=iv.trace.method,
                        llm_used=iv.trace.llm_used,
                        llm_reason=iv.trace.llm_reason,
                        model=iv.trace.model,
                    ) if iv.trace else None,
                )
                for iv in slot.insurers
            ],
            diff_summary=slot.diff_summary,
        )
        for slot in slots
    ]


def _convert_response(result: CompareResponse) -> CompareResponseModel:
    """내부 결과를 API 응답 모델로 변환"""
    return CompareResponseModel(
        compare_axis=[
            CompareAxisItemResponse(
                insurer_code=item.insurer_code,
                coverage_code=item.coverage_code,
                coverage_name=item.coverage_name,
                doc_type_counts=item.doc_type_counts,
                evidence=[_convert_evidence(e) for e in item.evidence],
            )
            for item in result.compare_axis
        ],
        policy_axis=[
            PolicyAxisItemResponse(
                insurer_code=item.insurer_code,
                keyword=item.keyword,
                evidence=[_convert_evidence(e) for e in item.evidence],
            )
            for item in result.policy_axis
        ],
        coverage_compare_result=[
            CoverageCompareRowResponse(
                coverage_code=row.coverage_code,
                coverage_name=row.coverage_name,
                insurers=[
                    InsurerCompareCellResponse(
                        insurer_code=cell.insurer_code,
                        doc_type_counts=cell.doc_type_counts,
                        best_evidence=[_convert_evidence(e) for e in cell.best_evidence],
                    )
                    for cell in row.insurers
                ],
            )
            for row in result.coverage_compare_result
        ],
        diff_summary=[
            DiffSummaryItemResponse(
                coverage_code=item.coverage_code,
                coverage_name=item.coverage_name,
                bullets=[
                    DiffBulletResponse(
                        text=bullet.text,
                        evidence_refs=[
                            EvidenceRefResponse(
                                insurer_code=ref.insurer_code,
                                document_id=ref.document_id,
                                page_start=ref.page_start,
                            )
                            for ref in bullet.evidence_refs
                        ],
                    )
                    for bullet in item.bullets
                ],
            )
            for item in result.diff_summary
        ],
        # U-4.8: Comparison Slots
        slots=_convert_slots(getattr(result, 'slots', [])),
        debug=result.debug,
    )


@router.post("/compare", response_model=CompareResponseModel)
async def compare_insurers(request: CompareRequest) -> CompareResponseModel:
    """
    2-Phase Retrieval 비교 검색

    - **compare_axis**: 가입설계서/상품요약서/사업방법서에서 coverage_code 기반 근거 수집
    - **policy_axis**: 약관에서 키워드 기반 조문 근거 수집 (A2 정책)
    """
    try:
        result = compare(
            insurers=request.insurers,
            query=request.query,
            coverage_codes=request.coverage_codes,
            top_k_per_insurer=request.top_k_per_insurer,
            compare_doc_types=request.compare_doc_types,
            policy_doc_types=request.policy_doc_types,
            policy_keywords=request.policy_keywords,
            age=request.age,
            gender=request.gender,
        )
        return _convert_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
