"""
STEP 2.9: Query Anchor / Context Locking Tests

검증 시나리오:
1. 신규 질의: "DB손해보험 암진단비 알려줘" → anchor 생성
2. insurer-only 후속: "메리츠는?" → anchor.coverage_code 유지
3. anchor 재설정: "유사암은?" → 새 anchor 생성
"""

import pytest

from api.compare import (
    QueryAnchor,
    _has_coverage_keyword,
    _is_insurer_only_query,
    _detect_follow_up_query_type,
    _extract_insurers_from_query,
)


class TestCoverageKeywordDetection:
    """coverage 키워드 탐지 테스트"""

    def test_has_cancer_keyword(self):
        """암 관련 키워드 탐지"""
        assert _has_coverage_keyword("삼성 암진단비 알려줘") is True
        assert _has_coverage_keyword("암진단비 비교") is True
        assert _has_coverage_keyword("유사암 조건은?") is True
        assert _has_coverage_keyword("제자리암 보장 금액") is True

    def test_has_cerebro_keyword(self):
        """뇌/심혈관 관련 키워드 탐지"""
        assert _has_coverage_keyword("뇌졸중진단비") is True
        assert _has_coverage_keyword("심근경색 보장") is True
        assert _has_coverage_keyword("급성심근경색 진단비") is True

    def test_has_surgery_keyword(self):
        """수술비 관련 키워드 탐지"""
        assert _has_coverage_keyword("수술비 비교") is True
        assert _has_coverage_keyword("다빈치 수술") is True

    def test_no_coverage_keyword(self):
        """coverage 키워드 없는 질의"""
        assert _has_coverage_keyword("메리츠는?") is False
        assert _has_coverage_keyword("삼성은 어때?") is False
        assert _has_coverage_keyword("그럼 롯데는?") is False
        assert _has_coverage_keyword("비교해줘") is False


class TestInsurerExtraction:
    """보험사 추출 테스트"""

    def test_extract_single_insurer(self):
        """단일 보험사 추출"""
        assert _extract_insurers_from_query("삼성 암진단비") == ["SAMSUNG"]
        assert _extract_insurers_from_query("메리츠는?") == ["MERITZ"]
        assert _extract_insurers_from_query("DB손해보험 보장 내용") == ["DB"]

    def test_extract_multiple_insurers(self):
        """복수 보험사 추출"""
        insurers = _extract_insurers_from_query("삼성 vs 메리츠 비교")
        assert "SAMSUNG" in insurers
        assert "MERITZ" in insurers

    def test_no_insurer(self):
        """보험사 없는 질의"""
        assert _extract_insurers_from_query("암진단비 조건") == []
        assert _extract_insurers_from_query("일반적인 질문") == []


class TestFollowUpQueryDetection:
    """후속 질의 유형 판별 테스트"""

    @pytest.fixture
    def cancer_anchor(self):
        """암진단비 anchor"""
        return QueryAnchor(
            coverage_code="A4200_1",
            coverage_name="암진단비",
            domain="CANCER",
            original_query="DB손해보험 암진단비 알려줘",
        )

    def test_new_query_without_anchor(self):
        """anchor 없이 신규 질의"""
        query_type, debug = _detect_follow_up_query_type(
            query="삼성 암진단비 알려줘",
            anchor=None,
        )
        assert query_type == "new"
        assert debug["reason"] == "no_anchor"

    def test_new_query_with_coverage_keyword(self, cancer_anchor):
        """coverage 키워드가 있으면 신규 질의 (anchor 재설정)"""
        query_type, debug = _detect_follow_up_query_type(
            query="유사암은 어때?",
            anchor=cancer_anchor,
        )
        assert query_type == "new"
        assert debug["reason"] == "coverage_keyword_found"

    def test_insurer_only_followup(self, cancer_anchor):
        """insurer-only 후속 질의"""
        query_type, debug = _detect_follow_up_query_type(
            query="메리츠는?",
            anchor=cancer_anchor,
        )
        assert query_type == "insurer_only"
        assert debug["reason"] == "insurer_only_followup"

    def test_insurer_only_with_explicit_insurer(self, cancer_anchor):
        """명시적 보험사 이름이 있는 후속 질의"""
        query_type, debug = _detect_follow_up_query_type(
            query="그럼 삼성은?",
            anchor=cancer_anchor,
        )
        assert query_type == "insurer_only"
        assert "SAMSUNG" in debug["extracted_insurers"]

    def test_new_query_resets_anchor(self, cancer_anchor):
        """다른 담보 요청 시 anchor 재설정"""
        query_type, debug = _detect_follow_up_query_type(
            query="뇌졸중진단비 알려줘",
            anchor=cancer_anchor,
        )
        assert query_type == "new"
        assert debug["reason"] == "coverage_keyword_found"


class TestIsInsurerOnlyQuery:
    """insurer-only 질의 판별 상세 테스트"""

    @pytest.fixture
    def anchor(self):
        return QueryAnchor(
            coverage_code="A4200_1",
            coverage_name="암진단비",
            domain="CANCER",
            original_query="삼성 암진단비",
        )

    def test_without_anchor_returns_false(self):
        """anchor 없으면 항상 False"""
        assert _is_insurer_only_query("메리츠는?", anchor=None) is False

    def test_with_coverage_keyword_returns_false(self, anchor):
        """coverage 키워드 있으면 False"""
        assert _is_insurer_only_query("유사암 메리츠", anchor=anchor) is False

    def test_insurer_keyword_only(self, anchor):
        """보험사 키워드만 있으면 True"""
        assert _is_insurer_only_query("메리츠는?", anchor=anchor) is True
        assert _is_insurer_only_query("삼성화재 보여줘", anchor=anchor) is True


class TestQueryAnchorModel:
    """QueryAnchor 모델 테스트"""

    def test_anchor_creation(self):
        """anchor 생성"""
        anchor = QueryAnchor(
            coverage_code="A4200_1",
            coverage_name="암진단비",
            domain="CANCER",
            original_query="삼성 암진단비 알려줘",
        )
        assert anchor.coverage_code == "A4200_1"
        assert anchor.coverage_name == "암진단비"
        assert anchor.domain == "CANCER"

    def test_anchor_without_optional_fields(self):
        """선택적 필드 없이 생성"""
        anchor = QueryAnchor(
            coverage_code="A4200_1",
            original_query="암진단비",
        )
        assert anchor.coverage_code == "A4200_1"
        assert anchor.coverage_name is None
        assert anchor.domain is None


class TestIntegrationScenarios:
    """STEP 2.9 검증 시나리오 통합 테스트"""

    def test_scenario_1_initial_query(self):
        """시나리오 1: "DB손해보험 암진단비 알려줘" - 신규 질의"""
        query_type, debug = _detect_follow_up_query_type(
            query="DB손해보험 암진단비 알려줘",
            anchor=None,
        )
        assert query_type == "new"
        assert "DB" in debug["extracted_insurers"]

    def test_scenario_2_insurer_only_followup(self):
        """시나리오 2: "메리츠는?" - insurer-only 후속 질의"""
        anchor = QueryAnchor(
            coverage_code="A4200_1",
            coverage_name="암진단비",
            domain="CANCER",
            original_query="DB손해보험 암진단비 알려줘",
        )
        query_type, debug = _detect_follow_up_query_type(
            query="메리츠는?",
            anchor=anchor,
        )
        assert query_type == "insurer_only"
        assert "MERITZ" in debug["extracted_insurers"]

    def test_scenario_3_another_insurer_followup(self):
        """시나리오 3: "그럼 삼성은?" - insurer-only 후속 질의"""
        anchor = QueryAnchor(
            coverage_code="A4200_1",
            coverage_name="암진단비",
            domain="CANCER",
            original_query="DB손해보험 암진단비 알려줘",
        )
        query_type, debug = _detect_follow_up_query_type(
            query="그럼 삼성은?",
            anchor=anchor,
        )
        assert query_type == "insurer_only"
        assert "SAMSUNG" in debug["extracted_insurers"]

    def test_scenario_4_anchor_reset(self):
        """시나리오 4: "유사암은?" - anchor 재설정 (coverage 키워드)"""
        anchor = QueryAnchor(
            coverage_code="A4200_1",
            coverage_name="암진단비",
            domain="CANCER",
            original_query="DB손해보험 암진단비 알려줘",
        )
        query_type, debug = _detect_follow_up_query_type(
            query="유사암은?",
            anchor=anchor,
        )
        assert query_type == "new"
        assert debug["has_coverage_keyword"] is True
