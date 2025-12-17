#!/usr/bin/env python3
"""
Ontology Code → 신정원 표준코드 매핑 Seed 스크립트

coverage_standard.meta.ontology_codes에 ontology 코드 별칭을 저장하여
fallback 시 리매핑이 가능하도록 함

Usage:
    python tools/seed_ontology_codes.py
    python tools/seed_ontology_codes.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


# ============================================================================
# Ontology Code → 신정원 Coverage Code 매핑
# ============================================================================
# 주의: 1:1 매핑이 아닌 경우 가장 대표적인 코드로 매핑
# 여러 ontology 코드가 같은 신정원 코드에 매핑될 수 있음
ONTOLOGY_TO_STANDARD: dict[str, str] = {
    # 암 관련
    "CANCER_DIAG": "A4200_1",           # 암진단비(유사암제외)
    "THYROID_CANCER": "A4210",          # 갑상선암 → 유사암진단비
    "CIS_CARCINOMA": "A4210",           # 제자리암 → 유사암진단비
    "BORDERLINE_TUMOR": "A4210",        # 경계성종양 → 유사암진단비
    "BREAST_CANCER": "A4200_1",         # 유방암 → 암진단비
    "STOMACH_CANCER": "A4200_1",        # 위암 → 암진단비
    "LIVER_CANCER": "A4200_1",          # 간암 → 암진단비
    "LUNG_CANCER": "A4200_1",           # 폐암 → 암진단비
    "PROSTATE_CANCER": "A4200_1",       # 전립선암 → 암진단비

    # 뇌/심장 질환
    "STROKE": "A4103",                  # 뇌졸중 → 뇌졸중진단비
    "ACUTE_MI": "A4105",                # 급성심근경색 → 허혈성심장질환진단비

    # 수술/진단/입원
    "SURGERY": "A5100",                 # 수술비 → 질병수술비
    "DIAGNOSIS_BENEFIT": "A4200_1",     # 진단비 → 암진단비(대표)
    "HOSPITALIZATION": "A6100_1",       # 입원일당 → 질병입원비

    # 사망/장해
    "DEATH_BENEFIT": "A1100",           # 사망보험금 → 질병사망
    "DISABILITY": "A3300_1",            # 장해급여금 → 상해후유장해

    # 기타
    "CI_BENEFIT": "A4200_1",            # 중대한질병 → 암진단비(대표)
}


@dataclass
class SeedStats:
    """Seed 통계"""
    total_mappings: int = 0
    updated: int = 0
    not_found: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "",
            "=" * 60,
            "Ontology Code Seed 결과",
            "=" * 60,
            f"  총 매핑 수: {self.total_mappings}",
            f"  업데이트 성공: {self.updated}",
            f"  coverage_code 없음: {len(self.not_found)}",
        ]
        if self.not_found:
            for code in self.not_found:
                lines.append(f"    - {code}")
        if self.errors:
            lines.append(f"  에러: {len(self.errors)}")
            for err in self.errors[:5]:
                lines.append(f"    - {err}")
        lines.append("=" * 60)
        return "\n".join(lines)


def seed_ontology_codes(
    db_url: str | None = None,
    dry_run: bool = False,
) -> SeedStats:
    """
    coverage_standard.meta.ontology_codes에 ontology 코드 매핑 저장
    """
    stats = SeedStats()
    stats.total_mappings = len(ONTOLOGY_TO_STANDARD)

    # 역방향 매핑 생성: coverage_code → [ontology_codes]
    standard_to_ontology: dict[str, list[str]] = {}
    for ont_code, std_code in ONTOLOGY_TO_STANDARD.items():
        if std_code not in standard_to_ontology:
            standard_to_ontology[std_code] = []
        standard_to_ontology[std_code].append(ont_code)

    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)

    try:
        with conn.cursor() as cur:
            # 각 coverage_code에 대해 ontology_codes 업데이트
            for std_code, ont_codes in standard_to_ontology.items():
                # 존재 여부 확인
                cur.execute(
                    "SELECT coverage_code, meta FROM coverage_standard WHERE coverage_code = %s",
                    (std_code,),
                )
                row = cur.fetchone()

                if not row:
                    stats.not_found.append(std_code)
                    continue

                # 기존 meta 가져오기
                existing_meta = row["meta"] or {}
                existing_codes = existing_meta.get("ontology_codes", [])

                # 새 코드 추가 (중복 제거)
                new_codes = list(set(existing_codes + ont_codes))
                new_codes.sort()

                if new_codes == existing_codes:
                    # 변경 없음
                    continue

                existing_meta["ontology_codes"] = new_codes

                if dry_run:
                    print(f"[DRY-RUN] {std_code}: ontology_codes = {new_codes}")
                    stats.updated += 1
                else:
                    try:
                        cur.execute(
                            """
                            UPDATE coverage_standard
                            SET meta = %s
                            WHERE coverage_code = %s
                            """,
                            (json.dumps(existing_meta), std_code),
                        )
                        conn.commit()
                        stats.updated += 1
                        print(f"Updated {std_code}: ontology_codes = {new_codes}")
                    except Exception as e:
                        stats.errors.append(f"{std_code}: {e}")
                        conn.rollback()

    finally:
        conn.close()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ontology Code → 신정원 표준코드 매핑 Seed",
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

    print("Ontology Code → 신정원 표준코드 매핑")
    print("-" * 40)
    for ont, std in sorted(ONTOLOGY_TO_STANDARD.items()):
        print(f"  {ont} → {std}")
    print("-" * 40)

    stats = seed_ontology_codes(
        db_url=args.db_url,
        dry_run=args.dry_run,
    )

    print(stats.summary())

    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
