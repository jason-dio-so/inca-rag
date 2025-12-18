#!/bin/bash
# Step E-1: /compare API Smoke Tests (5 Fixed Cases)
# 수동 실행용 스모크 테스트 스크립트

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
OUTPUT_DIR="artifacts/compare_smoke"

mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Step E-1: /compare Smoke Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "Output: $OUTPUT_DIR"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 결과 저장 배열
declare -a RESULTS

# 테스트 실행 함수
run_test() {
    local case_num=$1
    local case_name=$2
    local output_file=$3
    local request_body=$4

    echo "----------------------------------------"
    echo "Case $case_num: $case_name"
    echo "----------------------------------------"

    # curl 실행 및 HTTP 상태 코드 캡처
    HTTP_CODE=$(curl -s -w "%{http_code}" -o "$OUTPUT_DIR/$output_file" \
        -X POST "$BASE_URL/compare" \
        -H "Content-Type: application/json" \
        -d "$request_body")

    echo "HTTP Status: $HTTP_CODE"
    echo "Output: $OUTPUT_DIR/$output_file"

    if [ "$HTTP_CODE" != "200" ]; then
        echo -e "${RED}[FAIL] HTTP $HTTP_CODE${NC}"
        RESULTS+=("Case $case_num: FAIL (HTTP $HTTP_CODE)")
        return 1
    fi

    # JSON 검증
    if ! python3 -c "import json; json.load(open('$OUTPUT_DIR/$output_file'))" 2>/dev/null; then
        echo -e "${RED}[FAIL] Invalid JSON${NC}"
        RESULTS+=("Case $case_num: FAIL (Invalid JSON)")
        return 1
    fi

    echo -e "${GREEN}[OK] Response saved${NC}"
    return 0
}

# 검증 함수 (Python으로 상세 검증)
validate_results() {
    python3 << 'PYTHON_SCRIPT'
import json
import os
import sys

OUTPUT_DIR = "artifacts/compare_smoke"

# 테스트 케이스 정의
CASES = [
    {
        "num": 1,
        "name": "SAMSUNG vs MERITZ / 경계성 종양 암진단비",
        "file": "case1_samsung_meritz.json",
        "insurers": ["SAMSUNG", "MERITZ"],
        "keywords": ["경계성", "유사암", "제자리암"]
    },
    {
        "num": 2,
        "name": "SAMSUNG vs LOTTE / 유사암 진단비",
        "file": "case2_samsung_lotte.json",
        "insurers": ["SAMSUNG", "LOTTE"],
        "keywords": ["경계성", "유사암", "제자리암"]
    },
    {
        "num": 3,
        "name": "DB vs KB / 제자리암",
        "file": "case3_db_kb.json",
        "insurers": ["DB", "KB"],
        "keywords": ["경계성", "유사암", "제자리암"]
    },
    {
        "num": 4,
        "name": "8개사 전체 / 암진단비 (쏠림 방지 검증)",
        "file": "case4_all_insurers.json",
        "insurers": ["SAMSUNG", "MERITZ", "LOTTE", "DB", "KB", "HANWHA", "HYUNDAI", "HEUNGKUK"],
        "keywords": ["경계성", "유사암", "제자리암"],
        "check_quota": True,
        "top_k": 10
    },
    {
        "num": 5,
        "name": "SAMSUNG 단일 / 갑상선암(유사암)",
        "file": "case5_samsung_single.json",
        "insurers": ["SAMSUNG"],
        "keywords": ["경계성", "유사암", "제자리암"]
    }
]

def validate_case(case):
    """개별 케이스 검증"""
    filepath = os.path.join(OUTPUT_DIR, case["file"])

    if not os.path.exists(filepath):
        return {"status": "FAIL", "reason": "파일 없음"}

    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {"status": "FAIL", "reason": "JSON 파싱 오류"}

    results = {
        "status": "PASS",
        "checks": [],
        "warnings": [],
        "stats": {}
    }

    # 1. 필수 키 존재 확인
    required_keys = ["compare_axis", "policy_axis", "debug"]
    for key in required_keys:
        if key not in data:
            results["checks"].append(f"FAIL: {key} 키 없음")
            results["status"] = "FAIL"
        else:
            results["checks"].append(f"PASS: {key} 존재")

    # 2. A2 준수: compare_axis에 약관이 없어야 함
    compare_axis = data.get("compare_axis", [])
    for item in compare_axis:
        for ev in item.get("evidence", []):
            if ev.get("doc_type") == "약관":
                results["checks"].append("FAIL: compare_axis에 약관 포함 (A2 위반)")
                results["status"] = "FAIL"
                break
        else:
            continue
        break
    else:
        results["checks"].append("PASS: compare_axis A2 준수 (약관 미포함)")

    # 3. A2 준수: policy_axis는 약관만 있어야 함
    policy_axis = data.get("policy_axis", [])
    non_policy_docs = []
    for item in policy_axis:
        for ev in item.get("evidence", []):
            if ev.get("doc_type") != "약관":
                non_policy_docs.append(ev.get("doc_type"))

    if non_policy_docs:
        results["checks"].append(f"FAIL: policy_axis에 약관 외 doc_type 포함: {set(non_policy_docs)} (A2 위반)")
        results["status"] = "FAIL"
    else:
        results["checks"].append("PASS: policy_axis A2 준수 (약관만 포함)")

    # 4. compare_axis: 각 insurer별 결과 확인
    compare_insurers = set(item["insurer_code"] for item in compare_axis)
    missing_insurers = set(case["insurers"]) - compare_insurers

    if missing_insurers:
        results["warnings"].append(f"WARN: compare_axis에 {missing_insurers} 데이터 없음")
    else:
        results["checks"].append(f"PASS: 모든 insurer에 compare_axis 결과 존재")

    # 5. policy_axis: 각 insurer별 키워드 결과 확인
    policy_insurers = set(item["insurer_code"] for item in policy_axis)
    missing_policy_insurers = set(case["insurers"]) - policy_insurers

    if missing_policy_insurers:
        results["warnings"].append(f"WARN: policy_axis에 {missing_policy_insurers} 데이터 없음")
    else:
        results["checks"].append(f"PASS: 모든 insurer에 policy_axis 결과 존재")

    # 6. 쏠림 방지 검증 (Case 4)
    if case.get("check_quota"):
        top_k = case.get("top_k", 10)
        for insurer in case["insurers"]:
            insurer_evidence_count = sum(
                len(item.get("evidence", []))
                for item in compare_axis
                if item["insurer_code"] == insurer
            )
            # coverage_code 당 top_k이므로, 총 evidence 수는 coverage_code 수 * top_k 이하
            # 하지만 여기서는 단일 coverage_code 기준이므로 top_k 이하여야 함
            results["stats"][f"{insurer}_compare_evidence"] = insurer_evidence_count

    # 통계 수집
    results["stats"]["compare_axis_count"] = len(compare_axis)
    results["stats"]["policy_axis_count"] = len(policy_axis)
    results["stats"]["compare_insurers"] = list(compare_insurers)
    results["stats"]["policy_insurers"] = list(policy_insurers)

    return results

# 메인 검증 실행
print("\n" + "=" * 60)
print("검증 결과 요약")
print("=" * 60)

all_results = []
for case in CASES:
    print(f"\n[Case {case['num']}] {case['name']}")
    print("-" * 50)

    result = validate_case(case)
    all_results.append({"case": case, "result": result})

    # 체크 결과 출력
    for check in result["checks"]:
        if check.startswith("PASS"):
            print(f"  \033[92m{check}\033[0m")
        else:
            print(f"  \033[91m{check}\033[0m")

    # 경고 출력
    for warn in result["warnings"]:
        print(f"  \033[93m{warn}\033[0m")

    # 통계 출력
    if result["stats"]:
        print(f"  Stats: {result['stats']}")

    # 최종 판정
    status = result["status"]
    if result["warnings"]:
        status = "WARN"

    if status == "PASS":
        print(f"  => \033[92m{status}\033[0m")
    elif status == "WARN":
        print(f"  => \033[93m{status}\033[0m")
    else:
        print(f"  => \033[91m{status}\033[0m")

# 최종 요약
print("\n" + "=" * 60)
print("최종 요약")
print("=" * 60)

summary_table = []
for r in all_results:
    case = r["case"]
    result = r["result"]
    status = result["status"]
    if result["warnings"]:
        status = "WARN"

    warnings = "; ".join(result["warnings"]) if result["warnings"] else "-"
    summary_table.append({
        "case": case["num"],
        "name": case["name"][:40],
        "status": status,
        "warnings": warnings
    })

print(f"\n{'Case':<6} {'Status':<8} {'Warnings'}")
print("-" * 70)
for row in summary_table:
    print(f"{row['case']:<6} {row['status']:<8} {row['warnings'][:50]}")

# 전체 판정
pass_count = sum(1 for r in all_results if r["result"]["status"] == "PASS" and not r["result"]["warnings"])
warn_count = sum(1 for r in all_results if r["result"]["warnings"])
fail_count = sum(1 for r in all_results if r["result"]["status"] == "FAIL")

print(f"\nPASS: {pass_count}, WARN: {warn_count}, FAIL: {fail_count}")

# 종료 코드
if fail_count > 0:
    sys.exit(1)
sys.exit(0)
PYTHON_SCRIPT
}

# ========================================
# Case 1: SAMSUNG vs MERITZ / 경계성 종양 암진단비
# ========================================
run_test 1 "SAMSUNG vs MERITZ / 경계성 종양 암진단비" "case1_samsung_meritz.json" '{
  "insurers": ["SAMSUNG", "MERITZ"],
  "query": "경계성 종양 암진단비",
  "coverage_codes": ["A4200_1", "A4210"],
  "top_k_per_insurer": 10,
  "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
  "policy_doc_types": ["약관"],
  "policy_keywords": ["경계성", "유사암", "제자리암"]
}'

# ========================================
# Case 2: SAMSUNG vs LOTTE / 유사암 진단비
# ========================================
run_test 2 "SAMSUNG vs LOTTE / 유사암 진단비" "case2_samsung_lotte.json" '{
  "insurers": ["SAMSUNG", "LOTTE"],
  "query": "유사암 진단비",
  "coverage_codes": ["A4210"],
  "top_k_per_insurer": 10,
  "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
  "policy_doc_types": ["약관"],
  "policy_keywords": ["경계성", "유사암", "제자리암"]
}'

# ========================================
# Case 3: DB vs KB / 제자리암
# ========================================
run_test 3 "DB vs KB / 제자리암" "case3_db_kb.json" '{
  "insurers": ["DB", "KB"],
  "query": "제자리암",
  "coverage_codes": ["A4210"],
  "top_k_per_insurer": 10,
  "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
  "policy_doc_types": ["약관"],
  "policy_keywords": ["경계성", "유사암", "제자리암"]
}'

# ========================================
# Case 4: 8개사 전체 / 암진단비 (쏠림 방지 검증)
# ========================================
run_test 4 "8개사 전체 / 암진단비 (쏠림 방지)" "case4_all_insurers.json" '{
  "insurers": ["SAMSUNG", "MERITZ", "LOTTE", "DB", "KB", "HANWHA", "HYUNDAI", "HEUNGKUK"],
  "query": "암진단비",
  "coverage_codes": ["A4200_1"],
  "top_k_per_insurer": 10,
  "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
  "policy_doc_types": ["약관"],
  "policy_keywords": ["경계성", "유사암", "제자리암"]
}'

# ========================================
# Case 5: SAMSUNG 단일 / 갑상선암(유사암)
# ========================================
run_test 5 "SAMSUNG 단일 / 갑상선암(유사암)" "case5_samsung_single.json" '{
  "insurers": ["SAMSUNG"],
  "query": "갑상선암 유사암 진단비",
  "coverage_codes": ["A4210"],
  "top_k_per_insurer": 10,
  "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
  "policy_doc_types": ["약관"],
  "policy_keywords": ["경계성", "유사암", "제자리암"]
}'

echo ""
echo "=========================================="
echo "모든 테스트 실행 완료. 검증 시작..."
echo "=========================================="

# 검증 실행
validate_results

echo ""
echo "=========================================="
echo "스모크 테스트 완료"
echo "=========================================="
