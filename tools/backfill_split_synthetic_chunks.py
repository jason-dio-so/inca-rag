#!/usr/bin/env python3
"""
V1.6.3 Split Synthetic Chunk Backfill

Mixed Coverage Chunk(하나의 chunk에 여러 담보 혼합)를 구조적으로 분해하여
담보별 synthetic chunk를 생성하는 스크립트.

핵심 원칙:
- 기존 chunk 절대 수정 금지 (INSERT ONLY)
- 신정원 canonical coverage_code만 사용
- LLM 추론 금지, 규칙 기반만 사용
- 매핑 실패 시 리포트만 생성

사용법:
    python tools/backfill_split_synthetic_chunks.py --scan        # 후보 스캔만
    python tools/backfill_split_synthetic_chunks.py --dry-run     # 미리보기
    python tools/backfill_split_synthetic_chunks.py               # 실제 실행
    python tools/backfill_split_synthetic_chunks.py --insurer SAMSUNG  # 특정 보험사만
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor

from services.extraction.amount_extractor import extract_amount


@dataclass
class CoverageLine:
    """담보 라인 추출 결과"""
    line_number: int
    raw_line: str
    raw_name: str | None = None
    coverage_code: str | None = None
    amount_value: int | None = None
    amount_text: str | None = None
    mapping_source: str | None = None  # 'coverage_alias' | 'coverage_name_map' | None


@dataclass
class MixedChunkCandidate:
    """혼합 담보 chunk 후보"""
    chunk_id: int
    insurer_id: int
    insurer_code: str
    document_id: int
    doc_type: str
    page_start: int | None
    page_end: int | None
    content: str
    current_coverage_code: str | None
    coverage_lines: list[CoverageLine] = field(default_factory=list)


@dataclass
class SyntheticChunkResult:
    """Synthetic chunk 생성 결과"""
    source_chunk_id: int
    insurer_code: str
    coverage_code: str
    raw_name: str
    amount_value: int
    amount_text: str
    new_chunk_id: int | None = None
    status: str = "pending"  # pending | created | skipped | error


# 담보명 키워드 (담보 라인 식별용)
COVERAGE_KEYWORDS = [
    "진단비", "수술비", "치료비", "입원비", "사망", "보험금", "보장",
    "일당", "간병비", "요양비",
]

# 담보명 추출 패턴 - 더 유연하게
COVERAGE_NAME_PATTERNS = [
    # 유사암 진단비(세부)(조건) 패턴 - SAMSUNG 형식
    r'(유사암\s*진단비\s*\([^)]+\)\s*\([^)]*\))',
    # 진단비/수술비 등 (조건) 패턴
    r'([가-힣\s]+(?:진단비|수술비|치료비|입원비|보험금)\s*\([^)]+\)(?:\s*\([^)]*\))?)',
    # 일반 담보명 패턴
    r'([가-힣\s]+(?:진단비|수술비|치료비|입원비|보험금|사망|보장))',
]

# 금액 패턴
AMOUNT_PATTERN = re.compile(
    r'(\d{1,3}(?:,\d{3})*)\s*(만\s*원|천만\s*원|억\s*원|원)'
    r'|(\d+)\s*(만\s*원|천만\s*원|억\s*원)'
)


def get_db_connection():
    """DB 연결 생성"""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "inca_rag"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def get_coverage_alias_map(conn, insurer_id: int) -> dict[str, str]:
    """
    보험사별 coverage_alias 매핑 조회
    Returns: {raw_name_norm: coverage_code}
    """
    query = """
    SELECT raw_name_norm, coverage_code
    FROM coverage_alias
    WHERE insurer_id = %s
    ORDER BY length(raw_name_norm) DESC  -- 긴 것 먼저 (더 구체적)
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (insurer_id,))
        rows = cur.fetchall()

    return {row["raw_name_norm"]: row["coverage_code"] for row in rows}


def get_coverage_standard_map(conn) -> dict[str, str]:
    """
    coverage_standard 매핑 조회 (canonical)
    Returns: {coverage_name: coverage_code}
    """
    query = """
    SELECT coverage_code, coverage_name
    FROM coverage_standard
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()

    return {row["coverage_name"]: row["coverage_code"] for row in rows}


def normalize_coverage_name(raw_name: str) -> str:
    """담보명 정규화 (매칭용)"""
    # 공백 정규화
    normalized = re.sub(r'\s+', ' ', raw_name.strip())
    # 특수문자 제거 (괄호 제외)
    normalized = re.sub(r'[^\w\s\(\)\[\]가-힣]', '', normalized)
    return normalized.lower()


def extract_coverage_lines(content: str, insurer_id: int, conn) -> list[CoverageLine]:
    """
    chunk content에서 담보 라인 추출

    전략:
    1. 전체 content에서 담보명 패턴 찾기
    2. 담보명 주변(±5줄)에서 금액 패턴 찾기
    3. coverage_code 매핑
    """
    lines = content.split('\n')
    coverage_lines: list[CoverageLine] = []

    # 보험사별 alias 맵 조회
    alias_map = get_coverage_alias_map(conn, insurer_id)
    standard_map = get_coverage_standard_map(conn)

    # 금액 패턴
    amount_pattern = re.compile(r'(\d{1,3}(?:,\d{3})*)\s*만\s*원|(\d+)\s*만\s*원|(\d+)\s*억\s*원')

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 담보명 패턴 매칭
        raw_name = None
        for pattern in COVERAGE_NAME_PATTERNS:
            match = re.search(pattern, line_stripped)
            if match:
                raw_name = match.group(1).strip()
                break

        if not raw_name:
            continue

        # 담보명 키워드 확인 (너무 짧거나 관련 없는 것 제외)
        if len(raw_name) < 4:
            continue
        if not any(kw in raw_name for kw in COVERAGE_KEYWORDS):
            continue

        # 주변 라인(현재 라인 ~ +5줄)에서 금액 찾기
        amount_value = None
        amount_text = None
        amount_line = None

        for j in range(i, min(i + 6, len(lines))):
            amount_match = amount_pattern.search(lines[j])
            if amount_match:
                # 금액 파싱
                if amount_match.group(1):  # X,XXX만원
                    num_str = amount_match.group(1).replace(",", "")
                    amount_value = int(num_str) * 10000
                    amount_text = amount_match.group(0)
                elif amount_match.group(2):  # X만원
                    amount_value = int(amount_match.group(2)) * 10000
                    amount_text = amount_match.group(0)
                elif amount_match.group(3):  # X억원
                    amount_value = int(amount_match.group(3)) * 100000000
                    amount_text = amount_match.group(0)

                if amount_value:
                    amount_line = lines[j].strip()
                    break

        if not amount_value:
            continue

        # 합쳐진 raw_line 생성
        raw_line = f"{raw_name} {amount_text}"

        coverage_line = CoverageLine(
            line_number=i,
            raw_line=raw_line,
            raw_name=raw_name,
            amount_value=amount_value,
            amount_text=amount_text,
        )

        # coverage_code 매핑 시도
        normalized = normalize_coverage_name(raw_name)

        # 1. coverage_alias에서 매칭 시도
        for alias_norm, code in alias_map.items():
            # 부분 매칭 (alias가 담보명에 포함되거나 담보명이 alias에 포함)
            if alias_norm in normalized or normalized in alias_norm:
                coverage_line.coverage_code = code
                coverage_line.mapping_source = "coverage_alias"
                break

        # 2. coverage_standard에서 매칭 시도
        if not coverage_line.coverage_code:
            for std_name, code in standard_map.items():
                std_normalized = normalize_coverage_name(std_name)
                if std_normalized in normalized or normalized in std_normalized:
                    coverage_line.coverage_code = code
                    coverage_line.mapping_source = "coverage_standard"
                    break

        coverage_lines.append(coverage_line)

    return coverage_lines


def scan_mixed_chunks(
    conn,
    insurer_code: str | None = None,
    doc_types: list[str] | None = None,
    limit: int | None = None,
) -> list[MixedChunkCandidate]:
    """
    혼합 담보 chunk 후보 스캔

    조건:
    - 비교 가능 문서 (가입설계서, 상품요약서, 사업방법서)
    - 진단비/수술비 패턴 2개 이상
    - 금액 패턴 존재
    """
    if doc_types is None:
        doc_types = ["가입설계서", "상품요약서", "사업방법서"]

    query = """
    SELECT
        c.chunk_id,
        c.insurer_id,
        i.insurer_code,
        c.document_id,
        d.doc_type,
        c.page_start,
        c.page_end,
        c.content,
        c.meta->'entities'->>'coverage_code' as current_coverage_code
    FROM chunk c
    JOIN insurer i ON c.insurer_id = i.insurer_id
    JOIN document d ON d.document_id = c.document_id
    WHERE d.doc_type = ANY(%s)
      AND (
        -- 진단비 패턴 2개 이상
        (length(c.content) - length(replace(c.content, '진단비', ''))) / 6 >= 2
        OR
        -- 수술비 패턴 2개 이상
        (length(c.content) - length(replace(c.content, '수술비', ''))) / 6 >= 2
      )
      AND c.content ~ '\d+만\s*원'
      -- synthetic chunk 제외
      AND (c.meta->'is_synthetic')::boolean IS NOT TRUE
    """

    params: list = [doc_types]

    if insurer_code:
        query += " AND i.insurer_code = %s"
        params.append(insurer_code)

    query += " ORDER BY i.insurer_code, c.chunk_id"

    if limit:
        query += " LIMIT %s"
        params.append(limit)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    candidates = []
    for row in rows:
        candidate = MixedChunkCandidate(
            chunk_id=row["chunk_id"],
            insurer_id=row["insurer_id"],
            insurer_code=row["insurer_code"],
            document_id=row["document_id"],
            doc_type=row["doc_type"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            content=row["content"],
            current_coverage_code=row["current_coverage_code"],
        )

        # 담보 라인 추출
        candidate.coverage_lines = extract_coverage_lines(
            row["content"], row["insurer_id"], conn
        )

        # 매핑 성공한 라인이 1개 이상 있으면 후보로 추가
        if any(line.coverage_code for line in candidate.coverage_lines):
            candidates.append(candidate)

    return candidates


def check_existing_synthetic(conn, source_chunk_id: int, coverage_code: str) -> bool:
    """기존 synthetic chunk 존재 여부 확인 (Idempotent)"""
    query = """
    SELECT 1 FROM chunk
    WHERE (meta->>'synthetic_source_chunk_id')::int = %s
      AND meta->'entities'->>'coverage_code' = %s
    LIMIT 1
    """

    with conn.cursor() as cur:
        cur.execute(query, (source_chunk_id, coverage_code))
        return cur.fetchone() is not None


def insert_synthetic_chunk(
    conn,
    candidate: MixedChunkCandidate,
    coverage_line: CoverageLine,
    dry_run: bool = False,
) -> SyntheticChunkResult:
    """
    Synthetic chunk INSERT

    원칙:
    - 기존 chunk 수정 금지
    - 1 담보 = 1 synthetic chunk
    """
    result = SyntheticChunkResult(
        source_chunk_id=candidate.chunk_id,
        insurer_code=candidate.insurer_code,
        coverage_code=coverage_line.coverage_code,
        raw_name=coverage_line.raw_name,
        amount_value=coverage_line.amount_value,
        amount_text=coverage_line.amount_text,
    )

    if dry_run:
        result.status = "dry_run"
        return result

    # Idempotent 체크
    if check_existing_synthetic(conn, candidate.chunk_id, coverage_line.coverage_code):
        result.status = "skipped_existing"
        return result

    # Synthetic chunk content
    content = f"""[SYNTHETIC]
{coverage_line.raw_line}

[V1.6.3 Split: source_chunk_id={candidate.chunk_id}]"""

    # Meta 구성
    meta = {
        "is_synthetic": True,
        "synthetic_method": "split_line_v1",
        "synthetic_source_chunk_id": candidate.chunk_id,
        "raw_name": coverage_line.raw_name,
        "raw_line_excerpt": coverage_line.raw_line[:200],
        "entities": {
            "coverage_code": coverage_line.coverage_code,
            "amount": {
                "amount_value": coverage_line.amount_value,
                "amount_text": coverage_line.amount_text,
                "method": "v1.6.3_split",
                "confidence": "high" if coverage_line.mapping_source == "coverage_alias" else "medium",
            },
        },
    }

    insert_query = """
    INSERT INTO chunk (document_id, insurer_id, doc_type, content, meta, page_start, page_end)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING chunk_id
    """

    try:
        with conn.cursor() as cur:
            cur.execute(
                insert_query,
                (
                    candidate.document_id,
                    candidate.insurer_id,
                    candidate.doc_type,
                    content,
                    json.dumps(meta),
                    candidate.page_start,
                    candidate.page_end,
                ),
            )
            result.new_chunk_id = cur.fetchone()[0]
            result.status = "created"
    except Exception as e:
        result.status = f"error: {str(e)}"

    return result


def run_backfill(
    insurer_code: str | None = None,
    doc_types: list[str] | None = None,
    dry_run: bool = False,
    scan_only: bool = False,
    limit: int | None = None,
    batch_size: int = 100,
) -> tuple[list[MixedChunkCandidate], list[SyntheticChunkResult], list[CoverageLine]]:
    """
    V1.6.3 Split Synthetic Chunk Backfill 실행

    Returns:
        (candidates, results, unmapped_lines)
    """
    conn = get_db_connection()

    try:
        # STEP 1: 혼합 chunk 후보 스캔
        print("[STEP 1] Scanning mixed coverage chunks...")
        candidates = scan_mixed_chunks(conn, insurer_code, doc_types, limit)
        print(f"  Found {len(candidates)} candidate chunks")

        if scan_only:
            return candidates, [], []

        # STEP 2-4: 각 후보에서 담보 라인 분해 및 synthetic chunk 생성
        print("\n[STEP 2-4] Processing coverage lines...")

        results: list[SyntheticChunkResult] = []
        unmapped_lines: list[CoverageLine] = []

        created_count = 0
        skipped_count = 0

        for i, candidate in enumerate(candidates):
            for line in candidate.coverage_lines:
                if line.coverage_code:
                    # 매핑 성공 → synthetic chunk 생성
                    result = insert_synthetic_chunk(conn, candidate, line, dry_run)
                    results.append(result)

                    if result.status == "created":
                        created_count += 1
                    elif result.status.startswith("skipped"):
                        skipped_count += 1
                else:
                    # 매핑 실패 → 리포트용
                    unmapped_lines.append(line)

            # 배치 커밋
            if not dry_run and (i + 1) % batch_size == 0:
                conn.commit()
                print(f"  Progress: {i + 1}/{len(candidates)} chunks processed")

        # 최종 커밋
        if not dry_run:
            conn.commit()

        # Summary
        print(f"\n[SUMMARY]")
        print(f"  Candidates scanned: {len(candidates)}")
        print(f"  Coverage lines found: {len(results) + len(unmapped_lines)}")
        print(f"  Mapped lines: {len(results)}")
        print(f"  Unmapped lines: {len(unmapped_lines)}")
        if not dry_run:
            print(f"  Synthetic chunks created: {created_count}")
            print(f"  Skipped (existing): {skipped_count}")

        return candidates, results, unmapped_lines

    finally:
        conn.close()


def save_candidates_report(candidates: list[MixedChunkCandidate], output_path: str):
    """mixed_chunk_candidates.csv 저장"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "chunk_id", "insurer_code", "document_id", "doc_type", "page_start",
            "current_code", "coverage_lines_count", "mapped_lines_count", "raw_names"
        ])

        for c in candidates:
            mapped_count = sum(1 for line in c.coverage_lines if line.coverage_code)
            raw_names = "; ".join(line.raw_name for line in c.coverage_lines if line.raw_name)

            writer.writerow([
                c.chunk_id, c.insurer_code, c.document_id, c.doc_type, c.page_start,
                c.current_coverage_code, len(c.coverage_lines), mapped_count, raw_names[:200]
            ])

    print(f"  Saved: {output_path}")


def save_unmapped_report(unmapped_lines: list[CoverageLine], output_path: str):
    """unmapped_lines_report.csv 저장"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["line_number", "raw_name", "amount_text", "raw_line_excerpt"])

        for line in unmapped_lines:
            writer.writerow([
                line.line_number,
                line.raw_name,
                line.amount_text,
                line.raw_line[:100] if line.raw_line else "",
            ])

    print(f"  Saved: {output_path}")


def save_results_report(results: list[SyntheticChunkResult], output_path: str):
    """synthetic_chunks_created.csv 저장"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "source_chunk_id", "insurer_code", "coverage_code", "raw_name",
            "amount_value", "amount_text", "new_chunk_id", "status"
        ])

        for r in results:
            writer.writerow([
                r.source_chunk_id, r.insurer_code, r.coverage_code, r.raw_name,
                r.amount_value, r.amount_text, r.new_chunk_id, r.status
            ])

    print(f"  Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="V1.6.3 Split Synthetic Chunk Backfill - Mixed Coverage Chunk 분해"
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="혼합 chunk 후보 스캔만 수행 (INSERT 없음)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="INSERT 없이 미리보기만",
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
        help="처리할 doc_type 목록",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처리할 최대 chunk 수",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/v1_6_3",
        help="리포트 출력 디렉토리",
    )

    args = parser.parse_args()

    print(f"[V1.6.3 Split Synthetic Chunk Backfill]")
    print(f"  mode: {'scan' if args.scan else 'dry-run' if args.dry_run else 'execute'}")
    print(f"  insurer: {args.insurer or 'ALL'}")
    print(f"  doc_types: {args.doc_types}")
    print(f"  limit: {args.limit or 'NONE'}")
    print()

    # 실행
    candidates, results, unmapped = run_backfill(
        insurer_code=args.insurer,
        doc_types=args.doc_types,
        dry_run=args.dry_run,
        scan_only=args.scan,
        limit=args.limit,
    )

    # 리포트 저장
    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    save_candidates_report(
        candidates,
        os.path.join(args.output_dir, f"mixed_chunk_candidates_{timestamp}.csv")
    )

    if unmapped:
        save_unmapped_report(
            unmapped,
            os.path.join(args.output_dir, f"unmapped_lines_report_{timestamp}.csv")
        )

    if results:
        save_results_report(
            results,
            os.path.join(args.output_dir, f"synthetic_chunks_created_{timestamp}.csv")
        )


if __name__ == "__main__":
    main()
