#!/usr/bin/env python3
"""
V1.6.3-β-3 Synthetic Meta Normalization (meta-only)

기존 synthetic_type=split chunk들의 meta 스키마를 운영 기준(β-2)으로 정규화.

목표:
- meta.synthetic_method = "v1_6_3_beta_2_split" 통일
- meta.entities.amount.method = "v1_6_3_beta_2_split" 통일
- 원본 값 보존: *_original 키 추가

절대 원칙:
- meta JSONB만 수정 (content/embedding/coverage_code/amount_value 불변)
- 신정원 통일코드 불변
- Fail Closed: 애매하면 UPDATE 하지 않고 리포트에 남김
- Idempotent: 재실행해도 동일 결과

사용법:
    python tools/backfill_normalize_synthetic_meta_v1_6_3_beta_3.py --scan
    python tools/backfill_normalize_synthetic_meta_v1_6_3_beta_3.py --dry-run --limit 200
    python tools/backfill_normalize_synthetic_meta_v1_6_3_beta_3.py --batch-size 1000
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor

# 운영 기준 값 (β-2)
TARGET_SYNTHETIC_METHOD = "v1_6_3_beta_2_split"
TARGET_AMOUNT_METHOD = "v1_6_3_beta_2_split"
TARGET_SYNTHETIC_TYPE = "split"


@dataclass
class NormalizationCandidate:
    """정규화 대상 chunk"""
    chunk_id: int
    insurer_id: int
    document_id: int
    page_start: int | None
    old_synthetic_type: str | None
    old_synthetic_method: str | None
    old_amount_method: str | None
    needs_synthetic_type: bool
    needs_synthetic_method: bool
    needs_amount_method: bool
    skip_reason: str | None = None


def get_db_connection():
    """DB 연결 생성"""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "inca_rag"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def scan_distribution(conn) -> dict:
    """
    STEP 1: 현황 스캔 - meta 분포 수집
    """
    results = {}

    # synthetic_type 분포
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                COALESCE(meta->>'synthetic_type', 'NULL') AS synthetic_type,
                COUNT(*) AS cnt
            FROM chunk
            WHERE COALESCE((meta->>'is_synthetic')::boolean, false) = true
            GROUP BY 1
            ORDER BY cnt DESC
        """)
        results["synthetic_type_distribution"] = cur.fetchall()

    # synthetic_method 분포
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                COALESCE(meta->>'synthetic_method', 'NULL') AS synthetic_method,
                COUNT(*) AS cnt
            FROM chunk
            WHERE COALESCE((meta->>'is_synthetic')::boolean, false) = true
            GROUP BY 1
            ORDER BY cnt DESC
        """)
        results["synthetic_method_distribution"] = cur.fetchall()

    # amount.method 분포
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                COALESCE(meta->'entities'->'amount'->>'method', 'NULL') AS amount_method,
                COUNT(*) AS cnt
            FROM chunk
            WHERE COALESCE((meta->>'is_synthetic')::boolean, false) = true
            GROUP BY 1
            ORDER BY cnt DESC
        """)
        results["amount_method_distribution"] = cur.fetchall()

    # 전체 synthetic chunk 수
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM chunk
            WHERE COALESCE((meta->>'is_synthetic')::boolean, false) = true
        """)
        results["total_synthetic_count"] = cur.fetchone()[0]

    # split synthetic chunk 수
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM chunk
            WHERE COALESCE((meta->>'is_synthetic')::boolean, false) = true
              AND (
                  meta->>'synthetic_type' = 'split'
                  OR (
                      meta->>'synthetic_type' IS NULL
                      AND meta ? 'synthetic_source_chunk_id'
                      AND meta->'entities'->>'coverage_code' IS NOT NULL
                      AND meta->'entities'->'amount'->>'amount_value' IS NOT NULL
                  )
              )
        """)
        results["split_synthetic_count"] = cur.fetchone()[0]

    return results


def get_normalization_candidates(conn, limit: int | None = None) -> list[NormalizationCandidate]:
    """
    정규화 대상 chunk 조회
    """
    query = """
        SELECT
            chunk_id,
            insurer_id,
            document_id,
            page_start,
            meta->>'synthetic_type' AS synthetic_type,
            meta->>'synthetic_method' AS synthetic_method,
            meta->'entities'->'amount'->>'method' AS amount_method,
            meta->'entities'->>'coverage_code' AS coverage_code,
            meta->'entities'->'amount'->>'amount_value' AS amount_value,
            meta ? 'synthetic_source_chunk_id' AS has_source_chunk_id
        FROM chunk
        WHERE COALESCE((meta->>'is_synthetic')::boolean, false) = true
        ORDER BY chunk_id
    """

    if limit:
        query += f" LIMIT {limit}"

    candidates = []

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()

    for row in rows:
        # 대상 여부 판별
        synthetic_type = row["synthetic_type"]
        synthetic_method = row["synthetic_method"]
        amount_method = row["amount_method"]
        coverage_code = row["coverage_code"]
        amount_value = row["amount_value"]
        has_source_chunk_id = row["has_source_chunk_id"]

        skip_reason = None

        # synthetic_type 판별
        is_split_type = synthetic_type == "split"
        is_split_candidate = (
            synthetic_type is None
            and has_source_chunk_id
            and coverage_code is not None
            and amount_value is not None
        )

        if not is_split_type and not is_split_candidate:
            # split이 아닌 다른 synthetic type이거나 조건 미충족
            if synthetic_type is not None and synthetic_type != "split":
                skip_reason = f"different_synthetic_type:{synthetic_type}"
            else:
                skip_reason = "missing_required_fields"

        # 필요한 업데이트 판별
        needs_synthetic_type = synthetic_type is None and is_split_candidate
        needs_synthetic_method = synthetic_method != TARGET_SYNTHETIC_METHOD
        needs_amount_method = amount_method != TARGET_AMOUNT_METHOD

        # 이미 정규화된 경우 skip
        if not needs_synthetic_type and not needs_synthetic_method and not needs_amount_method:
            skip_reason = "already_normalized"

        candidate = NormalizationCandidate(
            chunk_id=row["chunk_id"],
            insurer_id=row["insurer_id"],
            document_id=row["document_id"],
            page_start=row["page_start"],
            old_synthetic_type=synthetic_type,
            old_synthetic_method=synthetic_method,
            old_amount_method=amount_method,
            needs_synthetic_type=needs_synthetic_type if skip_reason is None else False,
            needs_synthetic_method=needs_synthetic_method if skip_reason is None else False,
            needs_amount_method=needs_amount_method if skip_reason is None else False,
            skip_reason=skip_reason,
        )
        candidates.append(candidate)

    return candidates


def execute_normalization(conn, candidates: list[NormalizationCandidate], batch_size: int = 500) -> dict:
    """
    STEP 3: meta-only UPDATE 실행
    """
    stats = {
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "updated_chunks": [],
        "skipped_chunks": [],
        "error_chunks": [],
    }

    update_candidates = [c for c in candidates if c.skip_reason is None]
    skip_candidates = [c for c in candidates if c.skip_reason is not None]

    stats["skipped"] = len(skip_candidates)
    stats["skipped_chunks"] = [(c.chunk_id, c.skip_reason) for c in skip_candidates]

    # 배치 단위 업데이트
    for i in range(0, len(update_candidates), batch_size):
        batch = update_candidates[i:i + batch_size]

        for candidate in batch:
            try:
                update_chunk_meta(conn, candidate)
                stats["updated"] += 1
                stats["updated_chunks"].append(candidate.chunk_id)
            except Exception as e:
                stats["errors"] += 1
                stats["error_chunks"].append((candidate.chunk_id, str(e)))

        conn.commit()
        print(f"  Progress: {min(i + batch_size, len(update_candidates))}/{len(update_candidates)} chunks")

    return stats


def update_chunk_meta(conn, candidate: NormalizationCandidate):
    """
    단일 chunk의 meta 정규화

    - synthetic_type: 없으면 'split' 추가
    - synthetic_method: 다르면 통일 + _original 보존
    - amount.method: 다르면 통일 + _original 보존
    """
    updates = []

    # 1. synthetic_type 설정 (없을 때만)
    if candidate.needs_synthetic_type:
        updates.append(f"meta = jsonb_set(meta, '{{synthetic_type}}', '\"{TARGET_SYNTHETIC_TYPE}\"')")

    # 2. synthetic_method 정규화
    if candidate.needs_synthetic_method:
        # 원본 보존 (기존 값이 있고 _original이 없을 때만)
        if candidate.old_synthetic_method is not None:
            updates.append(f"""
                meta = CASE
                    WHEN meta ? 'synthetic_method_original' THEN meta
                    ELSE jsonb_set(meta, '{{synthetic_method_original}}', to_jsonb(meta->>'synthetic_method'))
                END
            """)
        updates.append(f"meta = jsonb_set(meta, '{{synthetic_method}}', '\"{TARGET_SYNTHETIC_METHOD}\"')")

    # 3. amount.method 정규화
    if candidate.needs_amount_method:
        # 원본 보존 (기존 값이 있고 _original이 없을 때만)
        if candidate.old_amount_method is not None:
            updates.append(f"""
                meta = CASE
                    WHEN meta->'entities'->'amount' ? 'method_original' THEN meta
                    ELSE jsonb_set(meta, '{{entities,amount,method_original}}', to_jsonb(meta->'entities'->'amount'->>'method'))
                END
            """)
        updates.append(f"meta = jsonb_set(meta, '{{entities,amount,method}}', '\"{TARGET_AMOUNT_METHOD}\"')")

    if not updates:
        return

    # 순차 실행 (jsonb_set 연쇄)
    with conn.cursor() as cur:
        for update_sql in updates:
            full_query = f"UPDATE chunk SET {update_sql} WHERE chunk_id = %s"
            cur.execute(full_query, (candidate.chunk_id,))


def save_distribution_csv(distribution: dict, output_dir: str, prefix: str):
    """분포 결과를 CSV로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for key, rows in distribution.items():
        if isinstance(rows, list) and rows:
            filepath = os.path.join(output_dir, f"{prefix}_{key}_{timestamp}.csv")
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            print(f"  Saved: {filepath}")


def save_candidates_csv(candidates: list[NormalizationCandidate], output_dir: str, filename: str):
    """후보 목록을 CSV로 저장"""
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "chunk_id", "insurer_id", "document_id", "page_start",
            "old_synthetic_type", "old_synthetic_method", "old_amount_method",
            "needs_synthetic_type", "needs_synthetic_method", "needs_amount_method",
            "skip_reason"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for c in candidates:
            writer.writerow({
                "chunk_id": c.chunk_id,
                "insurer_id": c.insurer_id,
                "document_id": c.document_id,
                "page_start": c.page_start,
                "old_synthetic_type": c.old_synthetic_type,
                "old_synthetic_method": c.old_synthetic_method,
                "old_amount_method": c.old_amount_method,
                "needs_synthetic_type": c.needs_synthetic_type,
                "needs_synthetic_method": c.needs_synthetic_method,
                "needs_amount_method": c.needs_amount_method,
                "skip_reason": c.skip_reason,
            })

    print(f"  Saved: {filepath}")


def run_scan(output_dir: str):
    """STEP 1: 현황 스캔"""
    print("[V1.6.3-β-3 Synthetic Meta Normalization]")
    print("  mode: scan")
    print()

    conn = get_db_connection()

    try:
        print("[STEP 1] Scanning meta distribution...")
        distribution = scan_distribution(conn)

        print(f"\n  Total synthetic chunks: {distribution['total_synthetic_count']}")
        print(f"  Split synthetic chunks: {distribution['split_synthetic_count']}")

        print("\n  synthetic_type distribution:")
        for row in distribution["synthetic_type_distribution"]:
            print(f"    {row['synthetic_type']}: {row['cnt']}")

        print("\n  synthetic_method distribution:")
        for row in distribution["synthetic_method_distribution"]:
            print(f"    {row['synthetic_method']}: {row['cnt']}")

        print("\n  amount.method distribution:")
        for row in distribution["amount_method_distribution"]:
            print(f"    {row['amount_method']}: {row['cnt']}")

        # CSV 저장
        print("\n[Saving distribution CSVs]")
        save_distribution_csv(distribution, output_dir, "meta_before")

    finally:
        conn.close()


def run_dry_run(output_dir: str, limit: int | None = None):
    """STEP 2: Dry-run 계획 수립"""
    print("[V1.6.3-β-3 Synthetic Meta Normalization]")
    print(f"  mode: dry-run")
    print(f"  limit: {limit or 'ALL'}")
    print()

    conn = get_db_connection()

    try:
        print("[STEP 2] Generating normalization plan...")
        candidates = get_normalization_candidates(conn, limit)

        # 통계
        to_update = [c for c in candidates if c.skip_reason is None]
        to_skip = [c for c in candidates if c.skip_reason is not None]

        needs_type = sum(1 for c in to_update if c.needs_synthetic_type)
        needs_method = sum(1 for c in to_update if c.needs_synthetic_method)
        needs_amount = sum(1 for c in to_update if c.needs_amount_method)

        print(f"\n  Total candidates: {len(candidates)}")
        print(f"  To update: {len(to_update)}")
        print(f"    - needs_synthetic_type: {needs_type}")
        print(f"    - needs_synthetic_method: {needs_method}")
        print(f"    - needs_amount_method: {needs_amount}")
        print(f"  To skip: {len(to_skip)}")

        # Skip 사유별 분류
        skip_reasons = {}
        for c in to_skip:
            reason = c.skip_reason or "unknown"
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

        if skip_reasons:
            print("\n  Skip reasons:")
            for reason, cnt in sorted(skip_reasons.items(), key=lambda x: -x[1]):
                print(f"    {reason}: {cnt}")

        # CSV 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print("\n[Saving plan CSVs]")
        save_candidates_csv(candidates, output_dir, f"normalize_plan_sample_{timestamp}.csv")

    finally:
        conn.close()


def run_execute(output_dir: str, batch_size: int = 500):
    """STEP 3: 실제 UPDATE 실행"""
    print("[V1.6.3-β-3 Synthetic Meta Normalization]")
    print(f"  mode: execute")
    print(f"  batch_size: {batch_size}")
    print()

    conn = get_db_connection()

    try:
        print("[STEP 3] Executing normalization...")
        candidates = get_normalization_candidates(conn)

        stats = execute_normalization(conn, candidates, batch_size)

        print(f"\n[SUMMARY]")
        print(f"  Updated: {stats['updated']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")

        # 결과 CSV 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # updated chunks
        if stats["updated_chunks"]:
            filepath = os.path.join(output_dir, f"normalize_executed_{timestamp}.csv")
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["chunk_id"])
                for chunk_id in stats["updated_chunks"]:
                    writer.writerow([chunk_id])
            print(f"  Saved: {filepath}")

        # 변경 후 분포 확인
        print("\n[STEP 4] Verifying distribution after update...")
        distribution = scan_distribution(conn)

        print("\n  synthetic_method distribution (after):")
        for row in distribution["synthetic_method_distribution"]:
            print(f"    {row['synthetic_method']}: {row['cnt']}")

        print("\n  amount.method distribution (after):")
        for row in distribution["amount_method_distribution"]:
            print(f"    {row['amount_method']}: {row['cnt']}")

        save_distribution_csv(distribution, output_dir, "meta_after")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="V1.6.3-β-3 Synthetic Meta Normalization"
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan and report meta distribution only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate normalization plan without executing",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of candidates (for dry-run)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for execute mode",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/v1_6_3_beta_3",
        help="Output directory for reports",
    )

    args = parser.parse_args()

    # 출력 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)

    if args.scan:
        run_scan(args.output_dir)
    elif args.dry_run:
        run_dry_run(args.output_dir, args.limit)
    else:
        run_execute(args.output_dir, args.batch_size)


if __name__ == "__main__":
    main()
