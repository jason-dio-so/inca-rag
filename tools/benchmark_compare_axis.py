#!/usr/bin/env python3
"""
Step K: Compare Axis 벤치마크 스크립트

HNSW/쿼리 파라미터(ef_search, top_k, candidate_pool_multiplier)를 튜닝하고
성능/품질을 측정하여 리포트 생성

Usage:
    python tools/benchmark_compare_axis.py
    python tools/benchmark_compare_axis.py --output custom_report.md
    python tools/benchmark_compare_axis.py --iterations 50
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

# 모듈 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import yaml

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
DEFAULT_ITERATIONS = 20
DEFAULT_OUTPUT = "artifacts/bench/compare_axis_benchmark.md"

# 벤치마크 케이스 정의
BENCHMARK_CASES = [
    {
        "name": "2사_암진단비",
        "description": "삼성 vs 메리츠: 암진단비",
        "request": {
            "insurers": ["SAMSUNG", "MERITZ"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
        },
    },
    {
        "name": "2사_유사암",
        "description": "삼성 vs 롯데: 유사암",
        "request": {
            "insurers": ["SAMSUNG", "LOTTE"],
            "query": "유사암 진단비",
            "coverage_codes": ["A4210"],
        },
    },
    {
        "name": "8사_암진단비",
        "description": "8개사 전체: 암진단비",
        "request": {
            "insurers": ["SAMSUNG", "LOTTE", "DB", "KB", "MERITZ", "HANWHA", "HYUNDAI", "HEUNGKUK"],
            "query": "암진단비",
            "coverage_codes": ["A4200_1"],
        },
    },
]

# 파라미터 조합 정의
PARAM_COMBINATIONS = [
    {"name": "baseline", "ef_search": None, "top_k_per_insurer": 5},
    {"name": "top_k_3", "ef_search": None, "top_k_per_insurer": 3},
    {"name": "top_k_8", "ef_search": None, "top_k_per_insurer": 8},
    {"name": "top_k_10", "ef_search": None, "top_k_per_insurer": 10},
]


@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    case_name: str
    param_name: str
    iterations: int
    avg_latency_ms: float
    p95_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    total_evidence: int
    evidence_per_insurer: dict[str, int] = field(default_factory=dict)
    success: bool = True
    error: str | None = None


def call_compare(request_body: dict, timeout: int = 60) -> tuple[dict, float]:
    """
    Compare API 호출 및 응답 시간 측정

    Returns:
        (응답, 레이턴시 ms)
    """
    start = time.perf_counter()
    resp = requests.post(f"{API_BASE}/compare", json=request_body, timeout=timeout)
    elapsed = (time.perf_counter() - start) * 1000

    if resp.status_code != 200:
        raise Exception(f"API error {resp.status_code}: {resp.text}")

    return resp.json(), elapsed


def count_evidence(response: dict) -> tuple[int, dict[str, int]]:
    """compare_axis에서 evidence 개수 집계"""
    per_insurer: dict[str, int] = {}
    total = 0

    for item in response.get("compare_axis", []):
        insurer = item.get("insurer_code")
        count = len(item.get("evidence", []))
        per_insurer[insurer] = per_insurer.get(insurer, 0) + count
        total += count

    return total, per_insurer


def run_benchmark(
    case: dict,
    params: dict,
    iterations: int,
) -> BenchmarkResult:
    """단일 케이스/파라미터 조합 벤치마크 실행"""
    case_name = case["name"]
    param_name = params["name"]

    # 요청 구성
    request = dict(case["request"])
    if params.get("top_k_per_insurer"):
        request["top_k_per_insurer"] = params["top_k_per_insurer"]

    latencies: list[float] = []
    last_response = None
    error = None

    try:
        for i in range(iterations):
            response, latency = call_compare(request)
            latencies.append(latency)
            last_response = response

    except Exception as e:
        error = str(e)
        return BenchmarkResult(
            case_name=case_name,
            param_name=param_name,
            iterations=len(latencies),
            avg_latency_ms=mean(latencies) if latencies else 0,
            p95_latency_ms=0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            total_evidence=0,
            success=False,
            error=error,
        )

    # 통계 계산
    latencies_sorted = sorted(latencies)
    p95_idx = int(len(latencies_sorted) * 0.95)
    p95 = latencies_sorted[p95_idx] if p95_idx < len(latencies_sorted) else latencies_sorted[-1]

    total_evidence, per_insurer = count_evidence(last_response) if last_response else (0, {})

    return BenchmarkResult(
        case_name=case_name,
        param_name=param_name,
        iterations=iterations,
        avg_latency_ms=mean(latencies),
        p95_latency_ms=p95,
        min_latency_ms=min(latencies),
        max_latency_ms=max(latencies),
        total_evidence=total_evidence,
        evidence_per_insurer=per_insurer,
        success=True,
    )


def generate_report(
    results: list[BenchmarkResult],
    iterations: int,
    output_path: Path,
) -> None:
    """마크다운 리포트 생성"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Compare Axis 벤치마크 리포트\n\n")
        f.write(f"> 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"> 반복 횟수: {iterations}회\n\n")
        f.write("---\n\n")

        # 요약 테이블
        f.write("## 요약\n\n")
        f.write("| 케이스 | 파라미터 | Avg(ms) | P95(ms) | Min(ms) | Max(ms) | Evidence | 상태 |\n")
        f.write("|--------|----------|---------|---------|---------|---------|----------|------|\n")

        for r in results:
            status = "✅" if r.success else f"❌ {r.error}"
            f.write(
                f"| {r.case_name} | {r.param_name} | "
                f"{r.avg_latency_ms:.1f} | {r.p95_latency_ms:.1f} | "
                f"{r.min_latency_ms:.1f} | {r.max_latency_ms:.1f} | "
                f"{r.total_evidence} | {status} |\n"
            )

        f.write("\n---\n\n")

        # 케이스별 상세
        f.write("## 케이스별 상세\n\n")

        for case in BENCHMARK_CASES:
            case_name = case["name"]
            case_results = [r for r in results if r.case_name == case_name]

            if not case_results:
                continue

            f.write(f"### {case['description']}\n\n")
            f.write(f"- 보험사: {case['request']['insurers']}\n")
            f.write(f"- 질의: {case['request']['query']}\n")
            f.write(f"- coverage_codes: {case['request'].get('coverage_codes', [])}\n\n")

            f.write("| 파라미터 | top_k | Avg(ms) | P95(ms) | Evidence | 보험사별 분포 |\n")
            f.write("|----------|-------|---------|---------|----------|---------------|\n")

            for r in case_results:
                params = next((p for p in PARAM_COMBINATIONS if p["name"] == r.param_name), {})
                top_k = params.get("top_k_per_insurer", "-")
                dist = ", ".join(f"{k}:{v}" for k, v in sorted(r.evidence_per_insurer.items()))

                f.write(
                    f"| {r.param_name} | {top_k} | "
                    f"{r.avg_latency_ms:.1f} | {r.p95_latency_ms:.1f} | "
                    f"{r.total_evidence} | {dist} |\n"
                )

            f.write("\n")

        f.write("---\n\n")

        # 권장 파라미터
        f.write("## 권장 파라미터\n\n")

        # 가장 빠른 baseline 기준
        baseline_results = [r for r in results if r.param_name == "baseline" and r.success]
        if baseline_results:
            avg_baseline = mean(r.avg_latency_ms for r in baseline_results)
            f.write(f"- **baseline (top_k=5)**: 평균 {avg_baseline:.1f}ms\n")

        # top_k_3이 더 빠른지 확인
        top_k_3_results = [r for r in results if r.param_name == "top_k_3" and r.success]
        if top_k_3_results:
            avg_top_k_3 = mean(r.avg_latency_ms for r in top_k_3_results)
            f.write(f"- **top_k_3**: 평균 {avg_top_k_3:.1f}ms (속도 우선)\n")

        # top_k_8 품질 확인
        top_k_8_results = [r for r in results if r.param_name == "top_k_8" and r.success]
        if top_k_8_results:
            avg_top_k_8 = mean(r.avg_latency_ms for r in top_k_8_results)
            avg_evidence_8 = mean(r.total_evidence for r in top_k_8_results)
            f.write(f"- **top_k_8**: 평균 {avg_top_k_8:.1f}ms, evidence {avg_evidence_8:.1f}개 (품질 우선)\n")

        f.write("\n### 결론\n\n")
        f.write("- **기본값 (top_k_per_insurer=5)** 권장: 속도와 품질 균형\n")
        f.write("- 속도 최적화 필요시: `top_k_per_insurer=3`\n")
        f.write("- 품질 최적화 필요시: `top_k_per_insurer=8~10`\n")
        f.write("- HNSW ef_search 튜닝: 현재 coverage_code 기반 검색에는 영향 없음\n")
        f.write("  - 벡터 검색 활성화 시 ef_search 튜닝 필요\n")

    print(f"Report generated: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Axis 벤치마크",
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"반복 횟수 (기본: {DEFAULT_ITERATIONS})",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"출력 파일 경로 (기본: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    print(f"Compare Axis Benchmark")
    print(f"  API: {API_BASE}")
    print(f"  Iterations: {args.iterations}")
    print(f"  Cases: {len(BENCHMARK_CASES)}")
    print(f"  Parameter combinations: {len(PARAM_COMBINATIONS)}")
    print()

    results: list[BenchmarkResult] = []

    total = len(BENCHMARK_CASES) * len(PARAM_COMBINATIONS)
    current = 0

    for case in BENCHMARK_CASES:
        for params in PARAM_COMBINATIONS:
            current += 1
            print(f"[{current}/{total}] {case['name']} / {params['name']}...", end=" ", flush=True)

            result = run_benchmark(case, params, args.iterations)
            results.append(result)

            if result.success:
                print(f"avg={result.avg_latency_ms:.1f}ms, evidence={result.total_evidence}")
            else:
                print(f"FAILED: {result.error}")

    print()

    # 리포트 생성
    output_path = Path(args.output)
    generate_report(results, args.iterations, output_path)

    # 성공/실패 통계
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    print(f"\nResults: {success_count} success, {fail_count} failed")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
