"""
Step H-1.5: amount/condition 추출 품질 리포트

8개 보험사 전체 chunk에서 추출 성공률/오탐 의심 패턴을 계측
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.extraction.amount_extractor import extract_amount
from services.extraction.condition_extractor import extract_condition_snippet


def get_db_url() -> str:
    """DATABASE_URL 환경변수 또는 기본값 반환"""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )

# 대상 doc_type (compare_axis)
TARGET_DOC_TYPES = ["가입설계서", "상품요약서", "사업방법서"]

# 샘플 수
SAMPLE_SIZE_PER_GROUP = 50

# 오탐 의심 기준
MIN_REASONABLE_AMOUNT = 1_000  # 1,000원 미만은 의심
MAX_REASONABLE_AMOUNT = 10_000_000_000  # 10억 초과는 의심
PREMIUM_KEYWORDS = ["보험료", "납입", "월납", "연납", "일시납"]


@dataclass
class FlaggedSample:
    """오탐 의심 샘플"""
    insurer_code: str
    doc_type: str
    chunk_id: int
    preview: str
    amount_text: str | None
    amount_value: int | None
    unit: str | None
    confidence: str
    flag_reason: str


@dataclass
class GroupStats:
    """insurer_code × doc_type별 통계"""
    insurer_code: str
    doc_type: str
    total_samples: int = 0
    amount_extracted: int = 0
    condition_extracted: int = 0
    flagged_count: int = 0
    flagged_samples: list[FlaggedSample] = field(default_factory=list)

    @property
    def amount_hit_rate(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.amount_extracted / self.total_samples * 100

    @property
    def condition_hit_rate(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.condition_extracted / self.total_samples * 100

    @property
    def flagged_rate(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.flagged_count / self.total_samples * 100


def get_db_connection():
    """DB 연결 생성"""
    return psycopg2.connect(get_db_url())


def fetch_samples(conn, insurer_code: str, doc_type: str, limit: int = SAMPLE_SIZE_PER_GROUP) -> list[dict]:
    """
    보험사/doc_type별 샘플 chunk 조회

    coverage_code가 있는 chunk만 대상 (담보 관련 chunk)
    """
    query = """
        SELECT
            c.chunk_id,
            c.content,
            c.page_start,
            i.insurer_code,
            d.doc_type
        FROM chunk c
        JOIN document d ON c.document_id = d.document_id
        JOIN insurer i ON d.insurer_id = i.insurer_id
        WHERE i.insurer_code = %s
          AND d.doc_type = %s
          AND c.meta->'entities'->>'coverage_code' IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %s
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (insurer_code, doc_type, limit))
        return cur.fetchall()


def check_premium_nearby(preview: str, amount_text: str) -> bool:
    """금액 주변에 보험료 관련 키워드가 있는지 확인"""
    if not amount_text or not preview:
        return False

    # amount_text 위치 찾기
    pos = preview.find(amount_text)
    if pos == -1:
        return False

    # ±50자 범위에서 보험료 키워드 확인
    start = max(0, pos - 50)
    end = min(len(preview), pos + len(amount_text) + 50)
    context = preview[start:end]

    for keyword in PREMIUM_KEYWORDS:
        if keyword in context:
            return True
    return False


def analyze_chunk(chunk: dict, doc_type: str) -> tuple[dict, dict, list[str]]:
    """
    단일 chunk 분석

    Args:
        chunk: chunk 데이터
        doc_type: 문서 유형 (가입설계서/상품요약서/사업방법서)

    Returns:
        (amount_result, condition_result, flag_reasons)
    """
    content = chunk["content"] or ""
    preview = content[:200]  # 미리보기용

    # 추출 실행 (doc_type 전달)
    amount_result = extract_amount(content, doc_type=doc_type)
    condition_result = extract_condition_snippet(content)

    # 오탐 의심 플래그
    flag_reasons = []

    # 1. amount_text 있는데 unit이 None
    if amount_result.amount_text and not amount_result.unit:
        flag_reasons.append("unit_missing")

    # 2. amount_value가 비정상 범위
    if amount_result.amount_value is not None:
        if amount_result.amount_value < MIN_REASONABLE_AMOUNT:
            flag_reasons.append(f"too_small({amount_result.amount_value}원)")
        elif amount_result.amount_value > MAX_REASONABLE_AMOUNT:
            flag_reasons.append(f"too_large({amount_result.amount_value:,}원)")

    # 3. 보험료 근처 금액
    if amount_result.amount_text and check_premium_nearby(content, amount_result.amount_text):
        flag_reasons.append("premium_nearby")

    return (
        {
            "amount_value": amount_result.amount_value,
            "amount_text": amount_result.amount_text,
            "unit": amount_result.unit,
            "confidence": amount_result.confidence,
        },
        {
            "snippet": condition_result.snippet,
            "matched_terms": condition_result.matched_terms,
        },
        flag_reasons,
    )


def run_audit(sample_size: int = SAMPLE_SIZE_PER_GROUP) -> dict[str, GroupStats]:
    """
    전체 보험사/doc_type에 대해 audit 실행
    """
    conn = get_db_connection()

    # 보험사 목록 조회
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT insurer_code FROM insurer ORDER BY insurer_code")
        insurers = [row["insurer_code"] for row in cur.fetchall()]

    results: dict[str, GroupStats] = {}

    for insurer_code in insurers:
        for doc_type in TARGET_DOC_TYPES:
            key = f"{insurer_code}|{doc_type}"
            stats = GroupStats(insurer_code=insurer_code, doc_type=doc_type)

            # 샘플 조회
            samples = fetch_samples(conn, insurer_code, doc_type, sample_size)
            stats.total_samples = len(samples)

            if not samples:
                results[key] = stats
                continue

            # 각 샘플 분석
            for chunk in samples:
                amount_info, condition_info, flags = analyze_chunk(chunk, doc_type)

                # 성공 카운트
                if amount_info["amount_value"] is not None:
                    stats.amount_extracted += 1

                if condition_info["snippet"] is not None:
                    stats.condition_extracted += 1

                # 플래그 카운트
                if flags:
                    stats.flagged_count += 1
                    stats.flagged_samples.append(FlaggedSample(
                        insurer_code=insurer_code,
                        doc_type=doc_type,
                        chunk_id=chunk["chunk_id"],
                        preview=chunk["content"][:150] if chunk["content"] else "",
                        amount_text=amount_info["amount_text"],
                        amount_value=amount_info["amount_value"],
                        unit=amount_info["unit"],
                        confidence=amount_info["confidence"],
                        flag_reason=", ".join(flags),
                    ))

            results[key] = stats

    conn.close()
    return results


def generate_report(results: dict[str, GroupStats], output_path: str):
    """
    Markdown 리포트 생성
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    lines = [
        "# Step H-1.5: amount/condition 추출 품질 리포트",
        "",
        f"> 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 1. 개요",
        "",
        "compare_axis 대상 doc_type(가입설계서/상품요약서/사업방법서)에서 amount/condition 추출 성공률 계측.",
        "",
        f"- 샘플 수: 보험사×doc_type별 최대 {SAMPLE_SIZE_PER_GROUP}개",
        "- 대상: coverage_code가 태깅된 chunk만 (담보 관련)",
        "",
        "---",
        "",
        "## 2. 전체 통계",
        "",
        "| insurer_code | doc_type | samples | amount_hit | condition_hit | flagged |",
        "|--------------|----------|---------|------------|---------------|---------|",
    ]

    # 전체 집계
    total_samples = 0
    total_amount_hit = 0
    total_condition_hit = 0
    total_flagged = 0
    all_flagged_samples: list[FlaggedSample] = []

    for key in sorted(results.keys()):
        stats = results[key]
        total_samples += stats.total_samples
        total_amount_hit += stats.amount_extracted
        total_condition_hit += stats.condition_extracted
        total_flagged += stats.flagged_count
        all_flagged_samples.extend(stats.flagged_samples)

        lines.append(
            f"| {stats.insurer_code} | {stats.doc_type} | {stats.total_samples} | "
            f"{stats.amount_hit_rate:.1f}% ({stats.amount_extracted}) | "
            f"{stats.condition_hit_rate:.1f}% ({stats.condition_extracted}) | "
            f"{stats.flagged_rate:.1f}% ({stats.flagged_count}) |"
        )

    # 합계 행
    if total_samples > 0:
        lines.append(
            f"| **합계** | - | **{total_samples}** | "
            f"**{total_amount_hit/total_samples*100:.1f}%** ({total_amount_hit}) | "
            f"**{total_condition_hit/total_samples*100:.1f}%** ({total_condition_hit}) | "
            f"**{total_flagged/total_samples*100:.1f}%** ({total_flagged}) |"
        )

    # doc_type별 집계
    lines.extend([
        "",
        "---",
        "",
        "## 3. doc_type별 집계",
        "",
        "| doc_type | samples | amount_hit_rate | condition_hit_rate | flagged_rate |",
        "|----------|---------|-----------------|--------------------|--------------| ",
    ])

    doc_type_stats: dict[str, dict] = defaultdict(lambda: {"samples": 0, "amount": 0, "condition": 0, "flagged": 0})
    for stats in results.values():
        doc_type_stats[stats.doc_type]["samples"] += stats.total_samples
        doc_type_stats[stats.doc_type]["amount"] += stats.amount_extracted
        doc_type_stats[stats.doc_type]["condition"] += stats.condition_extracted
        doc_type_stats[stats.doc_type]["flagged"] += stats.flagged_count

    for doc_type in TARGET_DOC_TYPES:
        s = doc_type_stats[doc_type]
        if s["samples"] > 0:
            lines.append(
                f"| {doc_type} | {s['samples']} | "
                f"{s['amount']/s['samples']*100:.1f}% | "
                f"{s['condition']/s['samples']*100:.1f}% | "
                f"{s['flagged']/s['samples']*100:.1f}% |"
            )

    # 오탐 의심 샘플
    lines.extend([
        "",
        "---",
        "",
        "## 4. 오탐 의심 샘플 (상위 20개)",
        "",
        "**플래그 종류:**",
        "- `unit_missing`: amount_text는 있지만 unit이 None",
        "- `too_small`: amount_value < 1,000원",
        "- `too_large`: amount_value > 10억원",
        "- `premium_nearby`: 보험료/납입 등 키워드가 금액 근처에 존재",
        "",
    ])

    # 상위 20개 플래그 샘플
    flagged_to_show = all_flagged_samples[:20]

    if flagged_to_show:
        for i, sample in enumerate(flagged_to_show, 1):
            preview_escaped = sample.preview.replace("|", "\\|").replace("\n", " ")[:100]
            lines.extend([
                f"### 4.{i}. [{sample.insurer_code}] {sample.doc_type} (chunk #{sample.chunk_id})",
                "",
                f"- **flag**: `{sample.flag_reason}`",
                f"- **amount_text**: {sample.amount_text}",
                f"- **amount_value**: {sample.amount_value:,}원" if sample.amount_value else "- **amount_value**: None",
                f"- **unit**: {sample.unit}",
                f"- **confidence**: {sample.confidence}",
                f"- **preview**: {preview_escaped}...",
                "",
            ])
    else:
        lines.append("(플래그된 샘플 없음)")

    # 플래그 종류별 집계
    lines.extend([
        "",
        "---",
        "",
        "## 5. 플래그 종류별 집계",
        "",
    ])

    flag_type_counts: dict[str, int] = defaultdict(int)
    for sample in all_flagged_samples:
        for reason in sample.flag_reason.split(", "):
            # 세부 내용 제거 (too_small(500원) → too_small)
            base_reason = reason.split("(")[0]
            flag_type_counts[base_reason] += 1

    if flag_type_counts:
        lines.append("| 플래그 종류 | 건수 |")
        lines.append("|------------|------|")
        for reason, count in sorted(flag_type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("(플래그 없음)")

    # 결론
    lines.extend([
        "",
        "---",
        "",
        "## 6. 관찰 요약",
        "",
        "- amount 추출 성공률과 condition 추출 성공률을 doc_type별로 비교",
        "- 플래그된 샘플은 오탐 **의심**이며, 정답/오답 판정은 수동 검토 필요",
        "- `premium_nearby` 플래그가 많으면 보험료 금액을 보험금으로 오인하는 패턴 의심",
        "",
    ])

    # 파일 저장
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report saved to: {output_path}")


def main():
    """메인 함수"""
    print("Starting extraction quality audit...")
    print(f"Sample size per group: {SAMPLE_SIZE_PER_GROUP}")
    print(f"Target doc_types: {TARGET_DOC_TYPES}")
    print()

    # Audit 실행
    results = run_audit()

    # 리포트 생성
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "artifacts/audit/extraction_quality_report.md"
    )
    generate_report(results, output_path)

    # 콘솔 요약
    print("\n=== Summary ===")
    total_samples = sum(s.total_samples for s in results.values())
    total_amount = sum(s.amount_extracted for s in results.values())
    total_condition = sum(s.condition_extracted for s in results.values())
    total_flagged = sum(s.flagged_count for s in results.values())

    if total_samples > 0:
        print(f"Total samples: {total_samples}")
        print(f"Amount hit rate: {total_amount/total_samples*100:.1f}%")
        print(f"Condition hit rate: {total_condition/total_samples*100:.1f}%")
        print(f"Flagged rate: {total_flagged/total_samples*100:.1f}%")


if __name__ == "__main__":
    main()
