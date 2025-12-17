#!/usr/bin/env python3
"""
기존 chunk의 coverage_code 백필 스크립트

chunk.meta.entities.coverage_code가 신정원 코드가 아닌 경우:
1. coverage_code 값을 ontology_code로 이동
2. coverage_standard.meta.ontology_codes를 통해 신정원 코드로 리매핑
3. match_source를 'fallback_remap' 또는 'fallback_unmapped'로 업데이트

Usage:
    python tools/backfill_chunk_coverage_code.py
    python tools/backfill_chunk_coverage_code.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


# 신정원 코드 패턴: A로 시작하고 숫자+언더스코어 조합
STANDARD_CODE_PATTERN = re.compile(r"^[A-Z]\d+(_\d+)?$")


def is_standard_code(code: str | None) -> bool:
    """신정원 표준코드 여부 확인"""
    if not code:
        return False
    return bool(STANDARD_CODE_PATTERN.match(code))


@dataclass
class BackfillStats:
    """백필 통계"""
    total_chunks: int = 0
    chunks_with_coverage: int = 0
    already_standard: int = 0
    remapped_success: int = 0
    remapped_unmapped: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "",
            "=" * 60,
            "Chunk Coverage Code Backfill 결과",
            "=" * 60,
            f"  총 chunk 수: {self.total_chunks}",
            f"  coverage_code 있는 chunk: {self.chunks_with_coverage}",
            f"  이미 신정원 코드: {self.already_standard}",
            f"  리매핑 성공: {self.remapped_success}",
            f"  리매핑 실패(unmapped): {self.remapped_unmapped}",
        ]
        if self.errors:
            lines.append(f"  에러: {len(self.errors)}")
            for err in self.errors[:5]:
                lines.append(f"    - {err}")
        lines.append("=" * 60)
        return "\n".join(lines)


def load_ontology_remap_cache(conn: psycopg.Connection) -> dict[str, tuple[str, str]]:
    """
    coverage_standard.meta.ontology_codes에서 리매핑 캐시 로드
    Returns: {ontology_code: (coverage_code, coverage_name)}
    """
    cache: dict[str, tuple[str, str]] = {}

    with conn.cursor() as cur:
        cur.execute("""
            SELECT coverage_code, coverage_name, meta
            FROM coverage_standard
            WHERE meta IS NOT NULL
              AND meta ? 'ontology_codes'
        """)

        for row in cur.fetchall():
            coverage_code = row["coverage_code"]
            coverage_name = row["coverage_name"]
            meta = row["meta"] or {}
            ontology_codes = meta.get("ontology_codes", [])

            for ont_code in ontology_codes:
                cache[ont_code] = (coverage_code, coverage_name)

    return cache


def backfill_chunks(
    db_url: str | None = None,
    dry_run: bool = False,
) -> BackfillStats:
    """기존 chunk의 coverage_code를 신정원 코드로 백필"""
    stats = BackfillStats()

    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)

    try:
        # 리매핑 캐시 로드
        remap_cache = load_ontology_remap_cache(conn)
        print(f"Ontology remap cache loaded: {len(remap_cache)} entries")

        with conn.cursor() as cur:
            # coverage_code가 있는 chunk 조회
            cur.execute("""
                SELECT chunk_id, meta
                FROM chunk
                WHERE meta IS NOT NULL
                  AND meta->'entities'->>'coverage_code' IS NOT NULL
            """)

            chunks = cur.fetchall()
            stats.total_chunks = len(chunks)

            for chunk in chunks:
                chunk_id = chunk["chunk_id"]
                meta = chunk["meta"] or {}
                entities = meta.get("entities", {})
                coverage_code = entities.get("coverage_code")

                if not coverage_code:
                    continue

                stats.chunks_with_coverage += 1

                # 이미 신정원 코드인 경우 스킵
                if is_standard_code(coverage_code):
                    stats.already_standard += 1
                    continue

                # ontology 코드로 간주하고 리매핑 시도
                ontology_code = coverage_code

                if ontology_code in remap_cache:
                    # 리매핑 성공
                    new_code, new_name = remap_cache[ontology_code]
                    entities["ontology_code"] = ontology_code
                    entities["coverage_code"] = new_code
                    entities["coverage_name"] = new_name
                    entities["match_source"] = "fallback_remap"
                    stats.remapped_success += 1
                    action = f"remapped {ontology_code} → {new_code}"
                else:
                    # 리매핑 실패
                    entities["ontology_code"] = ontology_code
                    entities["coverage_code"] = None  # 신정원 코드 아니면 None
                    entities["match_source"] = "fallback_unmapped"
                    stats.remapped_unmapped += 1
                    action = f"unmapped {ontology_code} → None"

                meta["entities"] = entities

                if dry_run:
                    print(f"[DRY-RUN] chunk_id={chunk_id}: {action}")
                else:
                    try:
                        cur.execute(
                            """
                            UPDATE chunk
                            SET meta = %s
                            WHERE chunk_id = %s
                            """,
                            (json.dumps(meta, ensure_ascii=False), chunk_id),
                        )
                        conn.commit()
                    except Exception as e:
                        stats.errors.append(f"chunk_id={chunk_id}: {e}")
                        conn.rollback()

        if not dry_run:
            print(f"Backfill completed.")

    finally:
        conn.close()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chunk coverage_code 백필 (ontology → 신정원)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 업데이트 없이 확인만",
    )

    args = parser.parse_args()

    stats = backfill_chunks(
        db_url=args.db_url,
        dry_run=args.dry_run,
    )

    print(stats.summary())

    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
