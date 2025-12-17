#!/usr/bin/env python3
"""
약관(doc_type='약관') chunk의 coverage 태깅 재평가 스크립트

기존에 fallback_remap으로 태깅된 약관 chunk들을 새로운 clause_header 로직으로 재평가.
오탐(일반 단어 매칭)을 제거하고 헤더 패턴에서만 coverage를 추출.

Usage:
    python tools/backfill_terms_for_policy.py
    python tools/backfill_terms_for_policy.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field

import psycopg
from psycopg.rows import dict_row

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ingestion.coverage_extractor import CoverageExtractor, reset_extractor


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


@dataclass
class BackfillStats:
    """백필 통계"""
    total_chunks: int = 0
    fallback_remap_chunks: int = 0
    re_tagged_with_header: int = 0
    coverage_removed: int = 0
    unchanged: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "",
            "=" * 60,
            "약관 Coverage 재태깅 결과",
            "=" * 60,
            f"  총 약관 chunk: {self.total_chunks}",
            f"  기존 fallback_remap chunk: {self.fallback_remap_chunks}",
            f"  헤더 매칭으로 재태깅: {self.re_tagged_with_header}",
            f"  coverage 제거 (오탐): {self.coverage_removed}",
            f"  변경 없음: {self.unchanged}",
        ]
        if self.errors:
            lines.append(f"  에러: {len(self.errors)}")
            for err in self.errors[:5]:
                lines.append(f"    - {err}")
        lines.append("=" * 60)
        return "\n".join(lines)


def backfill_terms_coverage(
    db_url: str | None = None,
    dry_run: bool = False,
) -> BackfillStats:
    """
    약관 chunk의 coverage 태깅 재평가

    기존 fallback_remap → clause_header 로직으로 재평가
    헤더에서 매칭되지 않으면 coverage 제거 (오탐 방지)
    """
    stats = BackfillStats()

    # extractor 초기화 (캐시 리셋)
    reset_extractor()
    extractor = CoverageExtractor(db_url or get_db_url())

    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)

    try:
        with conn.cursor() as cur:
            # 약관 chunk 중 fallback_remap으로 태깅된 것들 조회
            cur.execute("""
                SELECT
                    chunk_id,
                    content,
                    meta,
                    insurer_id
                FROM chunk
                WHERE doc_type = '약관'
                  AND meta->'entities'->>'match_source' = 'fallback_remap'
            """)

            chunks = cur.fetchall()
            stats.fallback_remap_chunks = len(chunks)

            # 전체 약관 chunk 수
            cur.execute("SELECT COUNT(*) FROM chunk WHERE doc_type = '약관'")
            stats.total_chunks = cur.fetchone()["count"]

            for chunk in chunks:
                chunk_id = chunk["chunk_id"]
                content = chunk["content"]
                meta = chunk["meta"] or {}
                insurer_id = chunk["insurer_id"]

                old_entities = meta.get("entities", {})
                old_code = old_entities.get("coverage_code")
                old_ontology = old_entities.get("ontology_code")

                # 새 로직으로 재평가 (clause_header만)
                match = extractor.extract(content, insurer_id, doc_type="약관")
                new_entities = extractor.to_meta_entities(match)

                if match and match.code:
                    # 헤더에서 매칭됨
                    stats.re_tagged_with_header += 1
                    action = f"re-tagged: {old_ontology} → {match.match_source}:{match.code}"
                else:
                    # 헤더에서 매칭 안 됨 → 오탐으로 간주, coverage 제거
                    stats.coverage_removed += 1
                    new_entities = {
                        "match_source": "no_match",
                        "confidence": "none",
                    }
                    # 기존 ontology 정보는 참고용으로 보존
                    if old_ontology:
                        new_entities["removed_ontology_code"] = old_ontology
                    action = f"removed: {old_ontology} (false positive)"

                meta["entities"] = new_entities

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
            print("Backfill completed.")

    finally:
        extractor.close()
        conn.close()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="약관 chunk coverage 재태깅 (clause_header 로직)",
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

    print("약관 Coverage 재태깅 시작...")
    print("-" * 40)

    stats = backfill_terms_coverage(
        db_url=args.db_url,
        dry_run=args.dry_run,
    )

    print(stats.summary())

    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
