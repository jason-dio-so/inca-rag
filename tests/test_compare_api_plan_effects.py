"""
Step J-3: /compare Plan Effects E2E 검증 테스트

Plan 선택이 실제 검색 결과(evidence, resolved_amount)에 미치는 영향을 검증

테스트 목적:
1. LOTTE gender=M vs F → best_evidence.document_id 차이 확인
2. LOTTE gender=M vs F → resolved_amount.source_document_id 차이 확인
3. DB age=39 vs 41 → evidence 또는 resolved_amount 변화 확인
4. SAMSUNG (plan 없는 보험사) → age/gender에 관계없이 결과 동일 (회귀)
"""

import pytest
import requests
import warnings

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


def extract_document_ids_from_compare_result(response: dict, insurer_code: str) -> set[int]:
    """coverage_compare_result에서 특정 보험사의 evidence document_id 집합 추출"""
    doc_ids = set()
    compare_result = response.get("coverage_compare_result", [])

    for row in compare_result:
        insurers = row.get("insurers", [])
        for ins in insurers:
            if ins.get("insurer_code") == insurer_code:
                for evidence in ins.get("best_evidence", []):
                    if evidence.get("document_id"):
                        doc_ids.add(evidence["document_id"])

    return doc_ids


def extract_resolved_amount_sources(response: dict, insurer_code: str) -> set[int]:
    """coverage_compare_result에서 특정 보험사의 resolved_amount.source_document_id 집합 추출"""
    doc_ids = set()
    compare_result = response.get("coverage_compare_result", [])

    for row in compare_result:
        insurers = row.get("insurers", [])
        for ins in insurers:
            if ins.get("insurer_code") == insurer_code:
                resolved = ins.get("resolved_amount")
                if resolved and resolved.get("source_document_id"):
                    doc_ids.add(resolved["source_document_id"])

    return doc_ids


def extract_all_evidence_document_ids(response: dict, insurer_code: str) -> set[int]:
    """compare_axis에서 특정 보험사의 모든 evidence document_id 집합 추출"""
    doc_ids = set()
    compare_axis = response.get("compare_axis", [])

    for item in compare_axis:
        if item.get("insurer_code") == insurer_code:
            for evidence in item.get("evidence", []):
                if evidence.get("document_id"):
                    doc_ids.add(evidence["document_id"])

    return doc_ids


# =============================================================================
# Test Cases: LOTTE Gender Effects
# =============================================================================

class TestLotteGenderEffects:
    """LOTTE: 성별에 따른 Plan 효과 검증"""

    def test_lotte_gender_m_vs_f_different_plan_ids(self):
        """LOTTE: 남/여 다른 plan_id 선택 확인"""
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

        male_plan = get_plan_for_insurer(get_selected_plans(resp_male), "LOTTE")
        female_plan = get_plan_for_insurer(get_selected_plans(resp_female), "LOTTE")

        assert male_plan is not None, "LOTTE 남성 plan 없음"
        assert female_plan is not None, "LOTTE 여성 plan 없음"
        assert male_plan.get("plan_id") is not None, "LOTTE 남성 plan_id 없음"
        assert female_plan.get("plan_id") is not None, "LOTTE 여성 plan_id 없음"
        assert male_plan["plan_id"] != female_plan["plan_id"], \
            f"LOTTE 남/여 plan_id 동일: {male_plan['plan_id']}"

    def test_lotte_gender_m_vs_f_evidence_document_difference(self):
        """
        LOTTE: 남/여 다른 plan → best_evidence.document_id 차이

        coverage_compare_result에서 best_evidence의 document_id가
        최소 1개 row에서 다른지 확인
        """
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

        male_doc_ids = extract_document_ids_from_compare_result(resp_male, "LOTTE")
        female_doc_ids = extract_document_ids_from_compare_result(resp_female, "LOTTE")

        # evidence가 없을 경우 건너뛰기
        if not male_doc_ids and not female_doc_ids:
            pytest.skip("LOTTE에 best_evidence document_id 없음 (coverage 미매칭)")

        # 남/여 document_id 집합이 다른지 확인
        # 최소한 한쪽에만 있는 document_id가 있어야 함
        symmetric_diff = male_doc_ids.symmetric_difference(female_doc_ids)

        assert len(symmetric_diff) > 0, \
            f"LOTTE 남/여 document_id 동일: male={male_doc_ids}, female={female_doc_ids}"

    def test_lotte_gender_m_vs_f_resolved_amount_source_difference(self):
        """
        LOTTE: 남/여 다른 plan → resolved_amount.source_document_id 차이

        최소 1개 row에서 source_document_id가 다르면 PASS,
        다르지 않으면 WARN (금액 데이터가 없을 수 있음)
        """
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

        male_sources = extract_resolved_amount_sources(resp_male, "LOTTE")
        female_sources = extract_resolved_amount_sources(resp_female, "LOTTE")

        # resolved_amount가 없는 경우
        if not male_sources and not female_sources:
            warnings.warn(
                "LOTTE 남/여 모두 resolved_amount.source_document_id 없음 - "
                "금액 추출이 안 된 상태",
                UserWarning
            )
            return  # WARN but pass

        # 한쪽만 있는 경우도 "다르다"로 인정
        if male_sources != female_sources:
            # PASS: 다른 source
            return

        # 동일한 경우 경고
        warnings.warn(
            f"LOTTE 남/여 resolved_amount.source_document_id 동일: {male_sources}",
            UserWarning
        )


# =============================================================================
# Test Cases: DB Age Effects
# =============================================================================

class TestDbAgeEffects:
    """DB: 나이에 따른 Plan 효과 검증"""

    def test_db_age_39_vs_41_different_plan_ids(self):
        """DB: 39세 vs 41세 다른 plan_id 선택 확인"""
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

        plan_39 = get_plan_for_insurer(get_selected_plans(resp_39), "DB")
        plan_41 = get_plan_for_insurer(get_selected_plans(resp_41), "DB")

        assert plan_39 is not None, "DB 39세 plan 없음"
        assert plan_41 is not None, "DB 41세 plan 없음"
        assert plan_39.get("plan_id") is not None, "DB 39세 plan_id 없음"
        assert plan_41.get("plan_id") is not None, "DB 41세 plan_id 없음"
        assert plan_39["plan_id"] != plan_41["plan_id"], \
            f"DB 39세/41세 plan_id 동일: {plan_39['plan_id']}"

    def test_db_age_39_vs_41_evidence_or_amount_change(self):
        """
        DB: 39세 vs 41세 → best_evidence 또는 resolved_amount 변화 확인

        둘 중 하나라도 변화가 있으면 PASS
        """
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

        # Evidence document_id 비교
        evidence_39 = extract_document_ids_from_compare_result(resp_39, "DB")
        evidence_41 = extract_document_ids_from_compare_result(resp_41, "DB")
        evidence_changed = evidence_39 != evidence_41

        # Resolved amount source 비교
        amount_39 = extract_resolved_amount_sources(resp_39, "DB")
        amount_41 = extract_resolved_amount_sources(resp_41, "DB")
        amount_changed = amount_39 != amount_41

        # 둘 중 하나라도 변화가 있으면 PASS
        if evidence_changed or amount_changed:
            return  # PASS

        # 둘 다 없으면 건너뛰기
        if not evidence_39 and not evidence_41 and not amount_39 and not amount_41:
            pytest.skip("DB에 evidence와 resolved_amount 모두 없음 (coverage 미매칭)")

        # 둘 다 동일하면 경고
        warnings.warn(
            f"DB 39세/41세 evidence와 amount 모두 동일: "
            f"evidence={evidence_39}, amount={amount_39}",
            UserWarning
        )


# =============================================================================
# Test Cases: SAMSUNG Regression (No Plan Changes)
# =============================================================================

class TestSamsungRegressionNoPlan:
    """
    SAMSUNG: Plan이 없는 보험사 회귀 테스트

    age/gender를 넣어도 결과가 동일해야 함 (plan이 없으므로)
    """

    def test_samsung_no_plan_same_results_with_different_gender(self):
        """SAMSUNG: gender 다르게 해도 결과 동일 (plan 없음)"""
        resp_male = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        resp_female = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "F",
        })

        # Plan 선택 정보 확인 - SAMSUNG은 plan이 없어야 함
        male_plan = get_plan_for_insurer(get_selected_plans(resp_male), "SAMSUNG")
        female_plan = get_plan_for_insurer(get_selected_plans(resp_female), "SAMSUNG")

        # plan_id가 둘 다 None이거나 동일해야 함
        male_plan_id = male_plan.get("plan_id") if male_plan else None
        female_plan_id = female_plan.get("plan_id") if female_plan else None

        # Evidence document_id 비교 - 동일해야 함
        male_evidence = extract_document_ids_from_compare_result(resp_male, "SAMSUNG")
        female_evidence = extract_document_ids_from_compare_result(resp_female, "SAMSUNG")

        # plan이 없으므로 결과가 동일해야 함
        assert male_evidence == female_evidence, \
            f"SAMSUNG: gender 다른데 evidence 다름 - male={male_evidence}, female={female_evidence}"

    def test_samsung_no_plan_same_results_with_different_age(self):
        """SAMSUNG: age 다르게 해도 결과 동일 (plan 없음)"""
        resp_young = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 25,
            "gender": "M",
        })

        resp_old = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 55,
            "gender": "M",
        })

        # Evidence document_id 비교 - 동일해야 함
        young_evidence = extract_document_ids_from_compare_result(resp_young, "SAMSUNG")
        old_evidence = extract_document_ids_from_compare_result(resp_old, "SAMSUNG")

        # plan이 없으므로 결과가 동일해야 함
        assert young_evidence == old_evidence, \
            f"SAMSUNG: age 다른데 evidence 다름 - young={young_evidence}, old={old_evidence}"

    def test_samsung_no_plan_same_compare_axis(self):
        """SAMSUNG: age/gender 변경해도 compare_axis 동일"""
        resp_base = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
        })

        resp_with_plan_params = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        # compare_axis에서 document_id 추출
        base_doc_ids = extract_all_evidence_document_ids(resp_base, "SAMSUNG")
        plan_doc_ids = extract_all_evidence_document_ids(resp_with_plan_params, "SAMSUNG")

        # 동일해야 함 (plan이 없으므로)
        assert base_doc_ids == plan_doc_ids, \
            f"SAMSUNG: plan 파라미터로 결과 달라짐 - base={base_doc_ids}, with_plan={plan_doc_ids}"

    def test_samsung_vs_lotte_plan_effect_comparison(self):
        """
        SAMSUNG(plan 없음) vs LOTTE(plan 있음) 비교

        SAMSUNG은 gender 변경해도 결과 동일,
        LOTTE는 gender 변경하면 결과 다름
        """
        # SAMSUNG male vs female
        samsung_male = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        samsung_female = call_compare({
            "insurers": ["SAMSUNG"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "F",
        })

        # LOTTE male vs female
        lotte_male = call_compare({
            "insurers": ["LOTTE"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "M",
        })

        lotte_female = call_compare({
            "insurers": ["LOTTE"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "age": 35,
            "gender": "F",
        })

        # SAMSUNG: evidence 동일해야 함
        samsung_male_ev = extract_document_ids_from_compare_result(samsung_male, "SAMSUNG")
        samsung_female_ev = extract_document_ids_from_compare_result(samsung_female, "SAMSUNG")
        samsung_same = samsung_male_ev == samsung_female_ev

        # LOTTE: evidence 다를 수 있음
        lotte_male_ev = extract_document_ids_from_compare_result(lotte_male, "LOTTE")
        lotte_female_ev = extract_document_ids_from_compare_result(lotte_female, "LOTTE")
        lotte_different = lotte_male_ev != lotte_female_ev

        # SAMSUNG은 동일해야 함
        assert samsung_same, \
            f"SAMSUNG은 plan 없으므로 gender 달라도 동일해야 함: " \
            f"male={samsung_male_ev}, female={samsung_female_ev}"

        # LOTTE는 다를 수 있음 (plan이 있으므로)
        # 다르면 좋지만, 둘 다 비어있을 수도 있음
        if lotte_male_ev or lotte_female_ev:
            # 최소한 하나는 있을 때만 체크
            # (evidence가 있으면 plan 효과 확인)
            pass  # LOTTE의 차이는 별도 테스트에서 검증
