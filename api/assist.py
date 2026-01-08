"""
STEP 5: Assist API Router

POST /assist/query - Query Assist (질의 정규화/힌트)
POST /assist/summary - Evidence Summary (비판단 요약)

핵심 원칙:
- /compare API는 LLM 없이도 100% 동일하게 동작
- Assist API는 보조 역할만 수행
- 자동 반영 금지 (사용자 Apply 필수)
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from services.llm import (
    QueryAssistRequest,
    QueryAssistResponse,
    EvidenceSummaryRequest,
    EvidenceSummaryResponse,
    query_assist,
    evidence_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assist", tags=["assist"])


# =============================================================================
# Audit Log Helper
# =============================================================================

def _log_assist_request(
    endpoint: str,
    request_data: dict[str, Any],
    response_data: dict[str, Any],
    latency_ms: float,
) -> None:
    """
    Assist 요청 감사 로그

    debug/audit 용도로만 기록
    """
    logger.info(
        f"[ASSIST] endpoint={endpoint} "
        f"latency={latency_ms:.0f}ms "
        f"status={response_data.get('assist_status', {}).get('status', 'UNKNOWN')}"
    )


# =============================================================================
# Query Assist Endpoint
# =============================================================================

@router.post("/query", response_model=QueryAssistResponse)
async def assist_query(request: QueryAssistRequest) -> QueryAssistResponse:
    """
    Query Assist - 질의 정규화 및 힌트 제공

    입력:
    - query: 사용자 질의
    - insurers: 선택된 보험사 코드 리스트
    - context: 추가 컨텍스트 (anchor 존재 여부, locked 담보 등)

    출력:
    - normalized_query: 정규화된 질의 (≤120자)
    - detected_intents: 감지된 의도 목록
    - detected_subtypes: 감지된 subtype 코드 목록
    - keywords: 추출된 키워드 목록
    - confidence: 신뢰도 (0.0 ~ 1.0)
    - notes: 참고 사항

    핵심 원칙:
    - 자동 반영 금지 (사용자가 Apply 버튼 눌러야 적용)
    - 판단/결론 금지
    - LLM 실패 시에도 규칙 기반 fallback으로 항상 응답
    """
    start_time = time.time()

    try:
        response = await query_assist(request)

        latency_ms = (time.time() - start_time) * 1000
        _log_assist_request(
            endpoint="query",
            request_data=request.model_dump(),
            response_data=response.model_dump(),
            latency_ms=latency_ms,
        )

        return response

    except Exception as e:
        logger.error(f"Query assist error: {e}")
        # Soft-fail: 에러가 발생해도 기본 응답 반환
        return QueryAssistResponse(
            normalized_query=request.query,
            detected_intents=["lookup"],
            detected_subtypes=[],
            keywords=[],
            confidence=0.0,
            notes="처리 중 오류 발생. 판단/결론 금지.",
            assist_status={
                "status": "FAILED",
                "error_code": "INTERNAL_ERROR",
                "error_message": str(e)[:100],
            },
        )


# =============================================================================
# Evidence Summary Endpoint
# =============================================================================

@router.post("/summary", response_model=EvidenceSummaryResponse)
async def assist_summary(request: EvidenceSummaryRequest) -> EvidenceSummaryResponse:
    """
    Evidence Summary - 비판단 요약

    입력:
    - evidence: Evidence 항목 리스트
      - insurer_code: 보험사 코드
      - doc_type: 문서 유형 (약관, 사업방법서 등)
      - page: 페이지 번호
      - excerpt: 발췌 원문 (≤2000자)
    - task: 작업 유형 (summarize_without_judgement 고정)

    출력:
    - summary_bullets: 요약 bullet 목록 (3~6개, 각 ≤160자)
    - limitations: 제한 사항 (비판단 요약 명시)

    핵심 원칙:
    - 판단 없는 요약만 제공
    - 결론/추천/지급 판단 절대 금지
    - 원문 evidence와 함께 표시해야 함 (UI 책임)
    """
    start_time = time.time()

    try:
        response = await evidence_summary(request)

        latency_ms = (time.time() - start_time) * 1000
        _log_assist_request(
            endpoint="summary",
            request_data=request.model_dump(),
            response_data=response.model_dump(),
            latency_ms=latency_ms,
        )

        return response

    except Exception as e:
        logger.error(f"Evidence summary error: {e}")
        # Soft-fail
        return EvidenceSummaryResponse(
            summary_bullets=["요약 처리 중 오류가 발생했습니다."],
            limitations=[
                "본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음.",
            ],
            assist_status={
                "status": "FAILED",
                "error_code": "INTERNAL_ERROR",
                "error_message": str(e)[:100],
            },
        )
