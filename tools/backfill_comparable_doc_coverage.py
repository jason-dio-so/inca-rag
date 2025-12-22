#!/usr/bin/env python3
"""
U-4.18-Ω: 비교 가능 문서(가입설계서/상품요약서/사업방법서) coverage_code 백필

coverage_alias에 등록된 담보명이 chunk content에 존재하면
해당 chunk에 coverage_code를 태깅한다.

원칙:
- coverage_alias/coverage_name_map을 기준으로만 태깅
- coverage_standard에 존재하는 coverage_code만 허용
- 임의 추론/LLM 재해석 금지
- 짧은 alias(6글자 이하)는 오매칭 방지를 위해 제외
- 애매한 경우 태깅하지 않음

Usage:
    python tools/backfill_comparable_doc_coverage.py
    python tools/backfill_comparable_doc_coverage.py --dry-run
    python tools/backfill_comparable_doc_coverage.py --insurer SAMSUNG
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# 모듈 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ingestion.normalize import normalize_coverage_name


# 최소 alias 길이 (오매칭 방지)
MIN_ALIAS_LENGTH = 7

# 짧은 alias 중 예외적으로 허용할 패턴 (매우 특정적인 담보명)
ALLOWED_SHORT_ALIASES = {
    # 현재 없음 - 필요시 추가
}


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


@dataclass
class BackfillStats:
    """백필 통계"""
    total_chunks: int = 0
    already_tagged: int = 0
    matched: int = 0
    updated: int = 0
    no_match: int = 0
    errors: list[str] = field(default_factory=list)

    # 보험사별 통계
    by_insurer: dict[str, dict[str, int]] = field(default_factory=dict)

    def add_insurer_stat(self, insurer: str, key: str, count: int = 1) -> None:
        if insurer not in self.by_insurer:
            self.by_insurer[insurer] = {"matched": 0, "updated": 0, "no_match": 0}
        if key in self.by_insurer[insurer]:
            self.by_insurer[insurer][key] += count

    def summary(self) -> str:
        lines = [
            "",
            "=" * 70,
            "U-4.18-Ω: Comparable Doc Coverage Code Backfill 결과",
            "=" * 70,
            f"  총 chunk 수 (비교 가능 문서): {self.total_chunks}",
            f"  이미 태깅됨: {self.already_tagged}",
            f"  매칭됨: {self.matched}",
            f"  업데이트됨: {self.updated}",
            f"  매칭 실패: {self.no_match}",
            "",
            "보험사별 통계:",
        ]

        for insurer, stats in sorted(self.by_insurer.items()):
            lines.append(f"  {insurer}: matched={stats['matched']}, updated={stats['updated']}, no_match={stats['no_match']}")

        if self.errors:
            lines.append("")
            lines.append(f"  에러: {len(self.errors)}")
            for err in self.errors[:5]:
                lines.append(f"    - {err}")

        lines.append("=" * 70)
        return "\n".join(lines)


def load_canonical_coverage_codes(conn: psycopg.Connection) -> set[str]:
    """
    coverage_standard에 등록된 신정원 기준 coverage_code 로드
    """
    codes: set[str] = set()

    with conn.cursor() as cur:
        cur.execute("SELECT coverage_code FROM coverage_standard")
        for row in cur.fetchall():
            codes.add(row["coverage_code"])

    return codes


def is_valid_alias(raw_name_norm: str) -> bool:
    """
    alias가 backfill에 사용 가능한지 검증

    - 최소 길이 체크 (오매칭 방지)
    - 예외 허용 목록 체크
    """
    if not raw_name_norm:
        return False

    # 예외 허용 목록에 있으면 통과
    if raw_name_norm in ALLOWED_SHORT_ALIASES:
        return True

    # 최소 길이 체크
    if len(raw_name_norm) < MIN_ALIAS_LENGTH:
        return False

    return True


def load_coverage_aliases(
    conn: psycopg.Connection,
    canonical_codes: set[str],
) -> tuple[dict[int, list[dict]], dict[str, int]]:
    """
    보험사별 coverage_alias 로드 (필터링 적용)

    - coverage_standard에 존재하는 coverage_code만 허용
    - 최소 길이 미만 alias 제외

    Returns:
        (aliases_dict, filter_stats)
        aliases_dict: {insurer_id: [{coverage_code, raw_name, raw_name_norm}, ...]}
        filter_stats: {"total": N, "valid": N, "short_excluded": N, "non_canonical": N}
    """
    aliases: dict[int, list[dict]] = {}
    stats = {"total": 0, "valid": 0, "short_excluded": 0, "non_canonical": 0}

    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                ca.insurer_id,
                ca.coverage_code,
                ca.raw_name,
                ca.raw_name_norm,
                i.insurer_code
            FROM coverage_alias ca
            JOIN insurer i ON ca.insurer_id = i.insurer_id
            ORDER BY ca.insurer_id, LENGTH(ca.raw_name_norm) DESC
        """)

        for row in cur.fetchall():
            stats["total"] += 1

            coverage_code = row["coverage_code"]
            raw_name_norm = row["raw_name_norm"]

            # 신정원 기준 코드인지 검증
            if coverage_code not in canonical_codes:
                stats["non_canonical"] += 1
                continue

            # alias 길이 검증
            if not is_valid_alias(raw_name_norm):
                stats["short_excluded"] += 1
                continue

            stats["valid"] += 1

            insurer_id = row["insurer_id"]
            if insurer_id not in aliases:
                aliases[insurer_id] = []

            aliases[insurer_id].append({
                "coverage_code": coverage_code,
                "raw_name": row["raw_name"],
                "raw_name_norm": raw_name_norm,
                "insurer_code": row["insurer_code"],
            })

    return aliases, stats


def find_matching_coverage(
    content: str,
    aliases: list[dict],
) -> dict | None:
    """
    content에서 coverage_alias 매칭 찾기

    - 가장 긴 매칭을 우선 선택 (정확도 향상)
    - 정규화된 content에서 정규화된 alias 검색
    """
    content_norm = normalize_coverage_name(content)
    content_lower = content.lower()

    # 긴 alias부터 검색 (이미 정렬됨)
    for alias in aliases:
        raw_name_norm = alias["raw_name_norm"]

        # 1차: 정규화된 이름으로 검색
        if raw_name_norm and raw_name_norm in content_norm:
            return alias

        # 2차: 원본 이름 (소문자) 검색
        raw_name_lower = alias["raw_name"].lower()
        if raw_name_lower in content_lower:
            return alias

    return None


def backfill_coverage_codes(
    db_url: str | None = None,
    dry_run: bool = False,
    target_insurer: str | None = None,
) -> BackfillStats:
    """비교 가능 문서의 coverage_code 백필"""
    stats = BackfillStats()

    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)

    try:
        # 1. 신정원 기준 coverage_code 로드
        canonical_codes = load_canonical_coverage_codes(conn)
        print(f"Loaded {len(canonical_codes)} canonical coverage codes from coverage_standard")

        # 2. coverage_alias 로드 (필터링 적용)
        all_aliases, alias_stats = load_coverage_aliases(conn, canonical_codes)
        total_aliases = sum(len(v) for v in all_aliases.values())
        print(f"Loaded {total_aliases} valid coverage aliases for {len(all_aliases)} insurers")
        print(f"  - Total aliases: {alias_stats['total']}")
        print(f"  - Valid aliases: {alias_stats['valid']}")
        print(f"  - Short excluded (<{MIN_ALIAS_LENGTH} chars): {alias_stats['short_excluded']}")
        print(f"  - Non-canonical excluded: {alias_stats['non_canonical']}")

        # 3. 대상 chunk 조회
        with conn.cursor() as cur:
            query = """
                SELECT
                    c.chunk_id,
                    c.insurer_id,
                    c.doc_type,
                    c.content,
                    c.meta,
                    i.insurer_code
                FROM chunk c
                JOIN insurer i ON c.insurer_id = i.insurer_id
                WHERE c.doc_type IN ('가입설계서', '상품요약서', '사업방법서')
            """
            params = []

            if target_insurer:
                query += " AND i.insurer_code = %s"
                params.append(target_insurer)

            query += " ORDER BY c.insurer_id, c.chunk_id"

            cur.execute(query, params)
            chunks = cur.fetchall()

        stats.total_chunks = len(chunks)
        print(f"Processing {stats.total_chunks} chunks from comparable docs...")

        # 4. 각 chunk 처리
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            insurer_id = chunk["insurer_id"]
            insurer_code = chunk["insurer_code"]
            content = chunk["content"]
            meta = chunk["meta"] or {}
            entities = meta.get("entities", {})

            # 이미 coverage_code가 있으면 스킵
            existing_code = entities.get("coverage_code")
            if existing_code:
                stats.already_tagged += 1
                continue

            # 해당 보험사의 alias 가져오기
            aliases = all_aliases.get(insurer_id, [])
            if not aliases:
                stats.no_match += 1
                stats.add_insurer_stat(insurer_code, "no_match")
                continue

            # 매칭 찾기
            match = find_matching_coverage(content, aliases)

            if match:
                stats.matched += 1
                stats.add_insurer_stat(insurer_code, "matched")

                # meta.entities 업데이트
                entities["coverage_code"] = match["coverage_code"]
                entities["coverage_name"] = match["raw_name"]
                entities["match_source"] = "backfill_alias"
                meta["entities"] = entities

                if dry_run:
                    print(f"[DRY-RUN] chunk_id={chunk_id} ({insurer_code}): {match['coverage_code']} ({match['raw_name'][:30]}...)")
                else:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE chunk
                                SET meta = %s
                                WHERE chunk_id = %s
                                """,
                                (json.dumps(meta, ensure_ascii=False), chunk_id),
                            )
                        conn.commit()
                        stats.updated += 1
                        stats.add_insurer_stat(insurer_code, "updated")
                    except Exception as e:
                        stats.errors.append(f"chunk_id={chunk_id}: {e}")
                        conn.rollback()
            else:
                stats.no_match += 1
                stats.add_insurer_stat(insurer_code, "no_match")

        print(f"Backfill completed.")

    finally:
        conn.close()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="U-4.18-Ω: 비교 가능 문서 coverage_code 백필",
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
    parser.add_argument(
        "--insurer",
        type=str,
        default=None,
        help="특정 보험사만 처리 (예: SAMSUNG)",
    )

    args = parser.parse_args()

    stats = backfill_coverage_codes(
        db_url=args.db_url,
        dry_run=args.dry_run,
        target_insurer=args.insurer,
    )

    print(stats.summary())

    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
