#!/usr/bin/env python3
"""
Step J-3: Audit Unassigned Plans

plan_id가 NULL인 문서들의 원인을 분류하여 리포트 생성

Usage:
    python tools/audit_unassigned_plans.py --insurer DB
    python tools/audit_unassigned_plans.py --insurer LOTTE
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# 모듈 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from psycopg.rows import dict_row

from services.ingestion.manifest import load_manifest
from services.ingestion.plan_detector import detect_plan_info
from services.ingestion.utils import find_manifest_for_pdf


# 공통 문서로 간주되는 doc_type
COMMON_DOC_TYPES = {"사업방법서", "약관", "상품요약서"}


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


def classify_unassigned_reason(
    conn,
    doc: dict,
    candidate_plans: list[dict],
) -> tuple[str, str]:
    """
    미태깅 원인 분류

    Returns:
        (reason_code, reason_detail)
    """
    source_path = doc["source_path"]
    doc_type = doc["doc_type"]
    meta = doc["meta"] if isinstance(doc["meta"], dict) else {}

    # 1. manifest 파일 확인
    pdf_path = Path(source_path)
    manifest_path = find_manifest_for_pdf(pdf_path) if pdf_path.exists() else None
    manifest = load_manifest(manifest_path) if manifest_path else None

    manifest_hit = False
    manifest_has_plan_info = False

    if manifest:
        manifest_hit = True
        # manifest에 plan 정보가 있는지 확인
        plan_info = manifest.plan
        if (plan_info.gender and plan_info.gender != "U") or \
           plan_info.age_min is not None or \
           plan_info.age_max is not None:
            manifest_has_plan_info = True

    # 2. detector로 감지 시도
    doc_title = meta.get("title")
    detected = detect_plan_info(source_path, doc_title, meta)
    detector_has_info = (detected.gender is not None or detected.age_min is not None)

    # 3. 분류
    # 3-1. 공통 문서 타입이고 manifest에 plan 정보 없음
    if doc_type in COMMON_DOC_TYPES and not manifest_has_plan_info and not detector_has_info:
        return "COMMON_DOC_EXPECTED", f"doc_type={doc_type}는 플랜 구분 없는 공통 문서"

    # 3-2. manifest가 있지만 plan 정보가 없음
    if manifest_hit and not manifest_has_plan_info:
        # detector가 감지할 수 있는 경우
        if detector_has_info:
            return "DETECTOR_POSSIBLE", f"detector가 감지 가능: {detected.detection_source}"
        # 공통 문서가 아닌데 plan 정보 없음 → manifest 추가 필요
        return "MANIFEST_MISSING", "manifest에 plan 정보 추가 필요"

    # 3-3. manifest가 없음
    if not manifest_hit:
        if detector_has_info:
            return "DETECTOR_POSSIBLE", f"detector가 감지 가능: {detected.detection_source}"
        if doc_type in COMMON_DOC_TYPES:
            return "COMMON_DOC_EXPECTED", f"doc_type={doc_type}는 플랜 구분 없는 공통 문서"
        return "MANIFEST_MISSING", "manifest 파일 생성 필요"

    # 3-4. plan 정보는 있지만 매칭되는 plan이 DB에 없음
    if manifest_has_plan_info and len(candidate_plans) == 0:
        return "NO_PLAN_DEFINED_IN_DB", f"product_plan 테이블에 매칭되는 plan 없음"

    # 3-5. 그 외 (detector로 감지 가능한 경우)
    if detector_has_info:
        return "DETECTOR_POSSIBLE", f"detector가 감지 가능: {detected.detection_source}"

    return "UNKNOWN", "원인 불명"


def audit_unassigned_plans(
    insurer_code: str,
    db_url: str | None = None,
) -> list[dict]:
    """
    특정 보험사의 plan_id가 NULL인 문서들 분석

    Returns:
        audit 결과 리스트
    """
    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)
    results: list[dict] = []

    try:
        with conn.cursor() as cur:
            # 1. plan_id가 NULL인 문서 조회
            cur.execute("""
                SELECT
                    d.document_id,
                    d.doc_type,
                    d.source_path,
                    d.product_id,
                    d.plan_id,
                    d.meta,
                    i.insurer_code
                FROM document d
                JOIN insurer i ON d.insurer_id = i.insurer_id
                WHERE i.insurer_code = %s AND d.plan_id IS NULL
                ORDER BY d.document_id
            """, (insurer_code.upper(),))

            documents = cur.fetchall()

            for doc in documents:
                # 2. candidate plans 조회
                cur.execute("""
                    SELECT plan_id, plan_name, gender, age_min, age_max
                    FROM product_plan
                    WHERE product_id = %s
                    ORDER BY plan_id
                """, (doc["product_id"],))

                candidate_plans = cur.fetchall()

                # 3. manifest 확인
                pdf_path = Path(doc["source_path"])
                manifest_path = find_manifest_for_pdf(pdf_path) if pdf_path.exists() else None
                manifest_hit = manifest_path is not None

                # 4. 원인 분류
                reason_code, reason_detail = classify_unassigned_reason(
                    conn, doc, candidate_plans
                )

                results.append({
                    "document_id": doc["document_id"],
                    "doc_type": doc["doc_type"],
                    "source_path": doc["source_path"],
                    "product_id": doc["product_id"],
                    "plan_id": doc["plan_id"],
                    "manifest_hit": manifest_hit,
                    "candidate_plans": [
                        f"{p['plan_id']}:{p['plan_name']}" for p in candidate_plans
                    ],
                    "reason": reason_code,
                    "reason_detail": reason_detail,
                })

        return results

    finally:
        conn.close()


def generate_markdown_report(
    insurer_code: str,
    audit_results: list[dict],
    output_path: Path,
) -> None:
    """
    마크다운 리포트 생성
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 통계
    reason_counts: dict[str, int] = {}
    for r in audit_results:
        reason = r["reason"]
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {insurer_code} Plan 미태깅 원인 분석 리포트\n\n")
        f.write(f"> 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("---\n\n")

        # 요약
        f.write("## 요약\n\n")
        f.write(f"- 전체 미태깅 문서: **{len(audit_results)}개**\n")
        for reason, count in sorted(reason_counts.items()):
            emoji = {
                "COMMON_DOC_EXPECTED": "✅",
                "MANIFEST_MISSING": "⚠️",
                "NO_PLAN_DEFINED_IN_DB": "❌",
                "DETECTOR_POSSIBLE": "🔍",
                "UNKNOWN": "❓",
            }.get(reason, "•")
            f.write(f"- {emoji} {reason}: {count}개\n")
        f.write("\n")

        # 원인별 설명
        f.write("### 원인 코드 설명\n\n")
        f.write("| 코드 | 의미 | 조치 |\n")
        f.write("|------|------|------|\n")
        f.write("| COMMON_DOC_EXPECTED | 공통 문서로 plan NULL이 정상 | 조치 불필요 (PASS) |\n")
        f.write("| MANIFEST_MISSING | manifest에 plan 정보 추가 필요 | manifest.yaml 수정 |\n")
        f.write("| NO_PLAN_DEFINED_IN_DB | product_plan 테이블에 plan 없음 | DB seed 추가 |\n")
        f.write("| DETECTOR_POSSIBLE | detector 개선으로 자동 감지 가능 | plan_detector 개선 |\n")
        f.write("\n---\n\n")

        # 상세 테이블
        f.write("## 상세 내역\n\n")
        f.write("| document_id | doc_type | source_path | product_id | plan_id | manifest_hit | reason | detail |\n")
        f.write("|-------------|----------|-------------|------------|---------|--------------|--------|--------|\n")

        for r in audit_results:
            source_short = r["source_path"].split("/")[-1] if r["source_path"] else ""
            manifest_emoji = "✅" if r["manifest_hit"] else "❌"
            f.write(f"| {r['document_id']} | {r['doc_type']} | {source_short} | {r['product_id']} | {r['plan_id'] or 'NULL'} | {manifest_emoji} | {r['reason']} | {r['reason_detail']} |\n")

        f.write("\n---\n\n")

        # candidate plans
        f.write("## 후보 Plans (product_plan 테이블)\n\n")
        if audit_results:
            plans = audit_results[0]["candidate_plans"]
            f.write("| plan_id:plan_name |\n")
            f.write("|-------------------|\n")
            for p in plans:
                f.write(f"| {p} |\n")

        f.write("\n---\n\n")

        # 결론
        f.write("## 결론\n\n")

        common_count = reason_counts.get("COMMON_DOC_EXPECTED", 0)
        action_needed = len(audit_results) - common_count

        if action_needed == 0:
            f.write("**모든 미태깅 문서가 `COMMON_DOC_EXPECTED`로 분류되어 정상입니다.**\n\n")
            f.write("이 문서들은 플랜 구분 없이 모든 플랜에 공통으로 적용되는 문서이므로, ")
            f.write("`plan_id = NULL`이 의도된 동작입니다.\n")
        else:
            f.write(f"**조치 필요 문서: {action_needed}개**\n\n")
            if reason_counts.get("MANIFEST_MISSING", 0) > 0:
                f.write("- MANIFEST_MISSING: manifest.yaml에 plan 정보 추가 필요\n")
            if reason_counts.get("NO_PLAN_DEFINED_IN_DB", 0) > 0:
                f.write("- NO_PLAN_DEFINED_IN_DB: product_plan 테이블에 plan seed 추가 필요\n")
            if reason_counts.get("DETECTOR_POSSIBLE", 0) > 0:
                f.write("- DETECTOR_POSSIBLE: plan_detector 로직 개선 검토\n")

    print(f"Report generated: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit unassigned plan_id documents",
    )

    parser.add_argument(
        "--insurer",
        type=str,
        required=True,
        help="보험사 코드 (예: DB, LOTTE)",
    )

    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 파일 경로 (기본: artifacts/audit/<insurer>_unassigned_plans.md)",
    )

    args = parser.parse_args()

    insurer_code = args.insurer.upper()

    # 감사 실행
    print(f"Auditing unassigned plans for {insurer_code}...")
    results = audit_unassigned_plans(insurer_code, args.db_url)

    if not results:
        print(f"No unassigned documents found for {insurer_code}")
        return 0

    print(f"Found {len(results)} unassigned documents")

    # 리포트 생성
    output_path = Path(args.output) if args.output else \
        Path(f"artifacts/audit/{insurer_code.lower()}_unassigned_plans.md")

    generate_markdown_report(insurer_code, results, output_path)

    # 콘솔 요약
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    reason_counts: dict[str, int] = {}
    for r in results:
        reason = r["reason"]
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    for reason, count in sorted(reason_counts.items()):
        print(f"  {reason}: {count}")

    common_count = reason_counts.get("COMMON_DOC_EXPECTED", 0)
    if common_count == len(results):
        print("\n✅ All unassigned documents are COMMON_DOC_EXPECTED (intentional NULL)")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
