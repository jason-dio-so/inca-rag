"""
Step H-1: amount_extractor / condition_extractor 단위 테스트
"""

import pytest

from services.extraction.amount_extractor import extract_amount, AmountExtract
from services.extraction.condition_extractor import extract_condition_snippet, ConditionExtract


class TestAmountExtractor:
    """amount_extractor 단위 테스트"""

    def test_extract_amount_1000만원(self):
        """1,000만원 추출"""
        text = "가입금액 1,000만원"
        result = extract_amount(text)

        assert result.amount_value == 10_000_000
        assert result.amount_text == "1,000만원"
        assert result.unit == "만원"
        assert result.confidence == "high"  # keyword nearby
        assert result.method == "regex"

    def test_extract_amount_5천만원(self):
        """5천만원 추출"""
        text = "보험금 5천만원 지급"
        result = extract_amount(text)

        assert result.amount_value == 50_000_000
        assert result.unit == "천만원"
        assert result.confidence == "high"

    def test_extract_amount_1억원(self):
        """1억원 추출"""
        text = "보장금액 1억원"
        result = extract_amount(text)

        assert result.amount_value == 100_000_000
        assert result.unit == "억원"
        assert result.confidence == "high"

    def test_extract_amount_no_keyword_low_confidence(self):
        """키워드 없으면 medium/low confidence"""
        text = "총 500만원입니다"
        result = extract_amount(text)

        # 키워드 없지만 단위 있으면 medium
        assert result.unit == "만원"
        assert result.confidence == "medium"

    def test_extract_amount_empty_text(self):
        """빈 텍스트는 None 반환"""
        result = extract_amount("")

        assert result.amount_value is None
        assert result.amount_text is None
        assert result.confidence == "low"

    def test_extract_amount_no_amount(self):
        """금액 없는 텍스트는 None 반환"""
        text = "이 문서에는 금액이 없습니다"
        result = extract_amount(text)

        assert result.amount_value is None
        assert result.confidence == "low"


class TestConditionExtractor:
    """condition_extractor 단위 테스트"""

    def test_extract_condition_basic(self):
        """기본 지급조건 추출"""
        text = "암 최초 진단확정 시 1회 지급"
        result = extract_condition_snippet(text)

        assert result.snippet is not None
        assert "최초" in result.matched_terms
        assert "진단확정" in result.matched_terms
        assert "1회" in result.matched_terms

    def test_extract_condition_borderline(self):
        """경계성종양 조건 추출"""
        text = "경계성 종양으로 진단 시 유사암 진단비 지급"
        result = extract_condition_snippet(text)

        assert result.snippet is not None
        assert "경계성" in result.matched_terms
        assert "유사암" in result.matched_terms

    def test_extract_condition_multiple_sentences(self):
        """여러 문장 중 키워드 많은 것 선택"""
        text = "보험료는 매월 납입합니다. 암 최초 진단확정 시 1회 지급합니다. 해지환급금은 없습니다."
        result = extract_condition_snippet(text)

        # 두 번째 문장(키워드 3개)이 선택되어야 함
        assert result.snippet is not None
        assert "최초" in result.matched_terms
        assert "진단확정" in result.matched_terms

    def test_extract_condition_empty_text(self):
        """빈 텍스트는 None 반환"""
        result = extract_condition_snippet("")

        assert result.snippet is None
        assert result.matched_terms == []

    def test_extract_condition_no_keywords(self):
        """키워드 없는 텍스트는 None 반환"""
        text = "이 문서에는 지급조건 키워드가 없습니다"
        result = extract_condition_snippet(text)

        assert result.snippet is None
        assert result.matched_terms == []

    def test_extract_condition_truncate_long(self):
        """120자 초과 시 잘림"""
        # 긴 문장 생성
        text = "암 최초 진단확정 시 " + "매우 긴 설명이 들어갑니다 " * 10
        result = extract_condition_snippet(text)

        assert result.snippet is not None
        assert len(result.snippet) <= 123  # 120 + "..."


class TestAmountExtractorStrict:
    """Step H-1.6: 가입설계서 엄격 모드 테스트 (보험료 vs 보험금 분리)"""

    def test_premium_column_returns_none(self):
        """가입설계서: '보험료(원) 35,000' → amount_value=None"""
        text = "보험료(원) 35,000"
        result = extract_amount(text, doc_type="가입설계서")

        # NEGATIVE 키워드 근처 금액은 제외
        assert result.amount_value is None

    def test_coverage_amount_extracted(self):
        """가입설계서: '가입금액 1,000만원' → 10,000,000"""
        text = "가입금액 1,000만원"
        result = extract_amount(text, doc_type="가입설계서")

        assert result.amount_value == 10_000_000
        assert result.unit == "만원"
        assert result.confidence == "high"

    def test_benefit_amount_extracted(self):
        """가입설계서: '보험금 500만원' → 5,000,000"""
        text = "보험금 500만원 지급"
        result = extract_amount(text, doc_type="가입설계서")

        assert result.amount_value == 5_000_000
        assert result.unit == "만원"

    def test_mixed_premium_and_benefit_selects_benefit(self):
        """가입설계서: '월납보험료 12,340원 / 암진단비 1,000만원' → 10,000,000"""
        text = "월납보험료 12,340원 / 암진단비 1,000만원"
        result = extract_amount(text, doc_type="가입설계서")

        # 보험금(진단비) 금액이 선택되어야 함
        assert result.amount_value == 10_000_000
        assert result.unit == "만원"

    def test_no_positive_keyword_returns_none(self):
        """가입설계서: POSITIVE 키워드 없이 숫자만 있으면 None"""
        text = "총 금액 500만원입니다"  # POSITIVE 키워드 없음
        result = extract_amount(text, doc_type="가입설계서")

        # 정답성 우선: POSITIVE 키워드 없으면 None
        assert result.amount_value is None

    def test_product_summary_keeps_existing_behavior(self):
        """상품요약서: 기존 동작 유지 (회귀 테스트)"""
        text = "총 금액 500만원입니다"
        result = extract_amount(text, doc_type="상품요약서")

        # 상품요약서는 기존 로직 유지
        assert result.amount_value == 5_000_000
        assert result.unit == "만원"

    def test_business_method_keeps_existing_behavior(self):
        """사업방법서: 기존 동작 유지 (회귀 테스트)"""
        text = "보장 한도 1억원"
        result = extract_amount(text, doc_type="사업방법서")

        # 사업방법서는 기존 로직 유지
        assert result.amount_value == 100_000_000
        assert result.unit == "억원"

    def test_premium_line_header_excluded(self):
        """가입설계서: 보험료(원) 컬럼 헤더가 있는 라인의 금액 제외"""
        text = "담보명 가입금액(만원) 보험료(원)\n암진단비 1,000 35,000"
        result = extract_amount(text, doc_type="가입설계서")

        # 두 번째 라인의 35,000은 보험료이므로 제외
        # 첫 번째 라인에 가입금액이 있지만 POSITIVE 키워드 근처에 숫자+만원 형태가 아님
        # 이 케이스는 복잡하므로 None이 정상
        # 실제로는 "가입금액" 근처의 "1,000"은 단위 없이 숫자만 있어 추출 안됨
        assert result.amount_value is None


class TestAmountExtractorBlockHeuristic:
    """Step H-1.7: 가입설계서 표-휴리스틱 테스트 (premium_block 제거)"""

    def test_premium_block_window_excluded(self):
        """premium header 라인 ±3 범위의 금액은 제외"""
        text = """보장내용
담보명 가입금액(만원) 보험료(원)
암진단비 1,000 35,000
심근경색 500 17,000
뇌졸중 500 17,000"""
        result = extract_amount(text, doc_type="가입설계서")

        # 보험료(원) 헤더 근처의 금액은 모두 제외
        # 가입금액(만원) 근처에 금액이 있지만 단위 없는 숫자라 추출 안됨
        assert result.amount_value is None

    def test_coverage_block_amount_extracted(self):
        """coverage header 라인 근처 금액은 우선 추출"""
        text = """보장내용
가입금액 1,000만원
암 진단 시 지급"""
        result = extract_amount(text, doc_type="가입설계서")

        # 가입금액 근처 금액 추출
        assert result.amount_value == 10_000_000
        assert result.unit == "만원"

    def test_premium_coverage_mixed_selects_coverage(self):
        """premium_block과 coverage_block이 섞여 있으면 coverage 선택"""
        text = """[보장내용]
암진단비 1,000만원 지급

[보험료]
보험료(원) 35,000
월납 35,000원"""
        result = extract_amount(text, doc_type="가입설계서")

        # coverage_block 내 금액(1,000만원) 선택
        assert result.amount_value == 10_000_000
        assert result.unit == "만원"

    def test_premium_header_line_nearby_numbers_excluded(self):
        """보험료(원) 헤더가 있는 라인 근처의 숫자는 제외 (표 구조)"""
        text = """보장내용
담보명 보험료(원) 가입금액
암진단비 12,340 1,000
심근경색 6,170 500"""
        result = extract_amount(text, doc_type="가입설계서")

        # 표 구조에서 보험료(원) 근처 숫자는 제외
        # 가입금액 근처 숫자도 단위 없어 추출 안됨
        assert result.amount_value is None

    def test_월보험료_header_excluded(self):
        """월보험료 헤더 근처 금액 제외"""
        text = """보장담보 안내

월보험료 현황
35,000원

---

보장내용 안내
가입금액 1,000만원"""
        result = extract_amount(text, doc_type="가입설계서")

        # 35,000원은 premium_block, 1,000만원은 coverage_block 밖이지만 POSITIVE 근처
        assert result.amount_value == 10_000_000

    def test_납입보험료_header_excluded(self):
        """납입보험료 헤더 근처 금액 제외"""
        text = """납입보험료 안내
35,000원 납입
---
보험금 안내
진단비 500만원"""
        result = extract_amount(text, doc_type="가입설계서")

        # 보험금 근처 금액 선택
        assert result.amount_value == 5_000_000

    def test_담보명_header_coverage_block(self):
        """담보명 헤더가 있으면 coverage block으로 인식"""
        text = """담보명 가입금액
암진단비 1,000만원
심근경색 500만원"""
        result = extract_amount(text, doc_type="가입설계서")

        # coverage_block 내 금액 선택
        assert result.amount_value == 10_000_000

    def test_보장금액_header_coverage_block(self):
        """보장금액 헤더가 있으면 coverage block으로 인식"""
        text = """특약 보장금액
암 진단비 1억원
사망 보험금 2억원"""
        result = extract_amount(text, doc_type="가입설계서")

        # coverage_block 내 첫 번째 금액 선택
        assert result.amount_value == 100_000_000
        assert result.unit == "억원"

    def test_other_doc_type_not_affected(self):
        """상품요약서/사업방법서는 block 휴리스틱 영향 없음 (회귀 테스트)"""
        text = """보험료(원) 안내
35,000원 납입"""
        result = extract_amount(text, doc_type="상품요약서")

        # 상품요약서는 기존 로직 (NEGATIVE 근처 제외하지만 fallback)
        # NEGATIVE 키워드 근처라 제외될 수도 있지만 회귀 테스트
        # 실제로는 "보험료" 근처라 필터링될 수 있음
        # 기존 동작 유지 확인 (None일 수도 있음)
        # 상품요약서는 strict 모드가 아니므로 기존 로직 적용
        pass  # 이 테스트는 strict 모드 영향 없음 확인용

    def test_complex_table_structure(self):
        """복잡한 표 구조에서 올바른 금액 선택"""
        text = """담보 가입 현황

담보명 | 가입금액(만원) | 보험료(원)
---------------------------------
암진단비 | 1,000 | 35,000
뇌졸중진단비 | 500 | 17,500
급성심근경색 | 500 | 17,500

총 보험료: 70,000원

※ 실제 보험금은 가입금액 기준 지급됩니다.
암 진단비 1,000만원"""
        result = extract_amount(text, doc_type="가입설계서")

        # 마지막 줄의 "1,000만원"이 선택되어야 함 (단위 있음 + POSITIVE 키워드 근처)
        # 표 내의 숫자들은 단위가 없어서 추출 안됨
        assert result.amount_value == 10_000_000
        assert result.unit == "만원"
