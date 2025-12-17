#!/usr/bin/env python3
"""
PDF 문서에 대한 manifest.yaml 자동 생성 스크립트

data/<INSURER>/ 하위의 doc_type 폴더들을 재귀 탐색하여
각 PDF 옆에 <stem>.manifest.yaml을 생성한다.

Usage:
    python tools/generate_manifests.py --root data/SAMSUNG --dry-run
    python tools/generate_manifests.py --root data/SAMSUNG
    python tools/generate_manifests.py --root data/SAMSUNG --force
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any


# 유효한 doc_type 폴더 목록
VALID_DOC_TYPES = {"약관", "사업방법서", "상품요약서", "가입설계서", "기타"}

# 쉬운요약서 감지 패턴 (상품요약서 중 subtype: easy)
EASY_SUMMARY_PATTERN = re.compile(r"쉬운요약서|쉬운\s*요약서|easy", re.IGNORECASE)

# manifest 템플릿
MANIFEST_TEMPLATE = """\
schema_version: manifest_v1
insurer_code: {insurer_code}
doc_type: {doc_type}

product:
  product_name: null
  product_version: null
  product_code: null

plan:
  plan_name: null
  gender: U
  age_min: null
  age_max: null
  meta: {{}}

document:
  title: null
  effective_date: null
  meta:
    subtype: {subtype}

ingestion:
  chunk_strategy: null
  chunk_tokens: null
  notes: null
"""


def extract_insurer_code(root: Path) -> str:
    """
    루트 경로에서 insurer_code 추출
    예: data/SAMSUNG -> SAMSUNG
    """
    return root.name.upper()


def extract_doc_type(pdf_path: Path, root: Path) -> str | None:
    """
    PDF 경로에서 doc_type 추출 (부모 폴더 이름)
    유효한 doc_type이 아니면 None 반환
    """
    # PDF의 부모 폴더가 root 바로 아래인지 확인
    relative = pdf_path.relative_to(root)
    parts = relative.parts

    if len(parts) < 2:
        # root 바로 아래의 PDF (doc_type 폴더 안에 있지 않음)
        return None

    doc_type = parts[0]
    if doc_type in VALID_DOC_TYPES:
        return doc_type

    return None


def detect_subtype(filename: str, doc_type: str) -> str | None:
    """
    파일명과 doc_type을 기반으로 subtype 결정

    규칙:
    - 상품요약서 + 쉬운요약서/easy 패턴 → "easy"
    - 상품요약서 + 일반 → "standard"
    - 그 외 doc_type → null
    """
    if doc_type != "상품요약서":
        return "null"

    if EASY_SUMMARY_PATTERN.search(filename):
        return "easy"

    return "standard"


def generate_manifest_content(insurer_code: str, doc_type: str, subtype: str) -> str:
    """manifest 내용 생성"""
    return MANIFEST_TEMPLATE.format(
        insurer_code=insurer_code,
        doc_type=doc_type,
        subtype=subtype,
    )


def find_pdfs(root: Path) -> list[Path]:
    """
    root 하위의 모든 PDF 파일을 재귀 탐색하여 반환
    """
    return sorted(root.rglob("*.pdf"))


def generate_manifests(
    root: Path,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, int]:
    """
    manifest 파일 생성 실행

    Args:
        root: 대상 폴더 경로 (예: data/SAMSUNG)
        dry_run: True면 실제 생성 없이 출력만
        force: True면 기존 파일도 덮어쓰기

    Returns:
        통계 dict
    """
    stats = {
        "created": 0,
        "skipped_exists": 0,
        "skipped_invalid": 0,
        "overwritten": 0,
    }

    insurer_code = extract_insurer_code(root)
    pdfs = find_pdfs(root)

    if not pdfs:
        print(f"[INFO] PDF 파일이 없습니다: {root}")
        return stats

    # 헤더 출력
    print(f"\n{'='*70}")
    print(f"대상 폴더: {root}")
    print(f"Insurer Code: {insurer_code}")
    print(f"Dry-run: {dry_run}")
    print(f"Force: {force}")
    print(f"PDF 파일 수: {len(pdfs)}")
    print(f"{'='*70}\n")

    for pdf_path in pdfs:
        manifest_path = pdf_path.with_suffix(".manifest.yaml")
        relative_pdf = pdf_path.relative_to(root)

        # doc_type 추출
        doc_type = extract_doc_type(pdf_path, root)

        if doc_type is None:
            print(f"[SKIP] {relative_pdf} (유효한 doc_type 폴더에 없음)")
            stats["skipped_invalid"] += 1
            continue

        # 기존 파일 존재 여부 확인
        if manifest_path.exists():
            if not force:
                print(f"[SKIP] {relative_pdf} (manifest 이미 존재)")
                stats["skipped_exists"] += 1
                continue
            else:
                action = "OVERWRITE"
                stats["overwritten"] += 1
        else:
            action = "CREATE"
            stats["created"] += 1

        # subtype 결정
        subtype = detect_subtype(pdf_path.name, doc_type)

        # 로그 출력
        action_prefix = "DRY-RUN:" if dry_run else ""
        subtype_info = f" (subtype: {subtype})" if subtype != "null" else ""
        print(f"[{action_prefix}{action}] {relative_pdf}{subtype_info}")
        print(f"         -> {manifest_path.name}")

        # 파일 생성
        if not dry_run:
            content = generate_manifest_content(insurer_code, doc_type, subtype)
            manifest_path.write_text(content, encoding="utf-8")

    # 요약 출력
    print(f"\n{'='*70}")
    print("생성 결과 요약")
    print(f"{'='*70}")
    print(f"  생성: {stats['created']}개")
    if stats["overwritten"] > 0:
        print(f"  덮어쓰기: {stats['overwritten']}개")
    if stats["skipped_exists"] > 0:
        print(f"  건너뜀 (이미 존재): {stats['skipped_exists']}개")
    if stats["skipped_invalid"] > 0:
        print(f"  건너뜀 (유효하지 않은 위치): {stats['skipped_invalid']}개")
    print(f"{'='*70}\n")

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PDF 문서에 대한 manifest.yaml 자동 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # Dry-run으로 미리 확인
  python tools/generate_manifests.py --root data/SAMSUNG --dry-run

  # manifest 생성 (기존 파일은 건너뜀)
  python tools/generate_manifests.py --root data/SAMSUNG

  # 기존 manifest도 덮어쓰기
  python tools/generate_manifests.py --root data/SAMSUNG --force

생성되는 manifest 위치:
  data/SAMSUNG/약관/삼성_약관.pdf
  -> data/SAMSUNG/약관/삼성_약관.manifest.yaml
        """,
    )

    parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="대상 폴더 경로 (예: data/SAMSUNG)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 생성 없이 결과만 미리 확인",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 manifest 파일도 덮어쓰기",
    )

    args = parser.parse_args()

    # 경로 검증
    root = Path(args.root)
    if not root.exists():
        print(f"[ERROR] 폴더가 존재하지 않습니다: {root}")
        return 1

    if not root.is_dir():
        print(f"[ERROR] 경로가 폴더가 아닙니다: {root}")
        return 1

    # 실행
    generate_manifests(
        root=root,
        dry_run=args.dry_run,
        force=args.force,
    )

    return 0


if __name__ == "__main__":
    exit(main())
