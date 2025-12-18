#!/usr/bin/env python3
"""
Step E-3: policy_axis 성능 벤치마크

Case 1 (SAMSUNG vs MERITZ)과 Case 4 (8개사 전체)를 5회씩 호출하여
평균/최대 응답 시간을 측정한다.
"""

import json
import statistics
import sys
import time
from typing import Any

import requests

BASE_URL = "http://localhost:8000"

# 테스트 케이스 정의
CASES = {
    "case1": {
        "name": "SAMSUNG vs MERITZ / 경계성 종양 암진단비",
        "request": {
            "insurers": ["SAMSUNG", "MERITZ"],
            "query": "경계성 종양 암진단비",
            "coverage_codes": ["A4200_1", "A4210"],
            "top_k_per_insurer": 10,
            "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
            "policy_doc_types": ["약관"],
            "policy_keywords": ["경계성", "유사암", "제자리암"],
        },
    },
    "case4": {
        "name": "8개사 전체 / 암진단비 (쏠림 방지)",
        "request": {
            "insurers": ["SAMSUNG", "MERITZ", "LOTTE", "DB", "KB", "HANWHA", "HYUNDAI", "HEUNGKUK"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
            "top_k_per_insurer": 10,
            "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
            "policy_doc_types": ["약관"],
            "policy_keywords": ["경계성", "유사암", "제자리암"],
        },
    },
}


def run_benchmark(case_id: str, iterations: int = 5) -> dict[str, Any]:
    """단일 케이스 벤치마크 실행"""
    case = CASES[case_id]
    results = []
    policy_axis_times = []
    compare_axis_times = []

    print(f"\n[{case_id}] {case['name']}")
    print(f"  Running {iterations} iterations...")

    for i in range(iterations):
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/compare",
            json=case["request"],
            timeout=30,
        )
        total_time = (time.time() - start) * 1000  # ms

        if response.status_code != 200:
            print(f"  Iteration {i+1}: ERROR {response.status_code}")
            continue

        data = response.json()
        debug = data.get("debug", {})
        timing = debug.get("timing_ms", {})

        policy_time = timing.get("policy_axis", 0)
        compare_time = timing.get("compare_axis", 0)

        results.append(total_time)
        policy_axis_times.append(policy_time)
        compare_axis_times.append(compare_time)

        print(f"  Iteration {i+1}: total={total_time:.2f}ms, policy={policy_time:.2f}ms, compare={compare_time:.2f}ms")

    return {
        "case_id": case_id,
        "name": case["name"],
        "iterations": iterations,
        "total": {
            "avg": statistics.mean(results) if results else 0,
            "max": max(results) if results else 0,
            "min": min(results) if results else 0,
        },
        "policy_axis": {
            "avg": statistics.mean(policy_axis_times) if policy_axis_times else 0,
            "max": max(policy_axis_times) if policy_axis_times else 0,
            "min": min(policy_axis_times) if policy_axis_times else 0,
        },
        "compare_axis": {
            "avg": statistics.mean(compare_axis_times) if compare_axis_times else 0,
            "max": max(compare_axis_times) if compare_axis_times else 0,
            "min": min(compare_axis_times) if compare_axis_times else 0,
        },
    }


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "before"
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print("=" * 60)
    print(f"policy_axis 벤치마크 ({phase.upper()})")
    print("=" * 60)

    results = {}
    for case_id in ["case1", "case4"]:
        results[case_id] = run_benchmark(case_id, iterations)

    # 요약 출력
    print("\n" + "=" * 60)
    print("요약")
    print("=" * 60)

    print(f"\n{'Case':<10} {'policy_axis avg':<20} {'policy_axis max':<20} {'total avg':<15}")
    print("-" * 65)
    for case_id, r in results.items():
        print(
            f"{case_id:<10} "
            f"{r['policy_axis']['avg']:.2f}ms{'':<12} "
            f"{r['policy_axis']['max']:.2f}ms{'':<12} "
            f"{r['total']['avg']:.2f}ms"
        )

    # JSON 결과 저장
    output_file = f"artifacts/bench/policy_axis_{phase}.json"
    with open(output_file, "w") as f:
        json.dump({"phase": phase, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"\n결과 저장: {output_file}")

    return results


if __name__ == "__main__":
    main()
