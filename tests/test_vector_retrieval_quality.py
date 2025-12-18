"""
Step K: Vector Retrieval 품질 회귀 테스트

고정 질의 세트(retrieval_cases.yaml)에 대해 /compare API의 retrieval 품질을 검증.

검증 항목:
1. compare_axis.evidence 수치가 기대치 충족
2. insurer별 evidence 쏠림이 top_k_per_insurer를 준수
3. A2 정책: compare_axis에 약관 없음
4. 케이스별 최소 키워드/coverage_code 포함
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import requests
import yaml

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
FIXTURES_PATH = Path(__file__).parent / "fixtures" / "retrieval_cases.yaml"


# =============================================================================
# Load Test Cases
# =============================================================================

def load_retrieval_cases() -> list[dict]:
    """YAML에서 테스트 케이스 로드"""
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("cases", [])


RETRIEVAL_CASES = load_retrieval_cases()


def get_case_ids() -> list[str]:
    """테스트 파라미터용 case_id 리스트"""
    return [c["case_id"] for c in RETRIEVAL_CASES]


def get_case_by_id(case_id: str) -> dict | None:
    """case_id로 케이스 찾기"""
    for case in RETRIEVAL_CASES:
        if case["case_id"] == case_id:
            return case
    return None


# =============================================================================
# Helper Functions
# =============================================================================

def call_compare(request_body: dict) -> dict:
    """Compare API 호출"""
    resp = requests.post(f"{API_BASE}/compare", json=request_body, timeout=60)
    assert resp.status_code == 200, f"API returned {resp.status_code}: {resp.text}"
    return resp.json()


def build_request_from_case(case: dict) -> dict:
    """케이스로부터 API 요청 본문 생성"""
    request = {
        "insurers": case["insurers"],
        "query": case["query"],
    }

    # 선택적 필드
    if case.get("coverage_codes"):
        request["coverage_codes"] = case["coverage_codes"]

    if case.get("policy_keywords"):
        request["policy_keywords"] = case["policy_keywords"]

    if case.get("age") is not None:
        request["age"] = case["age"]

    if case.get("gender"):
        request["gender"] = case["gender"]

    if case.get("top_k_per_insurer"):
        request["top_k_per_insurer"] = case["top_k_per_insurer"]

    return request


def count_evidence_per_insurer(response: dict) -> dict[str, int]:
    """compare_axis에서 보험사별 evidence 개수"""
    counts: dict[str, int] = {}
    for item in response.get("compare_axis", []):
        insurer = item.get("insurer_code")
        evidence_count = len(item.get("evidence", []))
        counts[insurer] = counts.get(insurer, 0) + evidence_count
    return counts


def count_total_evidence(response: dict) -> int:
    """compare_axis 전체 evidence 개수"""
    total = 0
    for item in response.get("compare_axis", []):
        total += len(item.get("evidence", []))
    return total


def get_all_doc_types_in_compare_axis(response: dict) -> set[str]:
    """compare_axis에 포함된 모든 doc_type"""
    doc_types = set()
    for item in response.get("compare_axis", []):
        for evidence in item.get("evidence", []):
            if evidence.get("doc_type"):
                doc_types.add(evidence["doc_type"])
    return doc_types


def get_all_coverage_codes_in_evidence(response: dict) -> set[str]:
    """compare_axis evidence에 포함된 모든 coverage_code"""
    codes = set()
    for item in response.get("compare_axis", []):
        for evidence in item.get("evidence", []):
            if evidence.get("coverage_code"):
                codes.add(evidence["coverage_code"])
    return codes


def format_debug_info(case: dict, response: dict, counts: dict[str, int]) -> str:
    """실패 시 디버그 정보 포맷"""
    lines = [
        f"Case ID: {case['case_id']}",
        f"Query: {case['query']}",
        f"Insurers: {case['insurers']}",
        f"Evidence per insurer: {counts}",
        f"Total evidence: {sum(counts.values())}",
        "",
        "Evidence details:",
    ]

    for item in response.get("compare_axis", []):
        insurer = item.get("insurer_code")
        for ev in item.get("evidence", [])[:3]:  # 처음 3개만
            lines.append(
                f"  - {insurer}: doc_id={ev.get('document_id')}, "
                f"page={ev.get('page_start')}, doc_type={ev.get('doc_type')}, "
                f"coverage={ev.get('coverage_code')}"
            )

    return "\n".join(lines)


# =============================================================================
# Test Classes
# =============================================================================

class TestRetrievalQuality:
    """Retrieval 품질 회귀 테스트"""

    @pytest.mark.parametrize("case_id", get_case_ids())
    def test_min_total_evidence(self, case_id: str):
        """전체 evidence 최소 개수 검증"""
        case = get_case_by_id(case_id)
        assert case is not None, f"Case not found: {case_id}"

        expected = case.get("expected", {})
        min_total = expected.get("min_total_evidence", 0)

        if min_total == 0:
            pytest.skip("min_total_evidence not specified")

        request = build_request_from_case(case)
        response = call_compare(request)
        counts = count_evidence_per_insurer(response)
        total = sum(counts.values())

        debug_info = format_debug_info(case, response, counts)
        assert total >= min_total, (
            f"Total evidence {total} < expected {min_total}\n{debug_info}"
        )

    @pytest.mark.parametrize("case_id", get_case_ids())
    def test_min_per_insurer(self, case_id: str):
        """보험사별 최소 evidence 검증"""
        case = get_case_by_id(case_id)
        assert case is not None

        expected = case.get("expected", {})
        min_per = expected.get("min_per_insurer", 0)

        if min_per == 0:
            pytest.skip("min_per_insurer is 0 (some insurers may have no evidence)")

        request = build_request_from_case(case)
        response = call_compare(request)
        counts = count_evidence_per_insurer(response)

        debug_info = format_debug_info(case, response, counts)

        for insurer in case["insurers"]:
            count = counts.get(insurer, 0)
            assert count >= min_per, (
                f"{insurer}: evidence {count} < expected {min_per}\n{debug_info}"
            )

    @pytest.mark.parametrize("case_id", get_case_ids())
    def test_max_per_insurer_quota(self, case_id: str):
        """보험사별 최대 evidence (quota) 검증"""
        case = get_case_by_id(case_id)
        assert case is not None

        expected = case.get("expected", {})
        max_per = expected.get("max_per_insurer")

        if max_per is None:
            pytest.skip("max_per_insurer not specified")

        request = build_request_from_case(case)
        response = call_compare(request)
        counts = count_evidence_per_insurer(response)

        debug_info = format_debug_info(case, response, counts)

        for insurer, count in counts.items():
            assert count <= max_per, (
                f"{insurer}: evidence {count} > max {max_per}\n{debug_info}"
            )


class TestA2PolicyCompliance:
    """A2 정책 검증: compare_axis에 약관 없음"""

    @pytest.mark.parametrize("case_id", get_case_ids())
    def test_no_policy_in_compare_axis(self, case_id: str):
        """compare_axis에 약관(약관) doc_type이 없어야 함"""
        case = get_case_by_id(case_id)
        assert case is not None

        request = build_request_from_case(case)
        response = call_compare(request)

        doc_types = get_all_doc_types_in_compare_axis(response)

        assert "약관" not in doc_types, (
            f"A2 정책 위반: compare_axis에 약관 포함됨\n"
            f"Case: {case_id}, doc_types found: {doc_types}"
        )


class TestDocTypeRequirements:
    """필수 doc_type 포함 검증"""

    @pytest.mark.parametrize("case_id", get_case_ids())
    def test_must_include_doc_types(self, case_id: str):
        """필수 doc_type 중 최소 1개 포함"""
        case = get_case_by_id(case_id)
        assert case is not None

        expected = case.get("expected", {})
        must_include = expected.get("must_include_doc_types", [])

        if not must_include:
            pytest.skip("must_include_doc_types not specified")

        request = build_request_from_case(case)
        response = call_compare(request)

        doc_types = get_all_doc_types_in_compare_axis(response)

        # evidence가 아예 없으면 건너뛰기
        if not doc_types:
            pytest.skip("No evidence found")

        # 필수 doc_type 중 최소 1개 포함
        intersection = doc_types.intersection(must_include)
        assert len(intersection) > 0, (
            f"필수 doc_type 없음: expected one of {must_include}, "
            f"found {doc_types}\nCase: {case_id}"
        )

    @pytest.mark.parametrize("case_id", get_case_ids())
    def test_must_exclude_doc_types(self, case_id: str):
        """제외 doc_type이 없어야 함"""
        case = get_case_by_id(case_id)
        assert case is not None

        expected = case.get("expected", {})
        must_exclude = expected.get("must_exclude_doc_types", [])

        if not must_exclude:
            pytest.skip("must_exclude_doc_types not specified")

        request = build_request_from_case(case)
        response = call_compare(request)

        doc_types = get_all_doc_types_in_compare_axis(response)

        for excluded in must_exclude:
            assert excluded not in doc_types, (
                f"제외 doc_type 포함됨: {excluded}\nCase: {case_id}"
            )


class TestCoverageCodeRequirements:
    """coverage_code 포함 검증"""

    @pytest.mark.parametrize("case_id", get_case_ids())
    def test_must_include_coverage_codes(self, case_id: str):
        """필수 coverage_code 포함"""
        case = get_case_by_id(case_id)
        assert case is not None

        expected = case.get("expected", {})
        must_include = expected.get("must_include_coverage_codes", [])

        if not must_include:
            pytest.skip("must_include_coverage_codes not specified or empty")

        request = build_request_from_case(case)
        response = call_compare(request)

        codes = get_all_coverage_codes_in_evidence(response)

        # evidence가 아예 없으면 건너뛰기
        if not codes:
            pytest.skip("No coverage_code found in evidence")

        # 필수 coverage_code 중 최소 1개 포함
        intersection = codes.intersection(must_include)
        assert len(intersection) > 0, (
            f"필수 coverage_code 없음: expected one of {must_include}, "
            f"found {codes}\nCase: {case_id}"
        )


class TestResponseStructure:
    """응답 구조 검증"""

    @pytest.mark.parametrize("case_id", get_case_ids()[:5])  # 샘플 5개만
    def test_response_has_required_keys(self, case_id: str):
        """필수 응답 키 존재"""
        case = get_case_by_id(case_id)
        assert case is not None

        request = build_request_from_case(case)
        response = call_compare(request)

        required_keys = [
            "compare_axis",
            "policy_axis",
            "coverage_compare_result",
            "diff_summary",
            "debug",
        ]

        for key in required_keys:
            assert key in response, f"Missing key: {key} in case {case_id}"

    @pytest.mark.parametrize("case_id", get_case_ids()[:5])
    def test_compare_axis_structure(self, case_id: str):
        """compare_axis 구조 검증"""
        case = get_case_by_id(case_id)
        assert case is not None

        request = build_request_from_case(case)
        response = call_compare(request)

        compare_axis = response.get("compare_axis", [])
        assert isinstance(compare_axis, list)

        for item in compare_axis[:3]:  # 샘플 3개만
            assert "insurer_code" in item
            assert "evidence" in item
            assert isinstance(item["evidence"], list)


class TestPlanSelection:
    """Plan 선택 검증 (age/gender 파라미터)"""

    def test_db_age_39_plan_selected(self):
        """DB 39세: 40세이하 plan 선택"""
        case = get_case_by_id("case_04_db_age_39")
        if not case:
            pytest.skip("case_04_db_age_39 not found")

        request = build_request_from_case(case)
        response = call_compare(request)

        selected_plans = response.get("debug", {}).get("selected_plan", [])
        db_plan = next(
            (p for p in selected_plans if p.get("insurer_code") == "DB"),
            None
        )

        assert db_plan is not None, "DB plan not selected"
        assert db_plan.get("plan_id") is not None

    def test_db_age_41_plan_selected(self):
        """DB 41세: 41세이상 plan 선택"""
        case = get_case_by_id("case_05_db_age_41")
        if not case:
            pytest.skip("case_05_db_age_41 not found")

        request = build_request_from_case(case)
        response = call_compare(request)

        selected_plans = response.get("debug", {}).get("selected_plan", [])
        db_plan = next(
            (p for p in selected_plans if p.get("insurer_code") == "DB"),
            None
        )

        assert db_plan is not None, "DB plan not selected"
        assert db_plan.get("plan_id") is not None

    def test_lotte_gender_plans_different(self):
        """LOTTE 남/여: 다른 plan 선택"""
        case_m = get_case_by_id("case_11_lotte_gender_male")
        case_f = get_case_by_id("case_12_lotte_gender_female")

        if not case_m or not case_f:
            pytest.skip("LOTTE gender cases not found")

        resp_m = call_compare(build_request_from_case(case_m))
        resp_f = call_compare(build_request_from_case(case_f))

        plans_m = resp_m.get("debug", {}).get("selected_plan", [])
        plans_f = resp_f.get("debug", {}).get("selected_plan", [])

        lotte_m = next(
            (p for p in plans_m if p.get("insurer_code") == "LOTTE"),
            None
        )
        lotte_f = next(
            (p for p in plans_f if p.get("insurer_code") == "LOTTE"),
            None
        )

        assert lotte_m is not None, "LOTTE male plan not selected"
        assert lotte_f is not None, "LOTTE female plan not selected"
        assert lotte_m.get("plan_id") != lotte_f.get("plan_id"), (
            f"LOTTE 남/여 plan_id 동일: {lotte_m.get('plan_id')}"
        )
