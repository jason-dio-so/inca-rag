#!/usr/bin/env python3
"""
Step I-1: Backfill Plan IDs

기존 document/chunk에 plan_id가 NULL인 경우
경로/메타에서 plan 정보를 감지하여 backfill

Usage:
    python tools/backfill_plan_ids.py
    python tools/backfill_plan_ids.py --dry-run
    python tools/backfill_plan_ids.py --insurer SAMSUNG
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 모듈 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from psycopg.rows import dict_row

from services.ingestion.manifest import ManifestData, load_manifest
from services.ingestion.plan_detector import (
    DetectedPlanInfo,
    PlanDetectorResult,
    detect_plan_info,
    find_matching_plan_id,
)
from services.ingestion.utils import find_manifest_for_pdf


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


def find_plan_by_manifest(
    conn,
    source_path: str,
    insurer_code: str,
) -> tuple[int | None, str | None]:
    """
    manifest 파일에서 plan 정보를 읽어 매칭되는 plan_id 반환

    Returns:
        (plan_id, reason) - plan_id가 None이면 매칭 실패
    """
    pdf_path = Path(source_path)
    if not pdf_path.exists():
        return None, "source_path not found"

    manifest_path = find_manifest_for_pdf(pdf_path)
    if not manifest_path:
        return None, "no_manifest"

    manifest = load_manifest(manifest_path)
    if not manifest:
        return None, "manifest_load_failed"

    # manifest에서 plan 정보 추출
    gender = manifest.plan.gender or "U"
    age_min = manifest.plan.age_min
    age_max = manifest.plan.age_max

    # gender=U이고 age도 없으면 매칭 불가
    if gender == "U" and age_min is None and age_max is None:
        return None, "manifest_no_plan_info"

    # product_id 조회
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT p.product_id
            FROM product p
            JOIN insurer i ON p.insurer_id = i.insurer_id
            WHERE i.insurer_code = %s
            ORDER BY p.product_id
            LIMIT 1
        """, (insurer_code,))

        product_row = cur.fetchone()
        if not product_row:
            return None, "no_product"

        product_id = product_row["product_id"]

        # gender 조건
        gender_condition = ""
        gender_params: list = []
        if gender != "U":
            gender_condition = "AND (pp.gender = %s OR pp.gender = 'U')"
            gender_params = [gender]

        # age 조건
        age_conditions: list[str] = []
        age_params: list = []
        if age_min is not None:
            age_conditions.append("(pp.age_min IS NULL OR pp.age_min <= %s)")
            age_params.append(age_min)
        if age_max is not None:
            age_conditions.append("(pp.age_max IS NULL OR pp.age_max >= %s)")
            age_params.append(age_max)

        age_condition = " AND ".join(age_conditions) if age_conditions else "TRUE"

        # 매칭 우선순위:
        # 1. age_specificity: age 제약이 있는 plan 우선 (NULL보다 구체적)
        # 2. gender_score: 정확한 gender 매칭 우선
        # 3. age_range: 더 좁은 범위 우선
        query = f"""
            SELECT pp.plan_id, pp.plan_name, pp.gender, pp.age_min, pp.age_max,
                   CASE WHEN pp.gender = %s THEN 2 WHEN pp.gender = 'U' THEN 1 ELSE 0 END as gender_score,
                   CASE
                     WHEN pp.age_min IS NOT NULL AND pp.age_max IS NOT NULL THEN 2
                     WHEN pp.age_min IS NOT NULL OR pp.age_max IS NOT NULL THEN 1
                     ELSE 0
                   END as age_specificity,
                   COALESCE(pp.age_max, 999) - COALESCE(pp.age_min, 0) as age_range
            FROM product_plan pp
            WHERE pp.product_id = %s
              {gender_condition}
              AND {age_condition}
            ORDER BY age_specificity DESC, gender_score DESC, age_range ASC
            LIMIT 1
        """

        params = tuple([gender, product_id] + gender_params + age_params)
        cur.execute(query, params)

        plan_row = cur.fetchone()
        if plan_row:
            reason = f"manifest: gender={gender}"
            if age_min is not None or age_max is not None:
                reason += f", age={age_min or '*'}-{age_max or '*'}"
            return plan_row["plan_id"], reason

        return None, f"manifest_no_match (gender={gender}, age={age_min}-{age_max})"


def backfill_plan_ids(
    db_url: str | None = None,
    insurer_code: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    use_manifest: bool = False,
) -> dict:
    """
    plan_id가 NULL인 document들에 대해 plan_id backfill

    Args:
        use_manifest: True이면 manifest 파일 우선 사용

    Returns:
        통계 dict: {scanned, detected, updated, errors}
    """
    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)

    stats = {
        "scanned": 0,
        "detected": 0,
        "manifest_matched": 0,
        "detector_matched": 0,
        "updated": 0,
        "no_match": 0,
        "errors": 0,
    }

    try:
        # 1. plan_id가 NULL인 문서 조회
        with conn.cursor() as cur:
            query = """
                SELECT
                    d.document_id,
                    d.source_path,
                    d.meta,
                    d.insurer_id,
                    i.insurer_code
                FROM document d
                LEFT JOIN insurer i ON d.insurer_id = i.insurer_id
                WHERE d.plan_id IS NULL
            """
            params: list = []

            if insurer_code:
                query += " AND i.insurer_code = %s"
                params.append(insurer_code.upper())

            query += " ORDER BY d.document_id"

            cur.execute(query, params)
            documents = cur.fetchall()

        print(f"Found {len(documents)} documents with plan_id IS NULL")

        # 2. 각 문서에 대해 plan 감지 시도
        for doc in documents:
            stats["scanned"] += 1
            doc_id = doc["document_id"]
            source_path = doc["source_path"]
            meta = doc["meta"] if isinstance(doc["meta"], dict) else {}
            doc_insurer_code = doc["insurer_code"]

            if not doc_insurer_code:
                if verbose:
                    print(f"  [SKIP] doc={doc_id}: no insurer_code")
                continue

            try:
                plan_id = None
                match_source = None

                # 3-1. Manifest 기반 매칭 시도 (use_manifest가 True인 경우)
                if use_manifest:
                    manifest_plan_id, manifest_reason = find_plan_by_manifest(
                        conn, source_path, doc_insurer_code
                    )
                    if manifest_plan_id:
                        plan_id = manifest_plan_id
                        match_source = manifest_reason
                        stats["manifest_matched"] += 1
                        stats["detected"] += 1
                    elif verbose and "no_manifest" not in manifest_reason:
                        print(f"  [MANIFEST] doc={doc_id}: {manifest_reason}")

                # 3-2. Detector 기반 매칭 (manifest 실패 시 또는 use_manifest=False)
                if plan_id is None:
                    doc_title = meta.get("title")
                    detected_info = detect_plan_info(source_path, doc_title, meta)

                    if detected_info.gender is None and detected_info.age_min is None:
                        if verbose:
                            print(f"  [SKIP] doc={doc_id}: no plan info detected from path/meta")
                        continue

                    stats["detected"] += 1

                    # 매칭되는 plan_id 조회
                    plan_id = find_matching_plan_id(conn, doc_insurer_code, detected_info)
                    if plan_id:
                        match_source = f"detector: {detected_info.detection_source}"
                        stats["detector_matched"] += 1

                if plan_id is None:
                    stats["no_match"] += 1
                    if verbose:
                        print(f"  [NO_MATCH] doc={doc_id}: no matching plan in DB")
                    continue

                # 4. Update
                if dry_run:
                    print(f"  [DRY-RUN] doc={doc_id}: would set plan_id={plan_id} ({match_source})")
                    stats["updated"] += 1
                else:
                    with conn.cursor() as cur:
                        # document 업데이트
                        cur.execute(
                            "UPDATE document SET plan_id = %s WHERE document_id = %s",
                            (plan_id, doc_id),
                        )

                        # chunk 업데이트 (document의 plan_id 상속)
                        cur.execute(
                            "UPDATE chunk SET plan_id = %s WHERE document_id = %s",
                            (plan_id, doc_id),
                        )

                        conn.commit()

                    print(f"  [UPDATED] doc={doc_id}: plan_id={plan_id} ({match_source})")
                    stats["updated"] += 1

            except Exception as e:
                stats["errors"] += 1
                print(f"  [ERROR] doc={doc_id}: {e}")
                continue

        # 결과 출력
        print("\n" + "=" * 60)
        print("Backfill Summary")
        print("=" * 60)
        print(f"  Scanned:    {stats['scanned']}")
        print(f"  Detected:   {stats['detected']} (plan info found)")
        if use_manifest:
            print(f"    - manifest: {stats['manifest_matched']}")
            print(f"    - detector: {stats['detector_matched']}")
        print(f"  Updated:    {stats['updated']}")
        print(f"  No match:   {stats['no_match']} (detected but no matching plan in DB)")
        print(f"  Errors:     {stats['errors']}")
        if dry_run:
            print("\n  [DRY-RUN MODE - no actual changes made]")

        return stats

    finally:
        conn.close()


def verify_backfill(db_url: str | None = None):
    """Backfill 결과 검증"""
    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)

    try:
        with conn.cursor() as cur:
            # plan_id 분포 조회
            cur.execute("""
                SELECT
                    i.insurer_code,
                    COUNT(*) as total_docs,
                    COUNT(d.plan_id) as with_plan,
                    COUNT(*) - COUNT(d.plan_id) as without_plan
                FROM document d
                LEFT JOIN insurer i ON d.insurer_id = i.insurer_id
                GROUP BY i.insurer_code
                ORDER BY i.insurer_code
            """)

            rows = cur.fetchall()

            print("\n" + "=" * 60)
            print("Document plan_id Distribution")
            print("=" * 60)
            print(f"{'Insurer':<12} {'Total':<10} {'With Plan':<12} {'Without Plan':<12}")
            print("-" * 60)

            for row in rows:
                insurer = row["insurer_code"] or "(NULL)"
                print(f"{insurer:<12} {row['total_docs']:<10} {row['with_plan']:<12} {row['without_plan']:<12}")

    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill plan_id for documents/chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 업데이트 없이 실행 (시뮬레이션)",
    )

    parser.add_argument(
        "--insurer",
        type=str,
        default=None,
        help="특정 보험사만 처리 (예: SAMSUNG)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="백필 없이 현재 상태만 확인",
    )

    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (기본: DATABASE_URL 환경변수)",
    )

    parser.add_argument(
        "--skip-if-empty",
        action="store_true",
        help="데이터가 없으면 에러 없이 종료 (CI용)",
    )

    parser.add_argument(
        "--manifest",
        action="store_true",
        help="manifest 파일 기반 plan 매칭 우선 사용",
    )

    args = parser.parse_args()

    # DB 연결 시도 (CI 환경에서 DB 없으면 skip)
    try:
        import psycopg
        conn = psycopg.connect(args.db_url or get_db_url())
        conn.close()
    except Exception as e:
        if args.skip_if_empty:
            print(f"[SKIP] Database not available: {e}")
            return 0
        raise

    if args.verify_only:
        verify_backfill(args.db_url)
        return 0

    print("=" * 60)
    print("Plan ID Backfill Tool")
    print("=" * 60)

    if args.dry_run:
        print("[DRY-RUN MODE]")

    if args.manifest:
        print("[MANIFEST MODE]")

    if args.insurer:
        print(f"Target insurer: {args.insurer}")

    print()

    stats = backfill_plan_ids(
        db_url=args.db_url,
        insurer_code=args.insurer,
        dry_run=args.dry_run,
        verbose=args.verbose,
        use_manifest=args.manifest,
    )

    # 검증 출력
    verify_backfill(args.db_url)

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
