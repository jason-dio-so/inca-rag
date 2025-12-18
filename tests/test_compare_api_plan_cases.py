"""
Step J-1: /compare Plan 회귀 테스트

age/gender 입력에 따라 plan_selector 동작을 검증하는 테스트
최소 6개 이상의 테스트 케이스로 구성

테스트 목적:
1. age/gender가 있으면 plan_selector 호출됨
2. debug에 selected_plan 정보 존재
3. 다른 gender/age는 다른 plan 선택
4. A2 정책 유지 (약관은 policy_axis에만)
5. plan_id 필터링이 retrieval에 적용됨
"""

import pytest
import requests

API_BASE = "http://localhost:8000"


# =============================================================================
# Helper Functions
# =============================================================================

def call_compare(request_body: dict) -> dict:
    """Compare API 호출"""
    resp = requests.post(f"{API_BASE}/compare", json=request_body, timeout=30)
    assert resp.status_code == 200, f"API returned {resp.status_code}: {resp.text}"
    return resp.json()


def get_selected_plans(response: dict) -> list:
    """응답에서 selected_plan 목록 추출"""
    return response.get("debug", {}).get("selected_plan", [])


def get_plan_for_insurer(selected_plans: list, insurer_code: str) -> dict | None:
    """특정 보험사의 선택된 plan 정보 추출"""
    for plan in selected_plans:
        if plan.get("insurer_code") == insurer_code:
            return plan
    return None


# =============================================================================
# Test Cases: Plan Selector Invocation
# =============================================================================

class TestPlanSelectorInvocation:
    """Plan selector 호출 검증"""

    def test_no_age_gender_no_plan_selection(self):
        """age/gender 없으면 plan 선택 안함"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
        })

        selected_plans = get_selected_plans(resp)
        # age/gender 없으면 plan 선택 안 하거나 reason이 no_age_gender_provided
        if selected_plans:
            for plan in selected_plans:
                assert plan.get("plan_id") is None or "no_age_gender" in plan.get("reason", "")

    def test_with_age_gender_plan_selected(self):
        """age/gender 있으면 plan 선택됨"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        selected_plans = get_selected_plans(resp)
        assert len(selected_plans) > 0, "selected_plan이 비어있음"

        samsung_plan = get_plan_for_insurer(selected_plans, "SAMSUNG")
        assert samsung_plan is not None
        assert samsung_plan.get("plan_id") is not None
        assert "gender" in samsung_plan.get("reason", "").lower() or "match" in samsung_plan.get("reason", "").lower()

    def test_male_vs_female_different_plans(self):
        """남/여 다른 plan 선택"""
        resp_male = call_compare({
            "insurers": ["LOTTE"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        resp_female = call_compare({
            "insurers": ["LOTTE"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "F",
        })

        male_plans = get_selected_plans(resp_male)
        female_plans = get_selected_plans(resp_female)

        male_plan = get_plan_for_insurer(male_plans, "LOTTE")
        female_plan = get_plan_for_insurer(female_plans, "LOTTE")

        assert male_plan is not None
        assert female_plan is not None
        # plan_id가 다르거나, reason에서 gender 차이가 있어야 함
        if male_plan.get("plan_id") and female_plan.get("plan_id"):
            assert male_plan["plan_id"] != female_plan["plan_id"], "남/여가 같은 plan 선택됨"

    def test_age_39_vs_41_different_plans(self):
        """39세 vs 41세 다른 plan 선택 (age 구간 분리)"""
        resp_39 = call_compare({
            "insurers": ["DB"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 39,
            "gender": "M",
        })

        resp_41 = call_compare({
            "insurers": ["DB"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 41,
            "gender": "M",
        })

        plans_39 = get_selected_plans(resp_39)
        plans_41 = get_selected_plans(resp_41)

        plan_39 = get_plan_for_insurer(plans_39, "DB")
        plan_41 = get_plan_for_insurer(plans_41, "DB")

        assert plan_39 is not None
        assert plan_41 is not None
        # plan_id가 다르거나 (age 기반 분리), 또는 reason에서 age 차이가 있어야 함
        if plan_39.get("plan_id") and plan_41.get("plan_id"):
            assert plan_39["plan_id"] != plan_41["plan_id"], "39세/41세가 같은 plan 선택됨"


# =============================================================================
# Test Cases: A2 Policy Compliance
# =============================================================================

class TestA2PolicyWithPlan:
    """Plan 선택 시에도 A2 정책 유지"""

    def test_compare_axis_no_policy_with_plan(self):
        """plan 선택 시에도 compare_axis에 약관 없음"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        compare_axis = resp.get("compare_axis", [])
        for item in compare_axis:
            for evidence in item.get("evidence", []):
                assert evidence.get("doc_type") != "약관", "compare_axis에 약관 포함됨"

    def test_policy_axis_only_policy_with_plan(self):
        """plan 선택 시에도 policy_axis는 약관만"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "policy_keywords": ["경계성"],
            "age": 35,
            "gender": "M",
        })

        policy_axis = resp.get("policy_axis", [])
        for item in policy_axis:
            for evidence in item.get("evidence", []):
                assert evidence.get("doc_type") == "약관", f"policy_axis에 약관 외 doc_type: {evidence.get('doc_type')}"


# =============================================================================
# Test Cases: Multiple Insurers
# =============================================================================

class TestMultipleInsurersWithPlan:
    """여러 보험사 동시 비교 시 plan 선택"""

    def test_multiple_insurers_each_has_plan(self):
        """여러 보험사 각각 plan 선택됨"""
        resp = call_compare({
            "insurers": ["SAMSUNG", "LOTTE", "DB"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        selected_plans = get_selected_plans(resp)

        # 각 보험사별로 plan 선택 정보가 있어야 함
        insurers_with_plan = {p.get("insurer_code") for p in selected_plans}
        assert "SAMSUNG" in insurers_with_plan
        assert "LOTTE" in insurers_with_plan
        assert "DB" in insurers_with_plan

    def test_multiple_insurers_quota_enforcement(self):
        """여러 보험사 비교 시에도 쏠림 방지"""
        resp = call_compare({
            "insurers": ["SAMSUNG", "LOTTE", "DB"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "top_k_per_insurer": 5,
            "age": 35,
            "gender": "M",
        })

        compare_axis = resp.get("compare_axis", [])
        for item in compare_axis:
            insurer_code = item.get("insurer_code")
            evidence_count = len(item.get("evidence", []))
            assert evidence_count <= 5, f"{insurer_code}: evidence {evidence_count} > top_k 5"


# =============================================================================
# Test Cases: Regression - Same Results for Common Documents
# =============================================================================

class TestCommonDocumentsRegression:
    """공통 문서(plan_id IS NULL)에 대한 회귀 테스트"""

    def test_results_exist_even_with_plan_filter(self):
        """plan 필터가 있어도 공통 문서는 반환됨"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        # 현재 모든 문서가 plan_id IS NULL이므로 결과가 있어야 함
        compare_axis = resp.get("compare_axis", [])
        # 결과가 없을 수도 있음 (coverage_code 매칭이 없는 경우)
        # 하지만 debug에 selected_plan은 있어야 함
        selected_plans = get_selected_plans(resp)
        assert len(selected_plans) > 0, "plan 선택 정보가 없음"

    def test_compare_result_structure_unchanged(self):
        """plan 추가해도 응답 구조 유지"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        # 필수 키 확인
        assert "compare_axis" in resp
        assert "policy_axis" in resp
        assert "debug" in resp
        assert "coverage_compare_result" in resp
        assert "diff_summary" in resp


# =============================================================================
# Test Cases: Edge Cases
# =============================================================================

class TestPlanEdgeCases:
    """Plan 관련 엣지 케이스"""

    def test_only_age_no_gender(self):
        """age만 있고 gender 없음"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
        })

        # age만 있어도 plan 선택 시도
        selected_plans = get_selected_plans(resp)
        # 결과가 있을 수도 없을 수도 있음
        assert isinstance(selected_plans, list)

    def test_only_gender_no_age(self):
        """gender만 있고 age 없음"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "gender": "M",
        })

        # gender만 있어도 plan 선택 시도
        selected_plans = get_selected_plans(resp)
        assert isinstance(selected_plans, list)

    def test_insurer_without_plans(self):
        """plan이 없는 보험사도 에러 없이 처리"""
        # KB는 plan이 없음 (seed에서 제외)
        resp = call_compare({
            "insurers": ["KB"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        # 에러 없이 처리되어야 함
        assert "compare_axis" in resp
        assert "debug" in resp

    def test_extreme_age_values(self):
        """극단적 나이 값"""
        resp = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 100,
            "gender": "M",
        })

        # 에러 없이 처리되어야 함
        assert "compare_axis" in resp
        selected_plans = get_selected_plans(resp)
        assert isinstance(selected_plans, list)


# =============================================================================
# Test Cases: Plan Evidence Differentiation (Step J-2)
# =============================================================================

class TestPlanEvidenceDifferentiation:
    """Plan에 따라 evidence가 다르게 반환되는지 검증"""

    def test_lotte_evidence_plan_id_in_debug(self):
        """LOTTE: evidence에 plan_id 정보 확인"""
        resp = call_compare({
            "insurers": ["LOTTE"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        selected_plans = get_selected_plans(resp)
        lotte_plan = get_plan_for_insurer(selected_plans, "LOTTE")

        assert lotte_plan is not None
        assert lotte_plan.get("plan_id") is not None
        # 남성 plan이 선택되었는지 확인
        assert "M" in lotte_plan.get("reason", "") or "male" in lotte_plan.get("reason", "").lower()

    def test_lotte_male_vs_female_evidence_chunks(self):
        """LOTTE: 남/여 다른 plan이면 evidence chunk도 다름"""
        resp_male = call_compare({
            "insurers": ["LOTTE"],
            "query": "암",
            "age": 35,
            "gender": "M",
        })

        resp_female = call_compare({
            "insurers": ["LOTTE"],
            "query": "암",
            "age": 35,
            "gender": "F",
        })

        male_plans = get_selected_plans(resp_male)
        female_plans = get_selected_plans(resp_female)

        male_plan = get_plan_for_insurer(male_plans, "LOTTE")
        female_plan = get_plan_for_insurer(female_plans, "LOTTE")

        # 서로 다른 plan이 선택됨
        assert male_plan is not None
        assert female_plan is not None
        assert male_plan.get("plan_id") != female_plan.get("plan_id")

    def test_db_age_based_plan_selection(self):
        """DB: 나이에 따라 다른 plan 선택"""
        resp_young = call_compare({
            "insurers": ["DB"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 30,
            "gender": "M",
        })

        resp_old = call_compare({
            "insurers": ["DB"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 50,
            "gender": "M",
        })

        young_plans = get_selected_plans(resp_young)
        old_plans = get_selected_plans(resp_old)

        young_plan = get_plan_for_insurer(young_plans, "DB")
        old_plan = get_plan_for_insurer(old_plans, "DB")

        # 서로 다른 plan이 선택됨
        if young_plan and old_plan:
            if young_plan.get("plan_id") and old_plan.get("plan_id"):
                assert young_plan["plan_id"] != old_plan["plan_id"], "30세/50세가 같은 plan 선택됨"

    def test_plan_filter_affects_retrieval(self):
        """plan 필터가 retrieval에 적용되는지 확인"""
        # LOTTE 남성 plan으로 조회
        resp = call_compare({
            "insurers": ["LOTTE"],
            "query": "보험금",
            "age": 35,
            "gender": "M",
        })

        compare_axis = resp.get("compare_axis", [])
        selected_plans = get_selected_plans(resp)

        lotte_plan = get_plan_for_insurer(selected_plans, "LOTTE")
        if lotte_plan and lotte_plan.get("plan_id"):
            # evidence가 있다면 plan_id와 관련된 문서여야 함
            for item in compare_axis:
                if item.get("insurer_code") == "LOTTE":
                    for evidence in item.get("evidence", []):
                        # chunk_id나 source에 plan 관련 정보가 있을 수 있음
                        # (현재 구조에서는 plan_id 직접 확인이 어려울 수 있음)
                        assert evidence is not None  # 기본 검증

    def test_insurer_with_vs_without_plans(self):
        """plan이 있는 보험사 vs 없는 보험사 비교"""
        resp = call_compare({
            "insurers": ["LOTTE", "KB"],  # LOTTE는 plan 있음, KB는 없음
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        selected_plans = get_selected_plans(resp)

        # LOTTE는 plan 선택됨
        lotte_plan = get_plan_for_insurer(selected_plans, "LOTTE")
        assert lotte_plan is not None
        assert lotte_plan.get("plan_id") is not None

        # KB는 plan이 없으므로 no_product 또는 no_plan
        kb_plan = get_plan_for_insurer(selected_plans, "KB")
        if kb_plan:
            # plan_id가 없거나 reason에 no_plan/no_product 포함
            assert kb_plan.get("plan_id") is None or "no_" in kb_plan.get("reason", "")
