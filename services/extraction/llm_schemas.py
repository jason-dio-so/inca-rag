"""
Step H-2: LLM 정밀 추출용 스키마

LLM 출력 JSON 구조를 Pydantic으로 정의
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LLMSpan(BaseModel):
    """근거 원문 span"""
    text: str = Field(..., max_length=120, description="근거 원문 (최대 120자)")
    start: int | None = Field(None, description="content 내 offset (시작)")
    end: int | None = Field(None, description="content 내 offset (끝)")


class LLMAmount(BaseModel):
    """금액 추출 결과"""
    label: Literal["benefit_amount", "premium_amount", "unknown"] = Field(
        ..., description="금액 종류: 보험금/보험료/불명"
    )
    amount_value: int | None = Field(None, description="KRW 정수값")
    amount_text: str | None = Field(None, description="원문 표현 (예: '1,000만원')")
    unit: str | None = Field(None, description="단위 (원/만원/억원)")
    confidence: Literal["high", "medium", "low"] = Field(
        "low", description="신뢰도"
    )
    span: LLMSpan | None = Field(None, description="근거 span")


class LLMCondition(BaseModel):
    """지급조건 추출 결과"""
    snippet: str | None = Field(None, max_length=120, description="조건 문장 (최대 120자)")
    matched_terms: list[str] = Field(default_factory=list, description="매칭된 키워드")
    confidence: Literal["high", "medium", "low"] = Field("low", description="신뢰도")
    span: LLMSpan | None = Field(None, description="근거 span")


class LLMExtractResult(BaseModel):
    """LLM 추출 전체 결과"""
    coverage_code: str = Field(..., description="담보 코드")
    insurer_code: str = Field(..., description="보험사 코드")
    doc_type: Literal["가입설계서"] = Field("가입설계서", description="문서 유형")
    document_id: int = Field(..., description="문서 ID")
    page_start: int | None = Field(None, description="페이지 번호")
    chunk_id: int = Field(..., description="Chunk ID")
    amount: LLMAmount = Field(..., description="금액 추출 결과")
    condition: LLMCondition = Field(..., description="조건 추출 결과")
    notes: str | None = Field(None, description="추가 메모 (예: '표 구조로 확신 어려움')")


# JSON Schema summary for prompt (simplified)
LLM_SCHEMA_SUMMARY = """
{
  "coverage_code": "string",
  "insurer_code": "string",
  "doc_type": "가입설계서",
  "document_id": int,
  "page_start": int | null,
  "chunk_id": int,
  "amount": {
    "label": "benefit_amount" | "premium_amount" | "unknown",
    "amount_value": int | null,  // KRW
    "amount_text": string | null,  // "1,000만원"
    "unit": string | null,  // "원"/"만원"/"억원"
    "confidence": "high" | "medium" | "low",
    "span": {"text": string, "start": int|null, "end": int|null} | null
  },
  "condition": {
    "snippet": string | null,  // max 120 chars
    "matched_terms": [string],
    "confidence": "high" | "medium" | "low",
    "span": {"text": string, "start": int|null, "end": int|null} | null
  },
  "notes": string | null
}
"""
