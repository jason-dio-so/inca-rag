#!/usr/bin/env python3
"""
Coverage Mapping 로더

담보명mapping자료.xlsx를 읽어 DB에 coverage_standard/coverage_alias 테이블 적재

Usage:
    python tools/load_coverage_mapping.py --xlsx data/담보명mapping자료.xlsx
    python tools/load_coverage_mapping.py --xlsx data/담보명mapping자료.xlsx --dry-run
    python tools/load_coverage_mapping.py --xlsx data/담보명mapping자료.xlsx --strict
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from psycopg.rows import dict_row

# 모듈 경로 설정 (services/ingestion 접근용)
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ingestion.normalize import normalize_coverage_name


def get_db_url() -> str:
    """환경변수에서 DB URL 가져오기"""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


# ============================================================================
# ins_cd → insurer_code 매핑 (엑셀의 ins_cd → 우리 시스템의 insurer_code)
# ============================================================================
INS_CODE_MAP: dict[str, str] = {
    "N01": "MERITZ",
    "N02": "HANWHA",
    "N03": "LOTTE",
    "N05": "HEUNGKUK",
    "N08": "SAMSUNG",
    "N09": "HYUNDAI",
    "N10": "KB",
    "N13": "DB",
}

# 보험사명 → insurer_code 매핑 (ins_cd 매핑 실패 시 fallback)
INSURER_NAME_MAP: dict[str, str] = {
    "메리츠": "MERITZ",
    "한화": "HANWHA",
    "롯데": "LOTTE",
    "흥국": "HEUNGKUK",
    "삼성": "SAMSUNG",
    "현대": "HYUNDAI",
    "KB": "KB",
    "DB": "DB",
}


@dataclass
class LoadStats:
    """로드 통계"""

    rows_read: int = 0
    insurers_resolved: int = 0
    standard_inserted: int = 0
    standard_updated: int = 0
    alias_inserted: int = 0
    alias_updated: int = 0
    alias_skipped: int = 0
    unmapped_ins_cd: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "",
            "=" * 60,
            "Coverage Mapping 로드 결과",
            "=" * 60,
            f"  총 rows 읽음: {self.rows_read}",
            f"  보험사 resolve: {self.insurers_resolved}",
            f"  표준코드 insert: {self.standard_inserted}",
            f"  표준코드 update: {self.standard_updated}",
            f"  Alias insert: {self.alias_inserted}",
            f"  Alias update: {self.alias_updated}",
            f"  Alias skip: {self.alias_skipped}",
        ]
        if self.unmapped_ins_cd:
            lines.append(f"  매핑 안 된 ins_cd: {sorted(self.unmapped_ins_cd)}")
        if self.errors:
            lines.append(f"  에러: {len(self.errors)}건")
            for err in self.errors[:10]:
                lines.append(f"    - {err}")
            if len(self.errors) > 10:
                lines.append(f"    ... 외 {len(self.errors) - 10}건")
        lines.append("=" * 60)
        return "\n".join(lines)


class CoverageMappingLoader:
    """Coverage Mapping 로더"""

    def __init__(
        self,
        db_url: str | None = None,
        strict: bool = False,
        create_missing_insurer: bool = False,
    ):
        """
        Args:
            db_url: DB URL (None이면 환경변수 사용)
            strict: True면 매핑 안 된 ins_cd 발견 시 에러
            create_missing_insurer: True면 없는 insurer 자동 생성
        """
        self._db_url = db_url or get_db_url()
        self._strict = strict
        self._create_missing_insurer = create_missing_insurer
        self._conn: psycopg.Connection | None = None
        self._insurer_cache: dict[str, int] = {}  # insurer_code -> insurer_id
        self._logger = logging.getLogger("coverage_loader")

    def connect(self) -> None:
        if self._conn is None:
            self._conn = psycopg.connect(self._db_url, row_factory=dict_row)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "CoverageMappingLoader":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None:
            self.connect()
        return self._conn  # type: ignore

    def resolve_insurer_id(self, insurer_code: str) -> int | None:
        """
        insurer_code로 insurer_id 조회

        Returns:
            insurer_id (BIGINT) 또는 None
        """
        if insurer_code in self._insurer_cache:
            return self._insurer_cache[insurer_code]

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT insurer_id FROM insurer WHERE insurer_code = %s",
                (insurer_code,),
            )
            row = cur.fetchone()
            if row:
                self._insurer_cache[insurer_code] = row["insurer_id"]
                return row["insurer_id"]

        # 없으면 생성 시도 (옵션)
        if self._create_missing_insurer:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO insurer (insurer_code, insurer_name)
                    VALUES (%s, %s)
                    RETURNING insurer_id
                    """,
                    (insurer_code, insurer_code),
                )
                row = cur.fetchone()
                self.conn.commit()
                if row:
                    self._insurer_cache[insurer_code] = row["insurer_id"]
                    self._logger.info(f"Created insurer: {insurer_code}")
                    return row["insurer_id"]

        return None

    def upsert_coverage_standard(
        self,
        coverage_code: str,
        coverage_name: str,
    ) -> tuple[bool, bool]:
        """
        coverage_standard upsert

        Returns:
            (inserted, updated)
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO coverage_standard (coverage_code, coverage_name)
                VALUES (%s, %s)
                ON CONFLICT (coverage_code)
                DO UPDATE SET coverage_name = EXCLUDED.coverage_name
                RETURNING (xmax = 0) AS inserted
                """,
                (coverage_code, coverage_name),
            )
            row = cur.fetchone()
            self.conn.commit()

            if row:
                inserted = row["inserted"]
                return inserted, not inserted

        return False, False

    def upsert_coverage_alias(
        self,
        insurer_id: int,
        coverage_code: str,
        raw_name: str,
        raw_name_norm: str,
        source_doc_type: str = "가입설계서",
    ) -> tuple[bool, bool]:
        """
        coverage_alias upsert

        Returns:
            (inserted, updated)
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO coverage_alias
                    (insurer_id, coverage_code, raw_name, raw_name_norm, source_doc_type)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (insurer_id, raw_name_norm, source_doc_type)
                DO UPDATE SET
                    raw_name = EXCLUDED.raw_name,
                    coverage_code = EXCLUDED.coverage_code
                RETURNING (xmax = 0) AS inserted
                """,
                (insurer_id, coverage_code, raw_name, raw_name_norm, source_doc_type),
            )
            row = cur.fetchone()
            self.conn.commit()

            if row:
                inserted = row["inserted"]
                return inserted, not inserted

        return False, False

    def load_from_dataframe(
        self,
        df: pd.DataFrame,
        dry_run: bool = False,
    ) -> LoadStats:
        """
        DataFrame에서 coverage mapping 로드

        Expected columns:
        - ins_cd: 보험사 코드 (N01, N02, ...)
        - 보험사명: 보험사 한글명
        - cre_cvr_cd: 표준 담보 코드
        - 신정원코드명: 표준 담보명
        - 담보명(가입설계서): 보험사별 실제 담보명
        """
        stats = LoadStats()
        stats.rows_read = len(df)

        # 1. 표준코드 수집 (중복 제거)
        standard_codes = df[["cre_cvr_cd", "신정원코드명"]].drop_duplicates()
        self._logger.info(f"표준코드 수: {len(standard_codes)}")

        if not dry_run:
            for _, row in standard_codes.iterrows():
                code = str(row["cre_cvr_cd"]).strip()
                name = str(row["신정원코드명"]).strip()

                if not code or code == "nan":
                    continue

                try:
                    inserted, updated = self.upsert_coverage_standard(code, name)
                    if inserted:
                        stats.standard_inserted += 1
                    if updated:
                        stats.standard_updated += 1
                except Exception as e:
                    stats.errors.append(f"Standard {code}: {e}")
        else:
            stats.standard_inserted = len(standard_codes)

        # 2. 보험사별 alias 처리
        insurers_seen: set[str] = set()

        for idx, row in df.iterrows():
            ins_cd = str(row["ins_cd"]).strip()
            insurer_name = str(row.get("보험사명", "")).strip()
            coverage_code = str(row["cre_cvr_cd"]).strip()
            raw_name = str(row["담보명(가입설계서)"]).strip()

            # 필수 값 체크
            if not coverage_code or coverage_code == "nan":
                continue
            if not raw_name or raw_name == "nan":
                stats.alias_skipped += 1
                continue

            # ins_cd → insurer_code 변환 (1순위)
            insurer_code: str | None = None
            if ins_cd and ins_cd != "nan":
                insurer_code = INS_CODE_MAP.get(ins_cd)

            # 보험사명 → insurer_code fallback (2순위)
            if not insurer_code and insurer_name and insurer_name != "nan":
                insurer_code = INSURER_NAME_MAP.get(insurer_name)

            # 둘 다 실패
            if not insurer_code:
                unmapped_key = ins_cd if (ins_cd and ins_cd != "nan") else insurer_name
                if unmapped_key:
                    stats.unmapped_ins_cd.add(unmapped_key)
                if self._strict:
                    raise ValueError(
                        f"Unknown ins_cd/보험사명: ins_cd={ins_cd}, 보험사명={insurer_name} (row {idx})"
                    )
                self._logger.warning(
                    f"Skip row {idx}: unmapped ins_cd={ins_cd}, 보험사명={insurer_name}"
                )
                stats.alias_skipped += 1
                continue

            insurers_seen.add(insurer_code)

            if dry_run:
                stats.alias_inserted += 1
                continue

            # insurer_id 조회
            insurer_id = self.resolve_insurer_id(insurer_code)
            if not insurer_id:
                stats.errors.append(f"Insurer not found: {insurer_code}")
                stats.alias_skipped += 1
                continue

            # 정규화 (공유 함수 사용)
            raw_name_norm = normalize_coverage_name(raw_name)

            if not raw_name_norm:
                stats.alias_skipped += 1
                continue

            try:
                inserted, updated = self.upsert_coverage_alias(
                    insurer_id=insurer_id,
                    coverage_code=coverage_code,
                    raw_name=raw_name,
                    raw_name_norm=raw_name_norm,
                    source_doc_type="가입설계서",
                )
                if inserted:
                    stats.alias_inserted += 1
                if updated:
                    stats.alias_updated += 1
            except Exception as e:
                stats.errors.append(f"Alias {insurer_code}/{raw_name}: {e}")
                stats.alias_skipped += 1

        stats.insurers_resolved = len(insurers_seen)

        return stats


def load_coverage_mapping(
    xlsx_path: Path,
    db_url: str | None = None,
    dry_run: bool = False,
    strict: bool = False,
    create_missing_insurer: bool = False,
) -> LoadStats:
    """
    엑셀 파일에서 coverage mapping 로드

    Args:
        xlsx_path: 엑셀 파일 경로
        db_url: DB URL
        dry_run: True면 실제 DB 쓰기 없이 통계만
        strict: True면 매핑 안 된 ins_cd 발견 시 에러
        create_missing_insurer: True면 없는 insurer 자동 생성

    Returns:
        LoadStats
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("coverage_loader")

    logger.info(f"Loading: {xlsx_path}")
    logger.info(f"Dry-run: {dry_run}, Strict: {strict}")

    # 엑셀 읽기
    df = pd.read_excel(xlsx_path)
    logger.info(f"Rows: {len(df)}")

    # 필수 컬럼 확인
    required_cols = ["ins_cd", "cre_cvr_cd", "신정원코드명", "담보명(가입설계서)"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if dry_run:
        # DB 없이 통계만
        stats = LoadStats()
        stats.rows_read = len(df)
        standard_codes = df[["cre_cvr_cd", "신정원코드명"]].drop_duplicates()
        stats.standard_inserted = len(standard_codes)

        # 매핑 가능한 row 수 및 unmapped 체크
        insurers_resolved: set[str] = set()
        for _, row in df.iterrows():
            ins_cd = str(row["ins_cd"]).strip()
            insurer_name = str(row.get("보험사명", "")).strip()

            insurer_code: str | None = None
            if ins_cd and ins_cd != "nan":
                insurer_code = INS_CODE_MAP.get(ins_cd)
            if not insurer_code and insurer_name and insurer_name != "nan":
                insurer_code = INSURER_NAME_MAP.get(insurer_name)

            if insurer_code:
                insurers_resolved.add(insurer_code)
                stats.alias_inserted += 1
            else:
                unmapped_key = ins_cd if (ins_cd and ins_cd != "nan") else insurer_name
                if unmapped_key:
                    stats.unmapped_ins_cd.add(unmapped_key)
                stats.alias_skipped += 1

        stats.insurers_resolved = len(insurers_resolved)
        return stats

    # DB 로드
    with CoverageMappingLoader(
        db_url,
        strict=strict,
        create_missing_insurer=create_missing_insurer,
    ) as loader:
        stats = loader.load_from_dataframe(df, dry_run=dry_run)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Coverage Mapping 로더",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python tools/load_coverage_mapping.py --xlsx data/담보명mapping자료.xlsx
  python tools/load_coverage_mapping.py --xlsx data/담보명mapping자료.xlsx --dry-run
  python tools/load_coverage_mapping.py --xlsx data/담보명mapping자료.xlsx --strict
        """,
    )

    parser.add_argument(
        "--xlsx",
        type=str,
        required=True,
        help="엑셀 파일 경로",
    )

    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (기본: DATABASE_URL 환경변수)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB 쓰기 없이 통계만 출력",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="매핑 안 된 ins_cd 발견 시 즉시 에러 종료",
    )

    parser.add_argument(
        "--create-missing-insurer",
        action="store_true",
        help="insurer 테이블에 없는 보험사 자동 생성",
    )

    args = parser.parse_args()

    # 경로 검증
    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        print(f"[ERROR] 파일이 없습니다: {xlsx_path}")
        return 1

    try:
        stats = load_coverage_mapping(
            xlsx_path=xlsx_path,
            db_url=args.db_url,
            dry_run=args.dry_run,
            strict=args.strict,
            create_missing_insurer=args.create_missing_insurer,
        )

        print(stats.summary())

        if stats.errors:
            return 1

        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
