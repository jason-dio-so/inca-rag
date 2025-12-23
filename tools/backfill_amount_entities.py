#!/usr/bin/env python3
"""
V1.6.1 Amount Tagging Backfill

chunk.meta.entities.amount 필드를 채우는 백필 스크립트.
V1.6 Amount Bridge가 NOT_FOUND로 떨어지는 근본 원인 해결.

원칙:
- LLM 추론 금지. 정규식/룰 기반 추출만 사용.
- 기존 amount_extractor.extract_amount() 재사용
- 신정원 canonical (coverage_code) 원칙 유지

사용법:
    python tools/backfill_amount_entities.py --dry-run  # 미리보기
    python tools/backfill_amount_entities.py            # 실제 실행
    python tools/backfill_amount_entities.py --insurer SAMSUNG  # 특정 보험사만
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor

from services.extraction.amount_extractor import extract_amount


@dataclass
class BackfillResult:
    """백필 결과"""
    chunk_id: int
    document_id: int
    insurer_code: str
    doc_type: str
    coverage_code: str | None
    amount_value: int | None
    amount_text: str | None
    confidence: str | None
    updated: bool = False


def get_db_connection():
    """DB 연결 생성"""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "inca_rag"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def get_target_chunks(
    conn,
    insurer_code: str | None = None,
    doc_types: list[str] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    백필 대상 chunk 조회

    조건:
    - coverage_code가 존재하는 chunk
    - meta.entities.amount가 없거나 비어있는 chunk
    - content에 금액 패턴이 있을 가능성이 있는 chunk (선제 필터링은 하지 않음)
    """
    query = """
    SELECT
        c.chunk_id,
        c.document_id,
        c.content,
        c.meta,
        c.page_start,
        i.insurer_code,
        d.doc_type
    FROM chunk c
    JOIN insurer i ON i.insurer_id = c.insurer_id
    JOIN document d ON d.document_id = c.document_id
    WHERE
        -- coverage_code가 존재
        c.meta->'entities'->>'coverage_code' IS NOT NULL
        -- amount가 없거나 비어있음
        AND (
            c.meta->'entities'->'amount' IS NULL
            OR c.meta->'entities'->'amount' = 'null'::jsonb
            OR c.meta->'entities'->'amount' = '{}'::jsonb
        )
    """

    params = []

    if insurer_code:
        query += " AND i.insurer_code = %s"
        params.append(insurer_code)

    if doc_types:
        query += " AND d.doc_type = ANY(%s)"
        params.append(doc_types)

    query += " ORDER BY c.chunk_id"

    if limit:
        query += " LIMIT %s"
        params.append(limit)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def extract_amount_from_content(content: str, doc_type: str) -> tuple[int | None, str | None, str | None]:
    """
    content에서 금액 추출

    기존 amount_extractor.extract_amount() 재사용

    Returns:
        (amount_value, amount_text, confidence)
    """
    result = extract_amount(content, doc_type=doc_type)

    if result.amount_value is not None:
        return result.amount_value, result.amount_text, result.confidence

    return None, None, None


def update_chunk_amount(
    conn,
    chunk_id: int,
    amount_value: int,
    amount_text: str,
    confidence: str,
    dry_run: bool = False,
) -> bool:
    """
    chunk.meta.entities.amount 업데이트

    기존 meta 구조를 깨지 않고 deep-merge 방식으로 업데이트
    """
    if dry_run:
        return False

    # amount 객체 생성
    amount_obj = {
        "amount_value": amount_value,
        "amount_text": amount_text,
        "confidence": confidence,
        "method": "backfill_regex",
    }

    # JSONB deep merge 업데이트
    update_query = """
    UPDATE chunk
    SET meta = jsonb_set(
        COALESCE(meta, '{}'::jsonb),
        '{entities,amount}',
        %s::jsonb,
        true
    )
    WHERE chunk_id = %s
    """

    with conn.cursor() as cur:
        cur.execute(update_query, (json.dumps(amount_obj), chunk_id))

    return True


def run_backfill(
    insurer_code: str | None = None,
    doc_types: list[str] | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    batch_size: int = 500,
) -> list[BackfillResult]:
    """
    백필 실행

    Args:
        insurer_code: 특정 보험사만 처리
        doc_types: 특정 doc_type만 처리
        dry_run: True면 업데이트 없이 대상만 출력
        limit: 처리할 최대 chunk 수
        batch_size: 배치 커밋 크기

    Returns:
        BackfillResult 리스트
    """
    conn = get_db_connection()
    results: list[BackfillResult] = []

    try:
        # 대상 chunk 조회
        chunks = get_target_chunks(conn, insurer_code, doc_types, limit)
        print(f"[INFO] 대상 chunk 수: {len(chunks)}")

        updated_count = 0
        skipped_count = 0

        for i, chunk in enumerate(chunks):
            chunk_id = chunk["chunk_id"]
            content = chunk["content"]
            doc_type = chunk["doc_type"]
            meta = chunk["meta"] or {}
            coverage_code = meta.get("entities", {}).get("coverage_code")

            # 금액 추출
            amount_value, amount_text, confidence = extract_amount_from_content(
                content, doc_type
            )

            result = BackfillResult(
                chunk_id=chunk_id,
                document_id=chunk["document_id"],
                insurer_code=chunk["insurer_code"],
                doc_type=doc_type,
                coverage_code=coverage_code,
                amount_value=amount_value,
                amount_text=amount_text,
                confidence=confidence,
            )

            if amount_value is not None:
                # 금액이 추출된 경우 업데이트
                updated = update_chunk_amount(
                    conn, chunk_id, amount_value, amount_text, confidence, dry_run
                )
                result.updated = updated

                if not dry_run:
                    updated_count += 1

                    # 배치 커밋
                    if updated_count % batch_size == 0:
                        conn.commit()
                        print(f"[INFO] {updated_count}개 커밋 완료")
            else:
                skipped_count += 1

            results.append(result)

            # 진행 상황 출력
            if (i + 1) % 100 == 0:
                print(f"[INFO] 진행: {i + 1}/{len(chunks)}")

        # 최종 커밋
        if not dry_run:
            conn.commit()

        print(f"\n[SUMMARY]")
        print(f"  대상 chunk: {len(chunks)}")
        print(f"  금액 추출 성공: {len([r for r in results if r.amount_value is not None])}")
        print(f"  금액 추출 실패: {skipped_count}")
        if not dry_run:
            print(f"  DB 업데이트: {updated_count}")

        return results

    finally:
        conn.close()


def print_dry_run_results(results: list[BackfillResult], max_show: int = 50):
    """dry-run 결과 출력"""
    extracted = [r for r in results if r.amount_value is not None]

    print(f"\n[DRY-RUN] 금액 추출 성공 chunk ({len(extracted)}건):\n")

    for r in extracted[:max_show]:
        print(f"  chunk_id={r.chunk_id:5d} | {r.insurer_code:8s} | {r.doc_type:10s} | "
              f"code={r.coverage_code or 'N/A':12s} | "
              f"amount={r.amount_text or 'N/A':15s} ({r.amount_value:,}원) | "
              f"conf={r.confidence}")

    if len(extracted) > max_show:
        print(f"\n  ... 외 {len(extracted) - max_show}건")


def main():
    parser = argparse.ArgumentParser(
        description="V1.6.1 Amount Tagging Backfill - chunk.meta.entities.amount 채우기"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="업데이트 없이 대상만 출력",
    )
    parser.add_argument(
        "--insurer",
        type=str,
        default=None,
        help="특정 보험사만 처리 (예: SAMSUNG)",
    )
    parser.add_argument(
        "--doc-types",
        type=str,
        nargs="+",
        default=["가입설계서", "상품요약서", "사업방법서"],
        help="처리할 doc_type 목록 (기본: 가입설계서 상품요약서 사업방법서)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처리할 최대 chunk 수",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="배치 커밋 크기 (기본: 500)",
    )

    args = parser.parse_args()

    print(f"[V1.6.1 Amount Tagging Backfill]")
    print(f"  dry-run: {args.dry_run}")
    print(f"  insurer: {args.insurer or 'ALL'}")
    print(f"  doc_types: {args.doc_types}")
    print(f"  limit: {args.limit or 'NONE'}")
    print()

    results = run_backfill(
        insurer_code=args.insurer,
        doc_types=args.doc_types,
        dry_run=args.dry_run,
        limit=args.limit,
        batch_size=args.batch_size,
    )

    if args.dry_run:
        print_dry_run_results(results)


if __name__ == "__main__":
    main()
