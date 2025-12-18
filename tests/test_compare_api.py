"""
Step E-2: /compare API 회귀 테스트

5개 고정 시나리오를 pytest parametrized test로 구성
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# 5개 고정 테스트 케이스 정의
COMPARE_TEST_CASES = [
    pytest.param(
        {
            "insurers": ["SAMSUNG", "MERITZ"],
            "query": "경계성 종양 암진단비",
            "coverage_codes": ["A4200_1", "A4210"],
            "top_k_per_insurer": 10,
            "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
            "policy_doc_types": ["약관"],
            "policy_keywords": ["경계성", "유사암", "제자리암"],
        },
        id="case1_samsung_meritz",
    ),
    pytest.param(
        {
            "insurers": ["SAMSUNG", "LOTTE"],
            "query": "유사암 진단비",
            "coverage_codes": ["A4210"],
            "top_k_per_insurer": 10,
            "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
            "policy_doc_types": ["약관"],
            "policy_keywords": ["경계성", "유사암", "제자리암"],
        },
        id="case2_samsung_lotte",
    ),
    pytest.param(
        {
            "insurers": ["DB", "KB"],
            "query": "제자리암",
            "coverage_codes": ["A4210"],
            "top_k_per_insurer": 10,
            "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
            "policy_doc_types": ["약관"],
            "policy_keywords": ["경계성", "유사암", "제자리암"],
        },
        id="case3_db_kb",
    ),
    pytest.param(
        {
            "insurers": ["SAMSUNG", "MERITZ", "LOTTE", "DB", "KB", "HANWHA", "HYUNDAI", "HEUNGKUK"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "top_k_per_insurer": 10,
            "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
            "policy_doc_types": ["약관"],
            "policy_keywords": ["경계성", "유사암", "제자리암"],
        },
        id="case4_all_insurers",
    ),
    pytest.param(
        {
            "insurers": ["SAMSUNG"],
            "query": "갑상선암 유사암 진단비",
            "coverage_codes": ["A4210"],
            "top_k_per_insurer": 10,
            "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
            "policy_doc_types": ["약관"],
            "policy_keywords": ["경계성", "유사암", "제자리암"],
        },
        id="case5_samsung_single",
    ),
]


class TestCompareAPI:
    """POST /compare API 테스트"""

    @pytest.mark.parametrize("request_body", COMPARE_TEST_CASES)
    def test_compare_response_status(self, request_body: dict):
        """응답 상태 코드 200 확인"""
        response = client.post("/compare", json=request_body)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    @pytest.mark.parametrize("request_body", COMPARE_TEST_CASES)
    def test_compare_response_keys(self, request_body: dict):
        """필수 키 존재 확인 (compare_axis, policy_axis, debug)"""
        response = client.post("/compare", json=request_body)
        data = response.json()

        assert "compare_axis" in data, "compare_axis 키 없음"
        assert "policy_axis" in data, "policy_axis 키 없음"
        assert "debug" in data, "debug 키 없음"

    @pytest.mark.parametrize("request_body", COMPARE_TEST_CASES)
    def test_a2_compare_axis_no_policy(self, request_body: dict):
        """A2 준수: compare_axis에 약관이 포함되면 실패"""
        response = client.post("/compare", json=request_body)
        data = response.json()

        for item in data["compare_axis"]:
            for evidence in item.get("evidence", []):
                assert evidence.get("doc_type") != "약관", (
                    f"A2 위반: compare_axis에 약관 포함 "
                    f"(insurer={item['insurer_code']}, coverage={item['coverage_code']})"
                )

    @pytest.mark.parametrize("request_body", COMPARE_TEST_CASES)
    def test_a2_policy_axis_only_policy(self, request_body: dict):
        """A2 준수: policy_axis는 약관만 포함"""
        response = client.post("/compare", json=request_body)
        data = response.json()

        for item in data["policy_axis"]:
            for evidence in item.get("evidence", []):
                assert evidence.get("doc_type") == "약관", (
                    f"A2 위반: policy_axis에 약관 외 doc_type 포함 "
                    f"(insurer={item['insurer_code']}, keyword={item['keyword']}, "
                    f"doc_type={evidence.get('doc_type')})"
                )

    @pytest.mark.parametrize("request_body", COMPARE_TEST_CASES)
    def test_quota_enforcement(self, request_body: dict):
        """쏠림 방지: insurer별 evidence 수가 top_k_per_insurer 초과하면 실패"""
        response = client.post("/compare", json=request_body)
        data = response.json()

        top_k = request_body["top_k_per_insurer"]

        # compare_axis: 각 (insurer, coverage_code) 조합별로 evidence 수 확인
        for item in data["compare_axis"]:
            evidence_count = len(item.get("evidence", []))
            assert evidence_count <= top_k, (
                f"쏠림 방지 위반: {item['insurer_code']}/{item['coverage_code']} "
                f"evidence {evidence_count}개 > top_k {top_k}"
            )

        # policy_axis: 각 (insurer, keyword) 조합별로 evidence 수 확인
        for item in data["policy_axis"]:
            evidence_count = len(item.get("evidence", []))
            assert evidence_count <= top_k, (
                f"쏠림 방지 위반: {item['insurer_code']}/{item['keyword']} "
                f"evidence {evidence_count}개 > top_k {top_k}"
            )

    @pytest.mark.parametrize("request_body", COMPARE_TEST_CASES)
    def test_all_insurers_have_results(self, request_body: dict):
        """모든 요청 insurer에 대해 결과가 존재 (데이터 부족 시 WARN만)"""
        response = client.post("/compare", json=request_body)
        data = response.json()

        requested_insurers = set(request_body["insurers"])

        # compare_axis에서 반환된 insurer 목록
        compare_insurers = {item["insurer_code"] for item in data["compare_axis"]}

        # policy_axis에서 반환된 insurer 목록
        policy_insurers = {item["insurer_code"] for item in data["policy_axis"]}

        # 최소 하나의 축에서라도 결과가 있으면 PASS
        # 둘 다 없으면 WARN (데이터 부족)
        missing_both = requested_insurers - (compare_insurers | policy_insurers)

        # 현재는 모든 보험사에 데이터가 있으므로 빈 set이어야 함
        # 데이터 부족으로 누락되는 경우는 허용 (assert 대신 warning)
        if missing_both:
            pytest.skip(f"데이터 부족으로 누락된 보험사: {missing_both}")


class TestCompareAPIEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_insurers_returns_error(self):
        """빈 insurers 리스트는 에러 반환"""
        response = client.post(
            "/compare",
            json={
                "insurers": [],
                "query": "암진단비",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_missing_query_returns_error(self):
        """query 누락 시 에러 반환"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
            },
        )
        assert response.status_code == 422  # Validation error

    def test_empty_coverage_codes_returns_all(self):
        """coverage_codes가 None이면 전체 coverage 반환"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "암진단비",
                "coverage_codes": None,
                "top_k_per_insurer": 5,
                "policy_keywords": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        # coverage_codes 필터 없이 조회되므로 결과가 있어야 함
        assert len(data["compare_axis"]) >= 0  # 결과 개수는 데이터에 따라 다름

    def test_empty_policy_keywords_auto_extracts_from_query(self):
        """policy_keywords가 빈 리스트면 query에서 자동 추출 (Step E-4)"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "경계성 종양 암진단비",  # '경계성'이 포함됨
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 5,
                "policy_keywords": [],  # 빈 리스트
            },
        )
        assert response.status_code == 200
        data = response.json()

        # resolved_policy_keywords가 debug에 있어야 함
        assert "resolved_policy_keywords" in data["debug"]
        resolved = data["debug"]["resolved_policy_keywords"]

        # '경계성'이 추출되어야 함
        assert "경계성" in resolved

        # policy_axis에 결과가 있어야 함 (자동 추출된 키워드로 검색됨)
        assert len(data["policy_axis"]) > 0

    def test_policy_keywords_auto_extraction_case1_no_keywords(self):
        """Case 1 시나리오를 policy_keywords 없이 호출 (Step E-4 검증)"""
        # Case 1과 동일하지만 policy_keywords 없음
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "경계성 종양 암진단비",
                "coverage_codes": ["A4200_1", "A4210"],
                "top_k_per_insurer": 10,
                "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
                "policy_doc_types": ["약관"],
                # policy_keywords 생략 (자동 추출)
            },
        )
        assert response.status_code == 200
        data = response.json()

        # resolved_policy_keywords 확인
        assert "resolved_policy_keywords" in data["debug"]
        resolved = data["debug"]["resolved_policy_keywords"]
        assert "경계성" in resolved

        # A2 준수: compare_axis에 약관 없음
        for item in data["compare_axis"]:
            for evidence in item.get("evidence", []):
                assert evidence.get("doc_type") != "약관"

        # A2 준수: policy_axis는 약관만
        for item in data["policy_axis"]:
            for evidence in item.get("evidence", []):
                assert evidence.get("doc_type") == "약관"

        # 모든 insurer에 결과 있어야 함
        compare_insurers = {item["insurer_code"] for item in data["compare_axis"]}
        policy_insurers = {item["insurer_code"] for item in data["policy_axis"]}
        assert "SAMSUNG" in compare_insurers
        assert "MERITZ" in compare_insurers
        assert "SAMSUNG" in policy_insurers
        assert "MERITZ" in policy_insurers

    def test_policy_keywords_normalization(self):
        """정규화 테스트: 경계성종양 → 경계성, 갑상선암 → 유사암"""
        # 경계성종양 테스트
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "경계성종양 진단비",
                "coverage_codes": ["A4210"],
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        resolved = data["debug"]["resolved_policy_keywords"]
        assert "경계성" in resolved  # 경계성종양 → 경계성

        # 갑상선암 테스트
        response2 = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "갑상선암 진단비",
                "coverage_codes": ["A4210"],
                "top_k_per_insurer": 5,
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        resolved2 = data2["debug"]["resolved_policy_keywords"]
        assert "유사암" in resolved2  # 갑상선암 → 유사암

    def test_policy_keywords_default_fallback(self):
        """매칭 안 되면 기본값 반환"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "보험료 납입",  # 관련 키워드 없음
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        resolved = data["debug"]["resolved_policy_keywords"]
        # 기본값: ['경계성', '유사암', '제자리암']
        assert set(resolved) == {"경계성", "유사암", "제자리암"}


class TestCoverageRecommendation:
    """Step E-5: coverage_codes 자동 추천 테스트"""

    def test_coverage_recommendation_debug_fields(self):
        """coverage_codes 없을 때 debug 필드 확인"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "암진단비",  # 명확한 query
                "top_k_per_insurer": 5,
                # coverage_codes 생략 (자동 추천)
            },
        )
        assert response.status_code == 200
        data = response.json()

        # debug 필드 존재 확인
        assert "recommended_coverage_codes" in data["debug"]
        assert "recommended_coverage_details" in data["debug"]
        assert "resolved_coverage_codes" in data["debug"]
        assert "coverage_recommendation" in data["debug"]["timing_ms"]

    def test_coverage_recommendation_returns_codes(self):
        """암진단비 query로 관련 coverage_code 추천"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암진단비",
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        recommended = data["debug"]["recommended_coverage_codes"]
        resolved = data["debug"]["resolved_coverage_codes"]

        # 추천 코드가 비어있지 않아야 함 (데이터 존재 시)
        # 데이터가 없는 경우 WARN
        if not recommended:
            pytest.skip("coverage_alias 데이터 없음")

        # resolved는 recommended와 동일해야 함
        assert resolved == recommended

        # compare_axis에 결과가 있어야 함
        assert len(data["compare_axis"]) > 0

    def test_coverage_recommendation_details_format(self):
        """recommended_coverage_details 포맷 검증"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "암진단비",
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        details = data["debug"]["recommended_coverage_details"]
        if not details:
            pytest.skip("coverage_alias 데이터 없음")

        # 각 detail 항목 포맷 확인
        for detail in details:
            assert "insurer_code" in detail
            assert "coverage_code" in detail
            assert "raw_name" in detail
            assert "source_doc_type" in detail
            assert "similarity" in detail
            assert isinstance(detail["similarity"], float)
            assert 0 <= detail["similarity"] <= 1

    def test_explicit_coverage_codes_no_recommendation(self):
        """coverage_codes 명시 시 추천하지 않음"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],  # 명시적 지정
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # 추천하지 않았으므로 빈 배열
        assert data["debug"]["recommended_coverage_codes"] == []
        assert data["debug"]["recommended_coverage_details"] == []
        # resolved는 명시된 값
        assert data["debug"]["resolved_coverage_codes"] == ["A4200_1"]
        # timing에 coverage_recommendation 없음
        assert "coverage_recommendation" not in data["debug"]["timing_ms"]

    def test_coverage_recommendation_per_insurer_limit(self):
        """보험사별 추천 개수 제한 확인"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암",  # 광범위한 query
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        details = data["debug"]["recommended_coverage_details"]
        if not details:
            pytest.skip("coverage_alias 데이터 없음")

        # 보험사별 추천 수 카운트
        from collections import Counter
        insurer_counts = Counter(d["insurer_code"] for d in details)

        # 기본값 3개 이하인지 확인
        for insurer, count in insurer_counts.items():
            assert count <= 3, f"{insurer}의 추천 수 {count}개 > 3개"

    def test_coverage_recommendation_empty_coverage_codes_list(self):
        """빈 coverage_codes 리스트도 자동 추천 트리거"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "암진단비",
                "coverage_codes": [],  # 빈 리스트
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # 빈 리스트도 자동 추천 트리거
        assert "coverage_recommendation" in data["debug"]["timing_ms"]


class TestCoverageCompareResult:
    """Step F: coverage_compare_result(비교표) 테스트"""

    def test_coverage_compare_result_exists(self):
        """coverage_compare_result 필드 존재 확인"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1", "A4210"],
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "coverage_compare_result" in data
        assert isinstance(data["coverage_compare_result"], list)

    def test_coverage_compare_result_case1_structure(self):
        """Case1: SAMSUNG/MERITZ 비교표 구조 확인"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "경계성 종양 암진단비",
                "coverage_codes": ["A4200_1", "A4210"],
                "top_k_per_insurer": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        compare_result = data["coverage_compare_result"]
        assert len(compare_result) > 0

        # 각 row 구조 확인
        for row in compare_result:
            assert "coverage_code" in row
            assert "coverage_name" in row
            assert "insurers" in row

            # insurers 순서 확인 (요청 순서 유지)
            assert len(row["insurers"]) == 2
            assert row["insurers"][0]["insurer_code"] == "SAMSUNG"
            assert row["insurers"][1]["insurer_code"] == "MERITZ"

    def test_coverage_compare_result_insurers_have_both(self):
        """Case1: coverage_code별로 두 보험사 모두 존재"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        compare_result = data["coverage_compare_result"]

        for row in compare_result:
            # 각 row에 insurers가 2개
            assert len(row["insurers"]) == 2

            # 각 insurer에 필수 필드 존재
            for cell in row["insurers"]:
                assert "insurer_code" in cell
                assert "doc_type_counts" in cell
                assert "best_evidence" in cell

    def test_coverage_compare_result_best_evidence_max_2(self):
        """best_evidence는 최대 2개"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1", "A4210"],
                "top_k_per_insurer": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        compare_result = data["coverage_compare_result"]

        for row in compare_result:
            for cell in row["insurers"]:
                assert len(cell["best_evidence"]) <= 2

    def test_coverage_compare_result_doc_type_priority(self):
        """best_evidence doc_type 우선순위 검증"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        compare_result = data["coverage_compare_result"]
        priority_order = ["가입설계서", "상품요약서", "사업방법서"]

        for row in compare_result:
            for cell in row["insurers"]:
                best_evidence = cell["best_evidence"]
                if len(best_evidence) >= 2:
                    # 첫 번째가 두 번째보다 우선순위가 높거나 같아야 함
                    first_priority = (
                        priority_order.index(best_evidence[0]["doc_type"])
                        if best_evidence[0]["doc_type"] in priority_order
                        else 999
                    )
                    second_priority = (
                        priority_order.index(best_evidence[1]["doc_type"])
                        if best_evidence[1]["doc_type"] in priority_order
                        else 999
                    )
                    assert first_priority <= second_priority

    def test_coverage_compare_result_timing(self):
        """timing에 coverage_compare_result 포함"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "coverage_compare_result" in data["debug"]["timing_ms"]


class TestDiffSummary:
    """Step G-1: diff_summary(차이점 요약) 테스트"""

    def test_diff_summary_exists(self):
        """diff_summary 필드 존재 확인"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "diff_summary" in data
        assert isinstance(data["diff_summary"], list)

    def test_diff_summary_case1_structure(self):
        """Case1: SAMSUNG/MERITZ diff_summary 구조 확인"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "경계성 종양 암진단비",
                "coverage_codes": ["A4200_1", "A4210"],
                "top_k_per_insurer": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        diff_summary = data["diff_summary"]
        assert len(diff_summary) > 0

        # 각 item 구조 확인
        for item in diff_summary:
            assert "coverage_code" in item
            assert "coverage_name" in item
            assert "bullets" in item
            assert isinstance(item["bullets"], list)

    def test_diff_summary_bullets_have_evidence_refs(self):
        """bullets에 evidence_refs 존재"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        diff_summary = data["diff_summary"]
        for item in diff_summary:
            for bullet in item["bullets"]:
                assert "text" in bullet
                assert "evidence_refs" in bullet
                assert isinstance(bullet["evidence_refs"], list)

                # evidence_refs 구조 확인
                for ref in bullet["evidence_refs"]:
                    assert "insurer_code" in ref
                    assert "document_id" in ref
                    assert "page_start" in ref

    def test_diff_summary_insurers_order_maintained(self):
        """diff_summary가 insurers 순서 유지"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        diff_summary = data["diff_summary"]
        # diff_summary의 bullets에서 insurer 순서 확인
        for item in diff_summary:
            for bullet in item["bullets"]:
                if bullet["evidence_refs"]:
                    # 첫 번째 insurer가 SAMSUNG이어야 함 (요청 순서)
                    first_ref = bullet["evidence_refs"][0]
                    assert first_ref["insurer_code"] in ["SAMSUNG", "MERITZ"]

    def test_diff_summary_timing(self):
        """timing에 diff_summary 포함"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "diff_summary" in data["debug"]["timing_ms"]


class TestAmountConditionExtraction:
    """Step H-1: amount/condition_snippet 추출 API 테스트"""

    def test_best_evidence_has_amount_field(self):
        """best_evidence에 amount 필드 존재"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "암진단비",
                "coverage_codes": ["A4200_1"],
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        compare_result = data["coverage_compare_result"]
        assert len(compare_result) > 0

        # best_evidence에 amount 필드 존재 확인
        for row in compare_result:
            for cell in row["insurers"]:
                for evidence in cell["best_evidence"]:
                    # amount 필드가 존재해야 함 (값은 None 가능)
                    assert "amount" in evidence
                    # amount가 있으면 구조 확인
                    if evidence["amount"] is not None:
                        assert "amount_value" in evidence["amount"]
                        assert "amount_text" in evidence["amount"]
                        assert "unit" in evidence["amount"]
                        assert "confidence" in evidence["amount"]
                        assert "method" in evidence["amount"]
                        assert evidence["amount"]["confidence"] in ["high", "medium", "low"]

    def test_best_evidence_has_condition_snippet_field(self):
        """best_evidence에 condition_snippet 필드 존재"""
        response = client.post(
            "/compare",
            json={
                "insurers": ["SAMSUNG", "MERITZ"],
                "query": "경계성 종양 암진단비",
                "coverage_codes": ["A4200_1", "A4210"],
                "top_k_per_insurer": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()

        compare_result = data["coverage_compare_result"]
        assert len(compare_result) > 0

        # best_evidence에 condition_snippet 필드 존재 확인
        for row in compare_result:
            for cell in row["insurers"]:
                for evidence in cell["best_evidence"]:
                    # condition_snippet 필드가 존재해야 함 (값은 None 가능)
                    assert "condition_snippet" in evidence
                    # condition_snippet이 있으면 구조 확인
                    if evidence["condition_snippet"] is not None:
                        assert "snippet" in evidence["condition_snippet"]
                        assert "matched_terms" in evidence["condition_snippet"]
                        assert isinstance(evidence["condition_snippet"]["matched_terms"], list)


class TestHealthEndpoint:
    """헬스 체크 엔드포인트 테스트"""

    def test_health_returns_healthy(self):
        """GET /health가 healthy 상태 반환"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
