"""
Step H-1.8: Amount Source Policy 단위 테스트

amount_source_priority 정책 검증:
- 상품요약서 > 사업방법서 > 가입설계서
- 가입설계서 confidence='low'이면 제외
"""

import pytest

from services.retrieval.compare_service import (
    _resolve_amount_from_evidence,
    ResolvedAmount,
    Evidence,
    AmountInfo,
    ConditionInfo,
)


def _make_evidence(
    doc_type: str,
    amount_value: int | None,
    amount_text: str | None = None,
    confidence: str = "high",
    document_id: int = 1,
) -> Evidence:
    """테스트용 Evidence 생성 헬퍼"""
    amount_info = None
    if amount_value is not None or amount_text is not None:
        amount_info = AmountInfo(
            amount_value=amount_value,
            amount_text=amount_text or f"{amount_value}원",
            unit="만원" if amount_value and amount_value >= 10000 else "원",
            confidence=confidence,
            method="regex",
        )

    return Evidence(
        document_id=document_id,
        doc_type=doc_type,
        page_start=1,
        preview="테스트 preview",
        score=0.5,
        amount=amount_info,
        condition_snippet=None,
    )


class TestAmountSourcePolicy:
    """H-1.8: amount_source_priority 정책 테스트"""

    def test_상품요약서_우선_선택(self):
        """상품요약서 amount가 있으면 가입설계서보다 우선 선택"""
        evidence_list = [
            _make_evidence("가입설계서", 10_000_000, "1,000만원", "high", document_id=1),
            _make_evidence("상품요약서", 5_000_000, "500만원", "high", document_id=2),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        assert result is not None
        assert result.amount_value == 5_000_000
        assert result.source_doc_type == "상품요약서"
        assert result.source_document_id == 2

    def test_사업방법서_가입설계서보다_우선(self):
        """사업방법서 amount가 있으면 가입설계서보다 우선 선택"""
        evidence_list = [
            _make_evidence("가입설계서", 10_000_000, "1,000만원", "high", document_id=1),
            _make_evidence("사업방법서", 8_000_000, "800만원", "high", document_id=2),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        assert result is not None
        assert result.amount_value == 8_000_000
        assert result.source_doc_type == "사업방법서"

    def test_가입설계서_low_confidence_제외(self):
        """가입설계서 confidence='low'이면 resolved_amount.amount_value는 None"""
        evidence_list = [
            _make_evidence("가입설계서", 10_000_000, "1,000만원", "low", document_id=1),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        # confidence='low'인 가입설계서는 제외되므로 None
        assert result is None

    def test_가입설계서_high_confidence_선택(self):
        """가입설계서만 있고 confidence='high'이면 선택됨"""
        evidence_list = [
            _make_evidence("가입설계서", 10_000_000, "1,000만원", "high", document_id=1),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        assert result is not None
        assert result.amount_value == 10_000_000
        assert result.source_doc_type == "가입설계서"
        assert result.confidence == "high"

    def test_모든_amount_none이면_resolved_amount도_none(self):
        """amount가 전부 None이면 resolved_amount도 None"""
        evidence_list = [
            _make_evidence("가입설계서", None, None, "low", document_id=1),
            _make_evidence("상품요약서", None, None, "low", document_id=2),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        assert result is None

    def test_빈_evidence_리스트(self):
        """빈 evidence 리스트면 None"""
        result = _resolve_amount_from_evidence([])
        assert result is None

    def test_상품요약서_사업방법서_가입설계서_전체_우선순위(self):
        """세 doc_type 모두 있을 때 상품요약서 우선"""
        evidence_list = [
            _make_evidence("가입설계서", 10_000_000, "1,000만원", "high", document_id=1),
            _make_evidence("사업방법서", 8_000_000, "800만원", "high", document_id=2),
            _make_evidence("상품요약서", 5_000_000, "500만원", "high", document_id=3),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        assert result is not None
        assert result.amount_value == 5_000_000
        assert result.source_doc_type == "상품요약서"
        assert result.source_document_id == 3

    def test_상품요약서_amount_none이면_사업방법서_선택(self):
        """상품요약서 amount=None이면 사업방법서 선택"""
        evidence_list = [
            _make_evidence("가입설계서", 10_000_000, "1,000만원", "high", document_id=1),
            _make_evidence("사업방법서", 8_000_000, "800만원", "high", document_id=2),
            _make_evidence("상품요약서", None, None, "low", document_id=3),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        assert result is not None
        assert result.amount_value == 8_000_000
        assert result.source_doc_type == "사업방법서"

    def test_가입설계서_medium_confidence_선택(self):
        """가입설계서 confidence='medium'이면 선택됨 (low만 제외)"""
        evidence_list = [
            _make_evidence("가입설계서", 10_000_000, "1,000만원", "medium", document_id=1),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        assert result is not None
        assert result.amount_value == 10_000_000
        assert result.confidence == "medium"

    def test_약관_doc_type은_amount_없음(self):
        """약관 doc_type은 amount가 없으므로 선택 안됨"""
        evidence_list = [
            Evidence(
                document_id=1,
                doc_type="약관",
                page_start=1,
                preview="약관 preview",
                score=0.5,
                amount=None,  # 약관은 amount 없음
                condition_snippet=None,
            ),
        ]

        result = _resolve_amount_from_evidence(evidence_list)

        assert result is None
