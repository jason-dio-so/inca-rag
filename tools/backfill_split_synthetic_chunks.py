#!/usr/bin/env python3
"""
V1.6.3-β-2 Split Synthetic Chunk Backfill (마감 패치)

Mixed Coverage Chunk(하나의 chunk에 여러 담보 혼합)를 구조적으로 분해하여
담보별 synthetic chunk를 생성하는 스크립트.

V1.6.3-β-2 핵심 변경 (마감 패치):
1. count-context 필터 실제 적용 (횟수/한도 숫자 오추출 차단)
2. synthetic meta 스키마 운영 기준 고정 (synthetic_method 추가)
3. amount.method = "v1_6_3_beta_2_split" 통일

V1.6.3-β 핵심 변경:
1. coverage_standard 자동 INSERT 금지 (coverage_alias 매핑만 허용)
2. amount_extractor 우선 사용 + payment-context 필터
3. 이상치 금액 필터 (< 10만원 스킵)
4. synthetic chunk meta 구조 보강 (provenance)

핵심 원칙:
- 기존 chunk 절대 수정 금지 (INSERT ONLY)
- 신정원 canonical coverage_code만 사용
- LLM 추론 금지, 규칙 기반만 사용
- 매핑 실패 시 리포트만 생성
- Fail closed: 애매하면 생성하지 말고 unmapped/rejected report로 남김

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
    confidence: str | None = None
    mapping_source: str | None = None  # 'coverage_alias' | 'coverage_standard_candidate' | None
    eligible_for_insert: bool = False  # V1.6.3-β: coverage_alias만 True
    reject_reason: str | None = None  # V1.6.3-β: 거절 사유


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
    mapping_source: str  # V1.6.3-β
    eligible_for_insert: bool  # V1.6.3-β
    reject_reason: str | None = None  # V1.6.3-β
    new_chunk_id: int | None = None
    status: str = "pending"  # pending | created | skipped_existing | rejected | error


# ============================================================================
# V1.6.3-β: 핵심 상수 정의
# ============================================================================

# 담보명 키워드 (담보 라인 식별용) - 필수 포함
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

# V1.6.3-β: 보험료/납입 문맥 금칙 키워드
PAYMENT_CONTEXT_KEYWORDS = [
    "보험료", "납입", "월납", "연납", "기본보험료", "적립", "환급",
    "수수료", "부담금", "자기부담", "갱신보험료", "납입면제", "1회차",
    "2회차", "회차별", "총보험료", "합계",
]

# V1.6.3-β: 횟수/한도 문맥 (금액이 아닌 숫자)
COUNT_CONTEXT_KEYWORDS = [
    "회한", "횟수", "지급횟수", "연간", "지급한도", "회당", "1회한", "연1회",
]

# V1.6.3-β: 최소 금액 임계값 (10만원 미만은 의심)
MIN_AMOUNT_THRESHOLD = 100_000


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
    V1.6.3-β: 보고서 기록용으로만 사용, 자동 INSERT 금지
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


def check_payment_context(window_text: str) -> bool:
    """
    V1.6.3-β: 보험료/납입 문맥인지 확인
    True면 금액 추출 스킵
    """
    window_lower = window_text.lower()
    for keyword in PAYMENT_CONTEXT_KEYWORDS:
        if keyword in window_lower:
            return True
    return False


def check_count_context(window_text: str) -> bool:
    """
    V1.6.3-β: 횟수/한도 문맥인지 확인
    True면 금액 추출 스킵
    """
    window_lower = window_text.lower()
    for keyword in COUNT_CONTEXT_KEYWORDS:
        if keyword in window_lower:
            return True
    return False


def extract_coverage_lines(content: str, insurer_id: int, doc_type: str, conn) -> list[CoverageLine]:
    """
    V1.6.3-β: chunk content에서 담보 라인 추출

    핵심 변경:
    1. coverage_alias 매핑만 eligible_for_insert=True
    2. coverage_standard 매핑은 report-only
    3. amount_extractor 우선 사용
    4. payment-context 필터 적용
    """
    lines = content.split('\n')
    coverage_lines: list[CoverageLine] = []

    # 보험사별 alias 맵 조회
    alias_map = get_coverage_alias_map(conn, insurer_id)
    standard_map = get_coverage_standard_map(conn)

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

        # V1.6.3-β: 담보명 최소 길이 4글자
        if len(raw_name) < 4:
            continue

        # V1.6.3-β: 담보 키워드 필수 포함
        if not any(kw in raw_name for kw in COVERAGE_KEYWORDS):
            continue

        # V1.6.3-β: 주변 윈도우 구성 (±5줄)
        window_start = max(0, i - 5)
        window_end = min(len(lines), i + 6)
        window_text = "\n".join(lines[window_start:window_end])

        # V1.6.3-β: amount_extractor 사용
        amount_result = extract_amount(window_text, doc_type=doc_type)

        # 기본 CoverageLine 생성
        coverage_line = CoverageLine(
            line_number=i,
            raw_line=line_stripped,
            raw_name=raw_name,
        )

        # 금액 추출 실패
        if amount_result.amount_value is None:
            coverage_line.reject_reason = "amount_not_found"
            coverage_lines.append(coverage_line)
            continue

        # V1.6.3-β: payment-context 필터
        if check_payment_context(window_text):
            coverage_line.reject_reason = "payment_context"
            coverage_lines.append(coverage_line)
            continue

        # V1.6.3-β-2: count-context(횟수/한도) 필터 - 실제 적용
        if check_count_context(window_text):
            coverage_line.reject_reason = "count_context"
            coverage_lines.append(coverage_line)
            continue

        # V1.6.3-β: 최소 금액 필터
        if amount_result.amount_value < MIN_AMOUNT_THRESHOLD:
            coverage_line.reject_reason = f"amount_too_small ({amount_result.amount_value})"
            coverage_lines.append(coverage_line)
            continue

        # 금액 정보 저장
        coverage_line.amount_value = amount_result.amount_value
        coverage_line.amount_text = amount_result.amount_text
        coverage_line.confidence = amount_result.confidence
        coverage_line.raw_line = f"{raw_name} {amount_result.amount_text}"

        # coverage_code 매핑
        normalized = normalize_coverage_name(raw_name)

        # V1.6.3-β: 1순위 - coverage_alias (자동 INSERT 허용)
        alias_matched = False
        for alias_norm, code in alias_map.items():
            # 양방향 포함 체크
            if alias_norm in normalized or normalized in alias_norm:
                coverage_line.coverage_code = code
                coverage_line.mapping_source = "coverage_alias"
                coverage_line.eligible_for_insert = True
                alias_matched = True
                break

        # V1.6.3-β: 2순위 - coverage_standard (report-only, INSERT 금지)
        if not alias_matched:
            for std_name, code in standard_map.items():
                std_normalized = normalize_coverage_name(std_name)
                if std_normalized in normalized or normalized in std_normalized:
                    coverage_line.coverage_code = code
                    coverage_line.mapping_source = "coverage_standard_candidate"
                    coverage_line.eligible_for_insert = False  # INSERT 금지
                    coverage_line.reject_reason = "coverage_standard_only"
                    break

        # 매핑 완전 실패
        if not coverage_line.coverage_code:
            coverage_line.reject_reason = "no_coverage_mapping"

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
      AND (c.meta->>'is_synthetic')::boolean IS NOT TRUE
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

        # V1.6.3-β: 담보 라인 추출 (doc_type 전달)
        candidate.coverage_lines = extract_coverage_lines(
            row["content"], row["insurer_id"], row["doc_type"], conn
        )

        # V1.6.3-β: eligible_for_insert인 라인이 1개 이상 있거나, 리포트용 라인이 있으면 후보로 추가
        if candidate.coverage_lines:
            candidates.append(candidate)

    return candidates


def check_existing_synthetic(
    conn,
    insurer_id: int,
    document_id: int,
    page_start: int | None,
    coverage_code: str,
    amount_value: int,
) -> bool:
    """
    V1.6.3-β: 기존 synthetic chunk 존재 여부 확인 (Idempotent)
    중복 키: (insurer_id, document_id, page_start, coverage_code, amount_value)
    """
    query = """
    SELECT 1 FROM chunk
    WHERE insurer_id = %s
      AND document_id = %s
      AND (page_start = %s OR (%s IS NULL AND page_start IS NULL))
      AND meta->'entities'->>'coverage_code' = %s
      AND (meta->'entities'->'amount'->>'amount_value')::int = %s
      AND (meta->>'is_synthetic')::boolean = true
    LIMIT 1
    """

    with conn.cursor() as cur:
        cur.execute(query, (insurer_id, document_id, page_start, page_start, coverage_code, amount_value))
        return cur.fetchone() is not None


def insert_synthetic_chunk(
    conn,
    candidate: MixedChunkCandidate,
    coverage_line: CoverageLine,
    dry_run: bool = False,
) -> SyntheticChunkResult:
    """
    V1.6.3-β: Synthetic chunk INSERT

    원칙:
    - 기존 chunk 수정 금지
    - 1 담보 = 1 synthetic chunk
    - coverage_alias 매핑만 INSERT 허용
    """
    result = SyntheticChunkResult(
        source_chunk_id=candidate.chunk_id,
        insurer_code=candidate.insurer_code,
        coverage_code=coverage_line.coverage_code or "",
        raw_name=coverage_line.raw_name or "",
        amount_value=coverage_line.amount_value or 0,
        amount_text=coverage_line.amount_text or "",
        mapping_source=coverage_line.mapping_source or "none",
        eligible_for_insert=coverage_line.eligible_for_insert,
        reject_reason=coverage_line.reject_reason,
    )

    # V1.6.3-β: INSERT 자격 체크
    if not coverage_line.eligible_for_insert:
        result.status = "rejected"
        return result

    if dry_run:
        result.status = "dry_run"
        return result

    # Idempotent 체크 (V1.6.3-β: 더 정밀한 중복 키)
    if check_existing_synthetic(
        conn,
        candidate.insurer_id,
        candidate.document_id,
        candidate.page_start,
        coverage_line.coverage_code,
        coverage_line.amount_value,
    ):
        result.status = "skipped_existing"
        return result

    # V1.6.3-β-2: Synthetic chunk content (버전 표기 업데이트)
    content = f"""[SYNTHETIC]
{coverage_line.raw_line}

[V1.6.3-β-2 Split: source_chunk_id={candidate.chunk_id}]"""

    # V1.6.3-β-2: Meta 구조 운영 기준 고정
    meta = {
        "is_synthetic": True,
        "synthetic_type": "split",  # 운영 기준 키 (불변)
        "synthetic_method": "v1_6_3_beta_2_split",  # V1.6.3-β-2: 호환성 키 추가
        "synthetic_source_chunk_id": candidate.chunk_id,
        "source_document_id": candidate.document_id,
        "source_doc_type": candidate.doc_type,
        "source_page_start": candidate.page_start,
        "raw_name": coverage_line.raw_name,
        "raw_line_excerpt": coverage_line.raw_line[:200] if coverage_line.raw_line else "",
        "entities": {
            "coverage_code": coverage_line.coverage_code,
            "amount": {
                "amount_value": coverage_line.amount_value,
                "amount_text": coverage_line.amount_text,
                "method": "v1_6_3_beta_2_split",  # V1.6.3-β-2: 통일
                "confidence": coverage_line.confidence or "medium",
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
    V1.6.3-β Split Synthetic Chunk Backfill 실행

    Returns:
        (candidates, results, rejected_lines)
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
        rejected_lines: list[CoverageLine] = []

        created_count = 0
        skipped_count = 0
        rejected_count = 0

        for i, candidate in enumerate(candidates):
            for line in candidate.coverage_lines:
                if line.eligible_for_insert:
                    # V1.6.3-β: INSERT 자격 있음
                    result = insert_synthetic_chunk(conn, candidate, line, dry_run)
                    results.append(result)

                    if result.status == "created":
                        created_count += 1
                    elif result.status.startswith("skipped"):
                        skipped_count += 1
                else:
                    # V1.6.3-β: INSERT 자격 없음 → rejected report
                    rejected_lines.append(line)
                    rejected_count += 1

                    # results에도 기록 (dry-run 리포트용)
                    result = SyntheticChunkResult(
                        source_chunk_id=candidate.chunk_id,
                        insurer_code=candidate.insurer_code,
                        coverage_code=line.coverage_code or "",
                        raw_name=line.raw_name or "",
                        amount_value=line.amount_value or 0,
                        amount_text=line.amount_text or "",
                        mapping_source=line.mapping_source or "none",
                        eligible_for_insert=False,
                        reject_reason=line.reject_reason,
                        status="rejected",
                    )
                    results.append(result)

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
        total_lines = sum(len(c.coverage_lines) for c in candidates)
        print(f"  Total coverage lines: {total_lines}")
        eligible_lines = sum(1 for c in candidates for line in c.coverage_lines if line.eligible_for_insert)
        print(f"  Eligible for INSERT (coverage_alias): {eligible_lines}")
        print(f"  Rejected (coverage_standard/no_mapping/etc): {rejected_count}")
        if not dry_run:
            print(f"  Synthetic chunks created: {created_count}")
            print(f"  Skipped (existing): {skipped_count}")

        return candidates, results, rejected_lines

    finally:
        conn.close()


def save_candidates_report(candidates: list[MixedChunkCandidate], output_path: str):
    """mixed_chunk_candidates.csv 저장"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "chunk_id", "insurer_code", "document_id", "doc_type", "page_start",
            "current_code", "total_lines", "eligible_lines", "rejected_lines", "raw_names"
        ])

        for c in candidates:
            eligible_count = sum(1 for line in c.coverage_lines if line.eligible_for_insert)
            rejected_count = len(c.coverage_lines) - eligible_count
            raw_names = "; ".join(line.raw_name for line in c.coverage_lines if line.raw_name)

            writer.writerow([
                c.chunk_id, c.insurer_code, c.document_id, c.doc_type, c.page_start,
                c.current_coverage_code, len(c.coverage_lines), eligible_count, rejected_count, raw_names[:200]
            ])

    print(f"  Saved: {output_path}")


def save_rejected_report(rejected_lines: list[CoverageLine], output_path: str):
    """V1.6.3-β: rejected_lines_report.csv 저장"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "line_number", "raw_name", "coverage_code", "mapping_source",
            "amount_value", "amount_text", "reject_reason", "raw_line_excerpt"
        ])

        for line in rejected_lines:
            writer.writerow([
                line.line_number,
                line.raw_name,
                line.coverage_code,
                line.mapping_source,
                line.amount_value,
                line.amount_text,
                line.reject_reason,
                line.raw_line[:100] if line.raw_line else "",
            ])

    print(f"  Saved: {output_path}")


def save_results_report(results: list[SyntheticChunkResult], output_path: str):
    """V1.6.3-β: synthetic_chunks_report.csv 저장"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "source_chunk_id", "insurer_code", "coverage_code", "raw_name",
            "amount_value", "amount_text", "mapping_source", "eligible_for_insert",
            "reject_reason", "new_chunk_id", "status"
        ])

        for r in results:
            writer.writerow([
                r.source_chunk_id, r.insurer_code, r.coverage_code, r.raw_name,
                r.amount_value, r.amount_text, r.mapping_source, r.eligible_for_insert,
                r.reject_reason, r.new_chunk_id, r.status
            ])

    print(f"  Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="V1.6.3-β Split Synthetic Chunk Backfill - Mixed Coverage Chunk 분해 (안정화 핫픽스)"
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
        default="artifacts/v1_6_3_beta",  # V1.6.3-β
        help="리포트 출력 디렉토리",
    )

    args = parser.parse_args()

    print(f"[V1.6.3-β-2 Split Synthetic Chunk Backfill (마감 패치)]")
    print(f"  mode: {'scan' if args.scan else 'dry-run' if args.dry_run else 'execute'}")
    print(f"  insurer: {args.insurer or 'ALL'}")
    print(f"  doc_types: {args.doc_types}")
    print(f"  limit: {args.limit or 'NONE'}")
    print()

    # 실행
    candidates, results, rejected = run_backfill(
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

    if rejected:
        save_rejected_report(
            rejected,
            os.path.join(args.output_dir, f"rejected_lines_report_{timestamp}.csv")
        )

    if results:
        save_results_report(
            results,
            os.path.join(args.output_dir, f"synthetic_chunks_report_{timestamp}.csv")
        )


if __name__ == "__main__":
    main()
