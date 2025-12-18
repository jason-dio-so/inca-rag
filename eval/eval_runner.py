#!/usr/bin/env python3
"""
Eval Runner for INCA-RAG

Validates compare API results against a goldset of expected values.

Usage:
    python eval/eval_runner.py
    python eval/eval_runner.py --goldset eval/goldset_cancer_minimal.csv
    python eval/eval_runner.py --api-base http://localhost:8000
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


DEFAULT_GOLDSET = "eval/goldset_cancer_minimal.csv"
DEFAULT_API_BASE = "http://localhost:8000"


def normalize_value(value: str | None) -> str:
    """Normalize value for comparison (remove commas, spaces, etc.)."""
    if value is None:
        return ""
    # Remove commas, spaces, and normalize
    normalized = re.sub(r"[,\s]", "", str(value))
    return normalized.lower()


def load_goldset(goldset_path: str) -> list[dict]:
    """Load goldset CSV file."""
    rows = []
    with open(goldset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def call_compare_api(
    api_base: str,
    query: str,
    insurers: list[str],
) -> dict[str, Any] | None:
    """Call the compare API and return response.

    Note: coverage_codes are NOT passed explicitly.
    The API auto-infers them from the query.
    """
    url = f"{api_base}/compare"
    payload = {
        "query": query,
        "insurers": insurers,
    }

    try:
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def extract_slot_value(
    response: dict,
    insurer_code: str,
    slot_key: str,
) -> tuple[str | None, str | None]:
    """Extract slot value and doc_type from API response.

    Returns (value, doc_type) tuple.
    """
    slots = response.get("slots", [])
    for slot in slots:
        if slot.get("slot_key") != slot_key:
            continue
        for iv in slot.get("insurers", []):
            if iv.get("insurer_code") != insurer_code:
                continue
            value = iv.get("value")
            confidence = iv.get("confidence", "")

            # Not found case
            if confidence == "not_found" or value is None:
                return None, None

            # Get doc_type from first evidence ref if available
            doc_type = None
            evidence_refs = iv.get("evidence_refs", [])
            if evidence_refs:
                # Try to get doc_type from evidence
                # (This assumes doc_type is available in response - may need adjustment)
                doc_type = evidence_refs[0].get("doc_type")

            return value, doc_type

    return None, None


def check_coverage_code_resolved(response: dict, expected_code: str) -> bool:
    """Check if expected coverage_code is in resolved_coverage_codes."""
    # resolved_coverage_codes is in debug field
    debug = response.get("debug") or {}
    resolved = debug.get("resolved_coverage_codes") or []
    return expected_code in resolved


def run_eval(goldset_path: str, api_base: str) -> dict:
    """Run evaluation against goldset.

    Returns summary statistics.
    """
    goldset = load_goldset(goldset_path)

    # Group by query to batch API calls (coverage_codes are auto-inferred)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in goldset:
        grouped[row["query"]].append(row)

    results = []
    api_cache: dict[str, dict] = {}

    print("\n" + "=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)
    print(f"\n{'Query':<25} {'Insurer':<10} {'Slot':<20} {'Expected':<15} {'Actual':<15} {'Match':<6}")
    print("-" * 80)

    for query, rows in grouped.items():
        # Get unique insurers for this group
        insurers = list(set(row["insurer"] for row in rows))

        # Create cache key
        cache_key = f"{query}|{','.join(sorted(insurers))}"

        # Call API (with caching) - coverage_codes are auto-inferred from query
        if cache_key not in api_cache:
            response = call_compare_api(api_base, query, insurers)
            api_cache[cache_key] = response or {}

        response = api_cache[cache_key]

        for row in rows:
            insurer = row["insurer"]
            slot_key = row["slot_key"]
            expected_value = row["expected_value"]
            expected_doc_type = row.get("expected_doc_type", "").strip()
            expected_coverage_code = row.get("coverage_code", "").strip()

            # Check if expected coverage_code was resolved
            coverage_code_resolved = check_coverage_code_resolved(response, expected_coverage_code)

            # Extract actual value
            actual_value, actual_doc_type = extract_slot_value(response, insurer, slot_key)

            # Check slot filled
            slot_filled = actual_value is not None

            # Check value match (normalized comparison)
            value_match = normalize_value(expected_value) == normalize_value(actual_value)

            # Check doc_type match (only if expected_doc_type is specified)
            doc_type_match = None
            if expected_doc_type:
                doc_type_match = actual_doc_type == expected_doc_type if actual_doc_type else False

            result = {
                "query": query,
                "insurer": insurer,
                "coverage_code": expected_coverage_code,
                "coverage_code_resolved": coverage_code_resolved,
                "slot_key": slot_key,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "slot_filled": slot_filled,
                "value_match": value_match,
                "expected_doc_type": expected_doc_type,
                "actual_doc_type": actual_doc_type,
                "doc_type_match": doc_type_match,
            }
            results.append(result)

            # Print row
            match_str = "Y" if value_match else "N"
            actual_str = str(actual_value)[:13] if actual_value else "-"
            expected_str = str(expected_value)[:13]
            query_str = query[:23]

            print(f"{query_str:<25} {insurer:<10} {slot_key:<20} {expected_str:<15} {actual_str:<15} {match_str:<6}")

    return calculate_summary(results)


def calculate_summary(results: list[dict]) -> dict:
    """Calculate summary statistics from results."""
    total = len(results)

    slot_filled_count = sum(1 for r in results if r["slot_filled"])
    value_correct_count = sum(1 for r in results if r["value_match"])
    coverage_resolved_count = sum(1 for r in results if r["coverage_code_resolved"])

    # Doc type match (only for rows with expected_doc_type)
    doc_type_cases = [r for r in results if r["expected_doc_type"]]
    doc_type_match_count = sum(1 for r in doc_type_cases if r["doc_type_match"])

    summary = {
        "total_cases": total,
        "slot_fill_rate": slot_filled_count / total * 100 if total > 0 else 0,
        "value_correct_rate": value_correct_count / total * 100 if total > 0 else 0,
        "coverage_resolve_rate": coverage_resolved_count / total * 100 if total > 0 else 0,
        "slot_filled_count": slot_filled_count,
        "value_correct_count": value_correct_count,
        "coverage_resolved_count": coverage_resolved_count,
        "doc_type_cases": len(doc_type_cases),
        "doc_type_match_count": doc_type_match_count,
        "doc_type_match_rate": doc_type_match_count / len(doc_type_cases) * 100 if doc_type_cases else None,
    }

    return summary


def print_summary(summary: dict) -> None:
    """Print evaluation summary."""
    print("\n" + "=" * 80)
    print("[Eval Summary]")
    print("=" * 80)

    print(f"- Total cases: {summary['total_cases']}")
    print(f"- Coverage resolve rate: {summary['coverage_resolve_rate']:.1f}% ({summary['coverage_resolved_count']}/{summary['total_cases']})")
    print(f"- Slot fill rate: {summary['slot_fill_rate']:.1f}% ({summary['slot_filled_count']}/{summary['total_cases']})")
    print(f"- Value correctness: {summary['value_correct_rate']:.1f}% ({summary['value_correct_count']}/{summary['total_cases']})")

    if summary["doc_type_cases"] > 0:
        rate = summary["doc_type_match_rate"]
        count = summary["doc_type_match_count"]
        total = summary["doc_type_cases"]
        print(f"- Evidence match: {rate:.1f}% ({count}/{total})")

    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run eval against goldset")
    parser.add_argument(
        "--goldset",
        default=DEFAULT_GOLDSET,
        help=f"Path to goldset CSV (default: {DEFAULT_GOLDSET})"
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"API base URL (default: {DEFAULT_API_BASE})"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results"
    )
    args = parser.parse_args()

    # Resolve goldset path
    goldset_path = Path(args.goldset)
    if not goldset_path.is_absolute():
        # Try relative to current directory
        if not goldset_path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent
            goldset_path = project_root / args.goldset

    if not goldset_path.exists():
        print(f"Error: Goldset file not found: {goldset_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("INCA-RAG EVAL RUNNER")
    print("=" * 80)
    print(f"\nGoldset: {goldset_path}")
    print(f"API Base: {args.api_base}")

    summary = run_eval(str(goldset_path), args.api_base)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_summary(summary)

    # Exit with error if value correctness is not 100%
    if summary["value_correct_rate"] < 100:
        sys.exit(1)


if __name__ == "__main__":
    main()
