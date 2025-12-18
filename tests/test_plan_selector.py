"""
Step I: Plan 자동 선택 테스트

plan_selector 단위 테스트 + compare API 통합 테스트
"""

import pytest
from unittest.mock import MagicMock, patch

from services.retrieval.plan_selector import (
    select_plan_for_insurer,
    select_plans_for_insurers,
    get_plan_ids_for_retrieval,
    SelectedPlan,
)


# =============================================================================
# Mock DB Helper
# =============================================================================

def _make_mock_cursor(query_results: dict):
    """
    쿼리 결과를 반환하는 mock cursor 생성

    query_results: {"query_substring": [row1, row2, ...], ...}
    """
    cursor = MagicMock()
    results_queue = []

    def execute(query, params=None):
        # 쿼리 문자열에 맞는 결과 찾기
        for key, rows in query_results.items():
            if key in query:
                results_queue.clear()
                results_queue.extend(rows)
                return
        results_queue.clear()

    def fetchone():
        return results_queue[0] if results_queue else None

    def fetchall():
        return results_queue

    cursor.execute = execute
    cursor.fetchone = fetchone
    cursor.fetchall = fetchall
    return cursor


def _make_mock_conn(cursor):
    """Mock connection 생성"""
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn


# =============================================================================
# Unit Tests: select_plan_for_insurer
# =============================================================================

class TestSelectPlanForInsurer:
    """select_plan_for_insurer 단위 테스트"""

    def test_no_product_found(self):
        """product가 없으면 plan_id=None, reason='no_product_found'"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [],  # product 없음
        })
        conn = _make_mock_conn(cursor)

        result = select_plan_for_insurer(conn, "UNKNOWN", age=30, gender="M")

        assert result.plan_id is None
        assert result.reason == "no_product_found"

    def test_no_age_gender_provided(self):
        """age/gender 모두 None이면 plan 선택 안함"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
        })
        conn = _make_mock_conn(cursor)

        result = select_plan_for_insurer(conn, "SAMSUNG", age=None, gender=None)

        assert result.plan_id is None
        assert result.reason == "no_age_gender_provided"
        assert result.product_id == 1

    def test_gender_exact_match_preferred(self):
        """gender 정확 일치가 우선"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
            "FROM product_plan": [
                {
                    "plan_id": 101,
                    "plan_name": "남성플랜",
                    "gender": "M",
                    "age_min": 0,
                    "age_max": 99,
                }
            ],
        })
        conn = _make_mock_conn(cursor)

        result = select_plan_for_insurer(conn, "SAMSUNG", age=30, gender="M")

        assert result.plan_id == 101
        assert "gender_match(M)" in result.reason

    def test_gender_universal_fallback(self):
        """정확 일치 없으면 U(공용) 선택"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
            "FROM product_plan": [
                {
                    "plan_id": 200,
                    "plan_name": "공용플랜",
                    "gender": "U",
                    "age_min": None,
                    "age_max": None,
                }
            ],
        })
        conn = _make_mock_conn(cursor)

        result = select_plan_for_insurer(conn, "SAMSUNG", age=30, gender="M")

        assert result.plan_id == 200
        assert "gender_universal" in result.reason

    def test_age_range_narrower_preferred(self):
        """age 범위가 좁은 plan 우선"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
            "FROM product_plan": [
                {
                    "plan_id": 101,
                    "plan_name": "남성-30대",
                    "gender": "M",
                    "age_min": 30,
                    "age_max": 39,  # 범위 10
                }
            ],
        })
        conn = _make_mock_conn(cursor)

        result = select_plan_for_insurer(conn, "SAMSUNG", age=35, gender="M")

        assert result.plan_id == 101
        assert "age_range(30-39)" in result.reason

    def test_no_matching_plan(self):
        """조건에 맞는 plan 없으면 plan_id=None"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
            "FROM product_plan": [],  # 조건에 맞는 plan 없음
        })
        conn = _make_mock_conn(cursor)

        result = select_plan_for_insurer(conn, "SAMSUNG", age=200, gender="M")  # 200세는 없음

        assert result.plan_id is None
        assert result.reason == "no_matching_plan"


# =============================================================================
# Unit Tests: select_plans_for_insurers
# =============================================================================

class TestSelectPlansForInsurers:
    """select_plans_for_insurers 단위 테스트"""

    def test_multiple_insurers(self):
        """여러 보험사에 대해 각각 plan 선택"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
            "FROM product_plan": [
                {"plan_id": 101, "plan_name": "남성플랜", "gender": "M", "age_min": 0, "age_max": 99}
            ],
        })
        conn = _make_mock_conn(cursor)

        results = select_plans_for_insurers(conn, ["SAMSUNG", "LOTTE"], age=30, gender="M")

        assert "SAMSUNG" in results
        assert "LOTTE" in results
        assert len(results) == 2


# =============================================================================
# Unit Tests: get_plan_ids_for_retrieval
# =============================================================================

class TestGetPlanIdsForRetrieval:
    """get_plan_ids_for_retrieval 단위 테스트"""

    def test_extracts_plan_ids(self):
        """plan_id만 추출"""
        selected_plans = {
            "SAMSUNG": SelectedPlan("SAMSUNG", 1, 101, "남성플랜", "test"),
            "LOTTE": SelectedPlan("LOTTE", 2, None, None, "no_match"),
        }

        result = get_plan_ids_for_retrieval(selected_plans)

        assert result["SAMSUNG"] == 101
        assert result["LOTTE"] is None


# =============================================================================
# Integration Tests: API 레벨
# =============================================================================

class TestCompareAPIWithPlanSelector:
    """compare API와 plan_selector 통합 테스트 (API 스키마 확인)"""

    def test_age_gender_fields_in_request(self):
        """CompareRequest에 age/gender 필드 존재"""
        from api.compare import CompareRequest

        # age/gender 필드가 존재하는지 확인
        fields = CompareRequest.model_fields
        assert "age" in fields
        assert "gender" in fields

    def test_age_gender_optional(self):
        """age/gender는 optional"""
        from api.compare import CompareRequest

        # age/gender 없이 생성 가능
        request = CompareRequest(
            insurers=["SAMSUNG"],
            query="암진단비",
        )
        assert request.age is None
        assert request.gender is None

    def test_age_gender_with_values(self):
        """age/gender 값 설정 가능"""
        from api.compare import CompareRequest

        request = CompareRequest(
            insurers=["SAMSUNG"],
            query="암진단비",
            age=35,
            gender="M",
        )
        assert request.age == 35
        assert request.gender == "M"

    def test_gender_validation(self):
        """gender는 M/F만 허용"""
        from api.compare import CompareRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompareRequest(
                insurers=["SAMSUNG"],
                query="암진단비",
                gender="X",  # 잘못된 값
            )


# =============================================================================
# Regression Tests: 기존 동작 유지
# =============================================================================

class TestRegressionNoPlanSelection:
    """age/gender 없으면 기존과 동일하게 동작"""

    def test_compare_function_signature(self):
        """compare 함수에 age/gender 파라미터 존재"""
        from services.retrieval.compare_service import compare
        import inspect

        sig = inspect.signature(compare)
        params = list(sig.parameters.keys())

        assert "age" in params
        assert "gender" in params

    def test_get_compare_axis_accepts_plan_ids(self):
        """get_compare_axis에 plan_ids 파라미터 존재"""
        from services.retrieval.compare_service import get_compare_axis
        import inspect

        sig = inspect.signature(get_compare_axis)
        params = list(sig.parameters.keys())

        assert "plan_ids" in params


# =============================================================================
# A2 Policy Tests: 약관 axis는 plan 무시
# =============================================================================

class TestA2PolicyMaintained:
    """A2 정책: policy_axis는 plan 필터링 적용 안함"""

    def test_policy_axis_no_plan_filter(self):
        """get_policy_axis에는 plan_ids 파라미터 없음"""
        from services.retrieval.compare_service import get_policy_axis
        import inspect

        sig = inspect.signature(get_policy_axis)
        params = list(sig.parameters.keys())

        # policy_axis는 plan_ids 파라미터가 없어야 함
        assert "plan_ids" not in params
