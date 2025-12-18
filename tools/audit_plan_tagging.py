#!/usr/bin/env python3
"""
Step J-1: Plan 태깅 품질 리포트

8개 보험사 전체에 대해 plan_id 태깅 결과를 정량 리포트로 생성

Usage:
    python tools/audit_plan_tagging.py
    python tools/audit_plan_tagging.py --output artifacts/audit/plan_tagging_report.md
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# 모듈 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


def audit_plan_tagging(db_url: str | None = None) -> dict:
    """
    Plan 태깅 품질 분석

    Returns:
        분석 결과 dict
    """
    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)

    results = {
        "summary": {},
        "by_insurer": {},
        "by_doc_type": {},
        "gender_distribution": {},
        "age_distribution": {},
        "conflicts": [],
    }

    try:
        with conn.cursor() as cur:
            # 1. 전체 요약
            cur.execute("""
                SELECT
                    COUNT(*) as total_docs,
                    COUNT(plan_id) as with_plan,
                    COUNT(*) - COUNT(plan_id) as without_plan
                FROM document
            """)
            row = cur.fetchone()
            results["summary"] = {
                "total_documents": row["total_docs"],
                "with_plan_id": row["with_plan"],
                "without_plan_id": row["without_plan"],
                "plan_rate": round(row["with_plan"] / row["total_docs"] * 100, 1) if row["total_docs"] > 0 else 0,
            }

            # 2. 보험사별 plan_id 분포
            cur.execute("""
                SELECT
                    i.insurer_code,
                    d.doc_type,
                    COUNT(*) as total,
                    COUNT(d.plan_id) as with_plan,
                    COUNT(*) - COUNT(d.plan_id) as without_plan
                FROM document d
                LEFT JOIN insurer i ON d.insurer_id = i.insurer_id
                GROUP BY i.insurer_code, d.doc_type
                ORDER BY i.insurer_code, d.doc_type
            """)
            rows = cur.fetchall()

            by_insurer = defaultdict(lambda: {"total": 0, "with_plan": 0, "by_doc_type": {}})
            for row in rows:
                insurer = row["insurer_code"] or "(NULL)"
                doc_type = row["doc_type"]
                by_insurer[insurer]["total"] += row["total"]
                by_insurer[insurer]["with_plan"] += row["with_plan"]
                by_insurer[insurer]["by_doc_type"][doc_type] = {
                    "total": row["total"],
                    "with_plan": row["with_plan"],
                    "without_plan": row["without_plan"],
                }
            results["by_insurer"] = dict(by_insurer)

            # 3. doc_type별 plan_id 분포
            cur.execute("""
                SELECT
                    doc_type,
                    COUNT(*) as total,
                    COUNT(plan_id) as with_plan,
                    COUNT(*) - COUNT(plan_id) as without_plan
                FROM document
                GROUP BY doc_type
                ORDER BY doc_type
            """)
            rows = cur.fetchall()
            results["by_doc_type"] = {
                row["doc_type"]: {
                    "total": row["total"],
                    "with_plan": row["with_plan"],
                    "without_plan": row["without_plan"],
                    "plan_rate": round(row["with_plan"] / row["total"] * 100, 1) if row["total"] > 0 else 0,
                }
                for row in rows
            }

            # 4. gender별 plan 분포 (product_plan 기준)
            cur.execute("""
                SELECT
                    i.insurer_code,
                    pp.gender,
                    COUNT(DISTINCT d.document_id) as doc_count
                FROM document d
                JOIN product_plan pp ON d.plan_id = pp.plan_id
                JOIN insurer i ON d.insurer_id = i.insurer_id
                GROUP BY i.insurer_code, pp.gender
                ORDER BY i.insurer_code, pp.gender
            """)
            rows = cur.fetchall()

            gender_dist = defaultdict(lambda: {"M": 0, "F": 0, "U": 0})
            for row in rows:
                insurer = row["insurer_code"]
                gender = row["gender"] or "U"
                gender_dist[insurer][gender] = row["doc_count"]
            results["gender_distribution"] = dict(gender_dist)

            # 5. age_range 분포 (product_plan 기준)
            cur.execute("""
                SELECT
                    i.insurer_code,
                    pp.age_min,
                    pp.age_max,
                    COUNT(DISTINCT d.document_id) as doc_count
                FROM document d
                JOIN product_plan pp ON d.plan_id = pp.plan_id
                JOIN insurer i ON d.insurer_id = i.insurer_id
                GROUP BY i.insurer_code, pp.age_min, pp.age_max
                ORDER BY i.insurer_code, pp.age_min NULLS FIRST
            """)
            rows = cur.fetchall()

            age_dist = defaultdict(list)
            for row in rows:
                insurer = row["insurer_code"]
                age_range = f"{row['age_min'] or '*'}-{row['age_max'] or '*'}"
                age_dist[insurer].append({
                    "age_range": age_range,
                    "age_min": row["age_min"],
                    "age_max": row["age_max"],
                    "doc_count": row["doc_count"],
                })
            results["age_distribution"] = dict(age_dist)

            # 6. Plan 충돌 탐지
            # 6-1. 동일 source_path가 서로 다른 plan_id로 태깅된 케이스
            cur.execute("""
                SELECT
                    source_path,
                    ARRAY_AGG(DISTINCT plan_id) as plan_ids
                FROM document
                WHERE plan_id IS NOT NULL
                GROUP BY source_path
                HAVING COUNT(DISTINCT plan_id) > 1
            """)
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    results["conflicts"].append({
                        "type": "duplicate_path_different_plan",
                        "source_path": row["source_path"],
                        "plan_ids": row["plan_ids"],
                    })

            # 6-2. 파일명에 성별 힌트가 있지만 다른 성별 plan에 태깅된 케이스
            cur.execute("""
                SELECT
                    d.document_id,
                    d.source_path,
                    pp.gender as plan_gender,
                    pp.plan_name
                FROM document d
                JOIN product_plan pp ON d.plan_id = pp.plan_id
                WHERE (
                    (d.source_path ILIKE '%남성%' OR d.source_path ILIKE '%_남_%' OR d.source_path ILIKE '%-남-%')
                    AND pp.gender = 'F'
                ) OR (
                    (d.source_path ILIKE '%여성%' OR d.source_path ILIKE '%_여_%' OR d.source_path ILIKE '%-여-%')
                    AND pp.gender = 'M'
                )
            """)
            rows = cur.fetchall()
            for row in rows:
                results["conflicts"].append({
                    "type": "gender_mismatch",
                    "document_id": row["document_id"],
                    "source_path": row["source_path"],
                    "plan_gender": row["plan_gender"],
                    "plan_name": row["plan_name"],
                })

        return results

    finally:
        conn.close()


def generate_report(results: dict) -> str:
    """
    분석 결과를 Markdown 리포트로 생성
    """
    lines = []
    lines.append("# Plan 태깅 품질 리포트")
    lines.append("")
    lines.append(f"> 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 1. 전체 요약
    lines.append("## 1. 전체 요약")
    lines.append("")
    summary = results["summary"]
    lines.append(f"| 지표 | 값 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 전체 문서 수 | {summary['total_documents']} |")
    lines.append(f"| plan_id 있음 | {summary['with_plan_id']} |")
    lines.append(f"| plan_id 없음 | {summary['without_plan_id']} |")
    lines.append(f"| Plan 태깅률 | {summary['plan_rate']}% |")
    lines.append("")

    # 2. 보험사별 분포
    lines.append("## 2. 보험사별 Plan 태깅 분포")
    lines.append("")
    lines.append("| 보험사 | 전체 문서 | plan_id 있음 | 태깅률 |")
    lines.append("|--------|----------|-------------|--------|")
    for insurer, data in sorted(results["by_insurer"].items()):
        total = data["total"]
        with_plan = data["with_plan"]
        rate = round(with_plan / total * 100, 1) if total > 0 else 0
        lines.append(f"| {insurer} | {total} | {with_plan} | {rate}% |")
    lines.append("")

    # 3. doc_type별 분포
    lines.append("## 3. doc_type별 Plan 태깅 분포")
    lines.append("")
    lines.append("| doc_type | 전체 | plan_id 있음 | plan_id 없음 | 태깅률 |")
    lines.append("|----------|------|-------------|-------------|--------|")
    for doc_type, data in sorted(results["by_doc_type"].items()):
        lines.append(f"| {doc_type} | {data['total']} | {data['with_plan']} | {data['without_plan']} | {data['plan_rate']}% |")
    lines.append("")

    # 4. 보험사 × doc_type 상세
    lines.append("## 4. 보험사 × doc_type 상세")
    lines.append("")
    for insurer, data in sorted(results["by_insurer"].items()):
        lines.append(f"### {insurer}")
        lines.append("")
        lines.append("| doc_type | 전체 | plan_id 있음 | plan_id 없음 |")
        lines.append("|----------|------|-------------|-------------|")
        for doc_type, dt_data in sorted(data["by_doc_type"].items()):
            lines.append(f"| {doc_type} | {dt_data['total']} | {dt_data['with_plan']} | {dt_data['without_plan']} |")
        lines.append("")

    # 5. Gender 분포
    lines.append("## 5. 보험사별 Gender 분포 (plan_id 있는 문서)")
    lines.append("")
    if results["gender_distribution"]:
        lines.append("| 보험사 | M(남성) | F(여성) | U(공용) |")
        lines.append("|--------|--------|--------|--------|")
        for insurer, data in sorted(results["gender_distribution"].items()):
            lines.append(f"| {insurer} | {data.get('M', 0)} | {data.get('F', 0)} | {data.get('U', 0)} |")
    else:
        lines.append("*plan_id가 태깅된 문서가 없습니다.*")
    lines.append("")

    # 6. Age 분포
    lines.append("## 6. 보험사별 Age Range 분포 (plan_id 있는 문서)")
    lines.append("")
    if results["age_distribution"]:
        for insurer, ranges in sorted(results["age_distribution"].items()):
            lines.append(f"### {insurer}")
            lines.append("")
            lines.append("| Age Range | 문서 수 |")
            lines.append("|-----------|--------|")
            for r in ranges:
                lines.append(f"| {r['age_range']} | {r['doc_count']} |")
            lines.append("")
    else:
        lines.append("*plan_id가 태깅된 문서가 없습니다.*")
    lines.append("")

    # 7. 충돌 탐지
    lines.append("## 7. Plan 충돌 탐지")
    lines.append("")
    conflicts = results["conflicts"]
    if conflicts:
        lines.append(f"**총 {len(conflicts)}건의 충돌 발견**")
        lines.append("")

        dup_path = [c for c in conflicts if c["type"] == "duplicate_path_different_plan"]
        gender_mismatch = [c for c in conflicts if c["type"] == "gender_mismatch"]

        if dup_path:
            lines.append("### 동일 경로 다른 plan_id")
            lines.append("")
            for c in dup_path:
                lines.append(f"- `{c['source_path']}`: plan_ids={c['plan_ids']}")
            lines.append("")

        if gender_mismatch:
            lines.append("### 성별 불일치")
            lines.append("")
            lines.append("| document_id | source_path | plan_gender | plan_name |")
            lines.append("|-------------|-------------|-------------|-----------|")
            for c in gender_mismatch:
                path = c["source_path"][-50:] if len(c["source_path"]) > 50 else c["source_path"]
                lines.append(f"| {c['document_id']} | ...{path} | {c['plan_gender']} | {c['plan_name']} |")
            lines.append("")
    else:
        lines.append("**충돌 없음** - 모든 태깅이 일관됩니다.")
    lines.append("")

    # 8. 결론
    lines.append("## 8. 결론")
    lines.append("")
    if summary["with_plan_id"] == 0:
        lines.append("- **Plan 태깅 없음**: 현재 plan_id가 태깅된 문서가 없습니다.")
        lines.append("- `tools/backfill_plan_ids.py`를 실행하거나, plan 정보가 포함된 문서를 ingestion해야 합니다.")
    else:
        lines.append(f"- **Plan 태깅률**: {summary['plan_rate']}%")
        if len(conflicts) == 0:
            lines.append("- **충돌 없음**: 모든 태깅이 일관됩니다.")
        else:
            lines.append(f"- **충돌 발견**: {len(conflicts)}건의 충돌이 있습니다. 검토가 필요합니다.")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan 태깅 품질 리포트 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/audit/plan_tagging_report.md",
        help="리포트 출력 경로",
    )

    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (기본: DATABASE_URL 환경변수)",
    )

    parser.add_argument(
        "--print-only",
        action="store_true",
        help="파일 저장 없이 출력만",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Plan 태깅 품질 리포트 생성")
    print("=" * 60)
    print()

    # 분석 실행
    results = audit_plan_tagging(args.db_url)

    # 리포트 생성
    report = generate_report(results)

    if args.print_only:
        print(report)
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"리포트 저장: {output_path}")

    # 요약 출력
    print()
    print("=" * 60)
    print("요약")
    print("=" * 60)
    summary = results["summary"]
    print(f"  전체 문서: {summary['total_documents']}")
    print(f"  plan_id 있음: {summary['with_plan_id']}")
    print(f"  plan_id 없음: {summary['without_plan_id']}")
    print(f"  태깅률: {summary['plan_rate']}%")
    print(f"  충돌: {len(results['conflicts'])}건")

    return 0


if __name__ == "__main__":
    sys.exit(main())
