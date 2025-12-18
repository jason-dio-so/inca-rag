#!/usr/bin/env python3
"""
Slot Completeness Audit for Cancer Coverage Codes

Audits slot extraction quality for cancer diagnosis coverage codes:
- A4200_1: 암진단비(유사암제외)
- A4210: 유사암진단비
- A4209: 암진단비

Usage:
    python tools/audit_slots.py
    python tools/audit_slots.py --api-base http://localhost:8000
    python tools/audit_slots.py --insurers SAMSUNG MERITZ DB
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# Cancer coverage codes to audit
# A4200_1: 암진단비(유사암제외) - standard
# A4210: 유사암진단비
# A4209: 암진단비
# A4299_1: 암진단비(유사암제외) - Samsung variant
CANCER_COVERAGE_CODES = ["A4200_1", "A4210", "A4209", "A4299_1"]

# Default insurers
DEFAULT_INSURERS = ["SAMSUNG", "MERITZ"]


def call_compare_api(
    api_base: str,
    insurers: list[str],
    coverage_codes: list[str],
) -> dict[str, Any] | None:
    """Call the compare API and return response."""
    url = f"{api_base}/compare"
    payload = {
        "query": "암진단비 비교",
        "insurers": insurers,
        "coverage_codes": coverage_codes,
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


def print_slot_details(slots: list[dict], insurers: list[str]) -> dict[str, dict]:
    """Print detailed slot information and return stats."""
    print("\n" + "=" * 80)
    print("SLOT DETAILS")
    print("=" * 80)

    # Header
    print(f"\n{'Insurer':<10} {'Slot Key':<28} {'Value?':<8} {'Refs':<6} {'Method':<8} {'LLM?':<6} {'Reason':<12}")
    print("-" * 80)

    # Stats collection
    stats: dict[str, dict] = {}

    for slot in slots:
        slot_key = slot.get("slot_key", "")
        comparable = slot.get("comparable", False)

        if slot_key not in stats:
            stats[slot_key] = {
                "total": 0,
                "filled": 0,
                "comparable": comparable,
                "label": slot.get("label", slot_key),
            }

        for iv in slot.get("insurers", []):
            insurer_code = iv.get("insurer_code", "")
            value = iv.get("value")
            confidence = iv.get("confidence", "")
            evidence_refs = iv.get("evidence_refs", [])
            trace = iv.get("trace", {}) or {}

            # Value present?
            has_value = value is not None and confidence != "not_found"
            value_str = "Y" if has_value else "N"

            # Trace info
            method = trace.get("method", "-")
            llm_used = "Y" if trace.get("llm_used") else "N"
            reason = trace.get("llm_reason") or "-"

            # Update stats
            stats[slot_key]["total"] += 1
            if has_value:
                stats[slot_key]["filled"] += 1

            print(f"{insurer_code:<10} {slot_key:<28} {value_str:<8} {len(evidence_refs):<6} {method:<8} {llm_used:<6} {reason:<12}")

    return stats


def print_summary(stats: dict[str, dict]) -> None:
    """Print summary statistics."""
    print("\n" + "=" * 80)
    print("SLOT FILL RATE SUMMARY")
    print("=" * 80)

    print(f"\n{'Slot Key':<28} {'Label':<20} {'Comparable':<12} {'Filled':<10} {'Rate':<10}")
    print("-" * 80)

    # Sort by comparable (True first), then by slot_key
    sorted_slots = sorted(
        stats.items(),
        key=lambda x: (not x[1]["comparable"], x[0])
    )

    total_comparable_filled = 0
    total_comparable = 0

    for slot_key, data in sorted_slots:
        total = data["total"]
        filled = data["filled"]
        rate = (filled / total * 100) if total > 0 else 0
        comparable_str = "Yes" if data["comparable"] else "No"
        label = data["label"][:18]

        print(f"{slot_key:<28} {label:<20} {comparable_str:<12} {filled}/{total:<6} {rate:>6.1f}%")

        if data["comparable"]:
            total_comparable_filled += filled
            total_comparable += total

    # Overall comparable rate
    if total_comparable > 0:
        overall_rate = total_comparable_filled / total_comparable * 100
        print("-" * 80)
        print(f"{'OVERALL (comparable only)':<28} {'':<20} {'':<12} {total_comparable_filled}/{total_comparable:<6} {overall_rate:>6.1f}%")


def print_trace_summary(slots: list[dict]) -> None:
    """Print LLM trace summary."""
    print("\n" + "=" * 80)
    print("LLM TRACE SUMMARY")
    print("=" * 80)

    method_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    llm_used_count = 0
    total_traces = 0

    for slot in slots:
        for iv in slot.get("insurers", []):
            trace = iv.get("trace", {}) or {}
            if trace:
                total_traces += 1
                method = trace.get("method", "unknown")
                method_counts[method] = method_counts.get(method, 0) + 1

                if trace.get("llm_used"):
                    llm_used_count += 1

                reason = trace.get("llm_reason")
                if reason:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1

    print(f"\nTotal traces: {total_traces}")
    print(f"LLM used: {llm_used_count} ({llm_used_count/total_traces*100:.1f}%)" if total_traces else "")

    print("\nBy method:")
    for method, count in sorted(method_counts.items()):
        print(f"  {method}: {count}")

    print("\nBy reason:")
    for reason, count in sorted(reason_counts.items()):
        print(f"  {reason}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Audit slot completeness for cancer coverage codes")
    parser.add_argument("--api-base", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--insurers", nargs="+", default=DEFAULT_INSURERS, help="Insurers to audit")
    parser.add_argument("--coverage-codes", nargs="+", default=CANCER_COVERAGE_CODES, help="Coverage codes to audit")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    args = parser.parse_args()

    print("=" * 80)
    print("SLOT COMPLETENESS AUDIT")
    print("=" * 80)
    print(f"\nAPI Base: {args.api_base}")
    print(f"Insurers: {', '.join(args.insurers)}")
    print(f"Coverage Codes: {', '.join(args.coverage_codes)}")

    # Call API
    print("\nCalling compare API...")
    response = call_compare_api(args.api_base, args.insurers, args.coverage_codes)

    if response is None:
        print("\nFailed to get API response.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return

    slots = response.get("slots", [])

    if not slots:
        print("\nNo slots found in response.")
        print("Debug info:")
        print(f"  slots_count: {response.get('debug', {}).get('slots_count', 'N/A')}")
        sys.exit(0)

    print(f"\nFound {len(slots)} slots")

    # Print details and get stats
    stats = print_slot_details(slots, args.insurers)

    # Print summary
    print_summary(stats)

    # Print trace summary
    print_trace_summary(slots)

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
