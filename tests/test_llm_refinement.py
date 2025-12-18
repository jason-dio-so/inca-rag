"""
Step H-2: LLM Refinement 단위 테스트

FakeLLMClient를 사용하여 LLM 없이도 CI 통과
"""

import pytest

from services.extraction.llm_client import FakeLLMClient, validate_span_in_text
from services.extraction.llm_schemas import LLMExtractResult
from services.retrieval.compare_service import (
    InsurerCompareCell,
    Evidence,
    AmountInfo,
    ResolvedAmount,
    refine_amount_with_llm_if_needed,
    refine_coverage_compare_result_with_llm,
    CoverageCompareRow,
    _should_call_llm_for_cell,
    LLMRefinementStats,
)


def _make_evidence(
    doc_type: str,
    amount_value: int | None = None,
    confidence: str = "high",
    preview: str = "테스트 preview 암진단비 1,000만원 지급",
    document_id: int = 1,
) -> Evidence:
    """테스트용 Evidence 생성"""
    amount_info = None
    if amount_value is not None or confidence != "high":
        amount_info = AmountInfo(
            amount_value=amount_value,
            amount_text=f"{amount_value}원" if amount_value else None,
            unit="만원" if amount_value and amount_value >= 10000 else "원",
            confidence=confidence,
            method="regex",
        )

    return Evidence(
        document_id=document_id,
        doc_type=doc_type,
        page_start=1,
        preview=preview,
        score=0.5,
        amount=amount_info,
        condition_snippet=None,
    )


def _make_cell(
    insurer_code: str,
    evidence_list: list[Evidence],
    resolved_amount: ResolvedAmount | None = None,
) -> InsurerCompareCell:
    """테스트용 InsurerCompareCell 생성"""
    return InsurerCompareCell(
        insurer_code=insurer_code,
        doc_type_counts={"가입설계서": 1},
        best_evidence=evidence_list,
        resolved_amount=resolved_amount,
    )


def _make_fake_llm_response(
    coverage_code: str,
    label: str,
    amount_value: int | None,
    confidence: str,
    span_text: str | None = None,
) -> dict:
    """FakeLLMClient용 응답 생성"""
    return {
        "coverage_code": coverage_code,
        "insurer_code": "SAMSUNG",
        "doc_type": "가입설계서",
        "document_id": 1,
        "page_start": 1,
        "chunk_id": 1,
        "amount": {
            "label": label,
            "amount_value": amount_value,
            "amount_text": f"{amount_value}원" if amount_value else None,
            "unit": "만원",
            "confidence": confidence,
            "span": {"text": span_text, "start": 0, "end": 10} if span_text else None,
        },
        "condition": {
            "snippet": None,
            "matched_terms": [],
            "confidence": "low",
            "span": None,
        },
        "notes": None,
    }


class TestShouldCallLLM:
    """_should_call_llm_for_cell 선별 조건 테스트"""

    def test_resolved_amount_already_exists_no_call(self):
        """resolved_amount 이미 있으면 호출 0회"""
        resolved = ResolvedAmount(
            amount_value=10_000_000,
            amount_text="1,000만원",
            unit="만원",
            confidence="high",
            source_doc_type="상품요약서",
        )
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "low")],
            resolved_amount=resolved,
        )

        should_call, reason, _ = _should_call_llm_for_cell(cell, "암진단비 금액")
        assert not should_call
        assert "already exists" in reason

    def test_no_enrollment_evidence_no_call(self):
        """가입설계서 evidence가 없으면 호출 0회"""
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("상품요약서", None, "low")],
        )

        should_call, reason, _ = _should_call_llm_for_cell(cell, "암진단비 금액")
        assert not should_call
        assert "no 가입설계서" in reason

    def test_enrollment_confidence_high_no_call(self):
        """가입설계서 confidence가 high이면 호출 0회"""
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", 10_000_000, "high")],
        )

        should_call, reason, _ = _should_call_llm_for_cell(cell, "암진단비 금액")
        assert not should_call
        assert "confidence is high" in reason

    def test_no_amount_intent_no_call(self):
        """query에 금액 의도가 없으면 호출 0회"""
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "low")],
        )

        should_call, reason, _ = _should_call_llm_for_cell(cell, "암 종류")  # 금액 의도 없음
        assert not should_call
        assert "no amount intent" in reason

    def test_conditions_met_should_call(self):
        """조건 충족 시 호출 필요"""
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "medium")],
        )

        should_call, reason, evidence = _should_call_llm_for_cell(cell, "암진단비 얼마")
        assert should_call
        assert evidence is not None


class TestRefineAmountWithLLM:
    """refine_amount_with_llm_if_needed 테스트"""

    @pytest.mark.asyncio
    async def test_premium_amount_no_upgrade(self):
        """FakeLLM이 premium_amount 반환 → resolved_amount 변화 없음"""
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "medium", "암진단비 보험료 35,000원")],
        )

        fake_llm = FakeLLMClient(responses={
            "CANCER_DIAGNOSIS": _make_fake_llm_response(
                "CANCER_DIAGNOSIS", "premium_amount", 35000, "high", "보험료 35,000원"
            )
        })

        updated_cell, debug_info = await refine_amount_with_llm_if_needed(
            cell=cell,
            insurer_code="SAMSUNG",
            coverage_code="CANCER_DIAGNOSIS",
            query="암진단비 금액",
            llm_client=fake_llm,
        )

        assert updated_cell.resolved_amount is None
        assert debug_info["called"]
        assert "premium_amount" in debug_info["reason"]

    @pytest.mark.asyncio
    async def test_benefit_amount_medium_upgrade(self):
        """FakeLLM이 benefit_amount + medium 반환 → resolved_amount 업그레이드됨"""
        preview_text = "암진단비 1,000만원 지급"
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "medium", preview_text)],
        )

        fake_llm = FakeLLMClient(responses={
            "CANCER_DIAGNOSIS": _make_fake_llm_response(
                "CANCER_DIAGNOSIS", "benefit_amount", 10_000_000, "medium", "1,000만원"
            )
        })

        updated_cell, debug_info = await refine_amount_with_llm_if_needed(
            cell=cell,
            insurer_code="SAMSUNG",
            coverage_code="CANCER_DIAGNOSIS",
            query="암진단비 얼마",
            llm_client=fake_llm,
        )

        assert updated_cell.resolved_amount is not None
        assert updated_cell.resolved_amount.amount_value == 10_000_000
        assert updated_cell.resolved_amount.source_doc_type == "가입설계서"
        assert debug_info["upgraded"]

    @pytest.mark.asyncio
    async def test_benefit_amount_low_no_upgrade(self):
        """FakeLLM이 benefit_amount + low 반환 → 업그레이드 금지"""
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "medium", "암진단비 가입금액 1,000만원")],
        )

        fake_llm = FakeLLMClient(responses={
            "CANCER_DIAGNOSIS": _make_fake_llm_response(
                "CANCER_DIAGNOSIS", "benefit_amount", 10_000_000, "low", "1,000만원"
            )
        })

        updated_cell, debug_info = await refine_amount_with_llm_if_needed(
            cell=cell,
            insurer_code="SAMSUNG",
            coverage_code="CANCER_DIAGNOSIS",
            query="암진단비 금액",
            llm_client=fake_llm,
        )

        assert updated_cell.resolved_amount is None
        assert debug_info["called"]
        assert "confidence is low" in debug_info["reason"]

    @pytest.mark.asyncio
    async def test_span_not_in_text_discard(self):
        """span.text가 chunk_text에 포함되지 않으면 결과 폐기 (환각 방지)"""
        preview_text = "암진단비 보장내용 설명"  # "2억원" 없음
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "medium", preview_text)],
        )

        fake_llm = FakeLLMClient(responses={
            "CANCER_DIAGNOSIS": _make_fake_llm_response(
                "CANCER_DIAGNOSIS", "benefit_amount", 200_000_000, "high", "2억원"  # 환각
            )
        })

        updated_cell, debug_info = await refine_amount_with_llm_if_needed(
            cell=cell,
            insurer_code="SAMSUNG",
            coverage_code="CANCER_DIAGNOSIS",
            query="암진단비 얼마",
            llm_client=fake_llm,
        )

        assert updated_cell.resolved_amount is None
        assert debug_info["called"]
        assert "hallucination" in debug_info["reason"]

    @pytest.mark.asyncio
    async def test_unknown_label_no_upgrade(self):
        """label이 unknown이면 업그레이드 안함"""
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "medium", "암진단비 관련 내용")],
        )

        fake_llm = FakeLLMClient(responses={
            "CANCER_DIAGNOSIS": _make_fake_llm_response(
                "CANCER_DIAGNOSIS", "unknown", None, "low", None
            )
        })

        updated_cell, debug_info = await refine_amount_with_llm_if_needed(
            cell=cell,
            insurer_code="SAMSUNG",
            coverage_code="CANCER_DIAGNOSIS",
            query="암진단비 금액",
            llm_client=fake_llm,
        )

        assert updated_cell.resolved_amount is None


class TestRefineCoverageCompareResult:
    """refine_coverage_compare_result_with_llm 전체 테스트"""

    @pytest.mark.asyncio
    async def test_max_calls_limit(self):
        """LLM_MAX_CALLS_PER_REQUEST 초과 방지"""
        import os
        original = os.environ.get("LLM_MAX_CALLS_PER_REQUEST")
        os.environ["LLM_MAX_CALLS_PER_REQUEST"] = "2"

        try:
            # 3개의 셀 생성
            cells = [
                _make_cell("SAMSUNG", [_make_evidence("가입설계서", None, "medium", "암진단비 1,000만원")]),
                _make_cell("LOTTE", [_make_evidence("가입설계서", None, "medium", "암진단비 500만원")]),
                _make_cell("DB", [_make_evidence("가입설계서", None, "medium", "암진단비 800만원")]),
            ]
            row = CoverageCompareRow(
                coverage_code="CANCER_DIAGNOSIS",
                coverage_name="암진단비",
                insurers=cells,
            )

            fake_llm = FakeLLMClient(responses={
                "CANCER_DIAGNOSIS": _make_fake_llm_response(
                    "CANCER_DIAGNOSIS", "benefit_amount", 10_000_000, "medium", "1,000만원"
                )
            })

            refined, stats = await refine_coverage_compare_result_with_llm(
                [row], "암진단비 금액", fake_llm
            )

            # max_calls=2이므로 2번만 호출
            assert stats.total_calls == 2
            assert any("max_calls" in r for r in stats.skip_reasons)
        finally:
            if original:
                os.environ["LLM_MAX_CALLS_PER_REQUEST"] = original
            else:
                os.environ.pop("LLM_MAX_CALLS_PER_REQUEST", None)

    @pytest.mark.asyncio
    async def test_llm_disabled_no_crash(self):
        """LLM disabled 상태에서도 요청 전체는 200 유지"""
        from services.extraction.llm_client import DisabledLLMClient

        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("가입설계서", None, "medium", "암진단비 1,000만원")],
        )
        row = CoverageCompareRow(
            coverage_code="CANCER_DIAGNOSIS",
            coverage_name="암진단비",
            insurers=[cell],
        )

        # DisabledLLMClient 사용
        refined, stats = await refine_coverage_compare_result_with_llm(
            [row], "암진단비 금액", DisabledLLMClient()
        )

        # crash 없이 완료
        assert len(refined) == 1
        assert refined[0].insurers[0].resolved_amount is None  # 업그레이드 안됨
        assert "LLM disabled" in stats.skip_reasons[0] if stats.skip_reasons else True


class TestSpanValidation:
    """span 검증 테스트"""

    def test_span_in_text(self):
        """span이 텍스트에 포함됨"""
        assert validate_span_in_text("1,000만원", "암진단비 1,000만원 지급")

    def test_span_not_in_text(self):
        """span이 텍스트에 없음"""
        assert not validate_span_in_text("2억원", "암진단비 1,000만원 지급")

    def test_span_none(self):
        """span이 None"""
        assert not validate_span_in_text(None, "암진단비 1,000만원 지급")

    def test_span_with_whitespace_normalization(self):
        """공백 정규화 후 비교"""
        assert validate_span_in_text("1,000 만원", "암진단비 1,000  만원 지급")


class TestA2PolicyMaintained:
    """A2 정책 유지 테스트 - 약관 axis에는 LLM 적용 금지"""

    @pytest.mark.asyncio
    async def test_약관_evidence_not_processed(self):
        """약관 doc_type은 LLM 호출 대상이 아님"""
        cell = _make_cell(
            "SAMSUNG",
            [_make_evidence("약관", None, "medium", "약관 내용")],  # 가입설계서가 아님
        )

        fake_llm = FakeLLMClient(responses={
            "CANCER_DIAGNOSIS": _make_fake_llm_response(
                "CANCER_DIAGNOSIS", "benefit_amount", 10_000_000, "medium", "1,000만원"
            )
        })

        updated_cell, debug_info = await refine_amount_with_llm_if_needed(
            cell=cell,
            insurer_code="SAMSUNG",
            coverage_code="CANCER_DIAGNOSIS",
            query="암진단비 금액",
            llm_client=fake_llm,
        )

        # 가입설계서가 아니므로 호출 안됨
        assert not debug_info["called"]
        assert "no 가입설계서" in debug_info["reason"]
