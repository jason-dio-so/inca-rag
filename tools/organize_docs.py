#!/usr/bin/env python3
"""
보험 문서 자동 분류 스크립트

PDF 파일을 파일명 키워드 기반으로 다음 폴더로 분류:
- 약관, 사업방법서, 상품요약서, 가입설계서, 기타

분류 규칙:
- PDF: 파일명 키워드 기반 분류 (우선순위: 가입설계서 > 사업방법서 > 약관 > 상품요약서 > 기타)
- non-PDF (--include-nonpdf 옵션): 항상 "기타"로 분류

Manifest(sidecar) 처리:
- A.pdf 이동 시 A.manifest.yaml|yml|json도 함께 이동 (절대 분리 안됨)

Usage:
    python tools/organize_docs.py --root data/SAMSUNG --dry-run
    python tools/organize_docs.py --root data/SAMSUNG --mode move
    python tools/organize_docs.py --root data/SAMSUNG --mode copy --keep-incoming
    python tools/organize_docs.py --root data/SAMSUNG --on-conflict skip
"""

from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# ============================================================================
# 분류 규칙 정의 (우선순위: 가입설계서 > 사업방법서 > 약관 > 상품요약서 > 기타)
# ============================================================================
CATEGORY_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("가입설계서", re.compile(r"가입설계서|설계서|proposal|illustration", re.IGNORECASE)),
    ("사업방법서", re.compile(r"사업방법서|사업방법|방법서|사업설명서|business|rule", re.IGNORECASE)),
    ("약관", re.compile(r"약관|terms|policy", re.IGNORECASE)),
    ("상품요약서", re.compile(r"상품요약서|요약서|summary|쉬운요약서|easy", re.IGNORECASE)),
]

# 출력 폴더 목록
OUTPUT_FOLDERS = ["약관", "사업방법서", "상품요약서", "가입설계서", "기타"]

# Manifest 확장자
MANIFEST_EXTENSIONS = [".manifest.yaml", ".manifest.yml", ".manifest.json"]


# ============================================================================
# 데이터 클래스
# ============================================================================
@dataclass
class ProcessingStats:
    """처리 통계"""
    by_category: dict[str, int] = field(default_factory=lambda: {cat: 0 for cat in OUTPUT_FOLDERS})
    manifests_moved: int = 0
    conflicts_skipped: int = 0
    conflicts_renamed: int = 0
    conflicts_overwritten: int = 0
    total_files: int = 0


@dataclass
class FileBundle:
    """PDF와 관련 manifest 파일 묶음"""
    main_file: Path
    manifests: list[Path] = field(default_factory=list)


# ============================================================================
# 핵심 함수
# ============================================================================
def classify_file(filename: str) -> str:
    """
    파일명을 기반으로 카테고리 분류
    우선순위: 가입설계서 > 사업방법서 > 약관 > 상품요약서 > 기타
    """
    for category, pattern in CATEGORY_RULES:
        if pattern.search(filename):
            return category
    return "기타"


def find_manifests(file_path: Path) -> list[Path]:
    """
    주어진 파일에 대한 manifest(sidecar) 파일들을 찾음
    예: A.pdf -> A.manifest.yaml, A.manifest.yml, A.manifest.json
    """
    manifests = []
    stem = file_path.stem  # 확장자 제외한 파일명
    parent = file_path.parent

    for ext in MANIFEST_EXTENSIONS:
        manifest_path = parent / f"{stem}{ext}"
        if manifest_path.exists():
            manifests.append(manifest_path)

    return manifests


def get_files_to_process(root: Path, include_nonpdf: bool = False) -> list[FileBundle]:
    """
    루트 폴더 바로 아래의 파일들만 반환 (하위 폴더 제외)
    manifest 파일은 별도로 수집하지 않음 (PDF와 함께 처리)
    """
    bundles = []
    processed_manifests: set[Path] = set()

    for item in sorted(root.iterdir()):
        # 폴더는 제외
        if item.is_dir():
            continue

        # manifest 파일은 별도로 처리하지 않음 (PDF와 함께 이동)
        if any(item.name.endswith(ext) for ext in MANIFEST_EXTENSIONS):
            continue

        # PDF 필터링
        if not include_nonpdf and item.suffix.lower() != ".pdf":
            continue

        # manifest 찾기
        manifests = find_manifests(item)
        processed_manifests.update(manifests)

        bundles.append(FileBundle(main_file=item, manifests=manifests))

    return bundles


def resolve_conflict(
    dest_path: Path,
    on_conflict: Literal["rename", "skip", "overwrite"],
) -> tuple[Path | None, str]:
    """
    충돌 해결
    Returns: (최종 경로 또는 None(skip), 액션 설명)
    """
    if not dest_path.exists():
        return dest_path, ""

    if on_conflict == "skip":
        return None, "SKIP(exists)"

    if on_conflict == "overwrite":
        return dest_path, "OVERWRITE"

    # rename: (1), (2), ... 형식
    stem = dest_path.stem
    suffix = dest_path.suffix
    parent = dest_path.parent

    counter = 1
    while True:
        new_name = f"{stem}({counter}){suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path, f"RENAME({counter})"
        counter += 1


def ensure_output_folders(root: Path, dry_run: bool = False) -> None:
    """출력 폴더들 생성"""
    for folder in OUTPUT_FOLDERS:
        folder_path = root / folder
        if not folder_path.exists():
            if dry_run:
                print(f"[DRY-RUN] CREATE DIR: {folder_path}")
            else:
                folder_path.mkdir(parents=True, exist_ok=True)
                print(f"[CREATE] DIR: {folder_path}")


def move_or_copy_file(
    src: Path,
    dest: Path,
    mode: Literal["move", "copy"],
    dry_run: bool = False,
) -> None:
    """파일 이동 또는 복사"""
    if dry_run:
        return

    if mode == "move":
        shutil.move(str(src), str(dest))
    else:
        shutil.copy2(str(src), str(dest))


def organize_documents(
    root: Path,
    mode: Literal["move", "copy"] = "move",
    dry_run: bool = False,
    include_nonpdf: bool = False,
    keep_incoming: bool = False,
    on_conflict: Literal["rename", "skip", "overwrite"] = "rename",
) -> ProcessingStats:
    """
    문서 분류 실행

    Args:
        root: 대상 폴더 경로
        mode: 'move' 또는 'copy'
        dry_run: True면 실제 실행 없이 출력만
        include_nonpdf: True면 PDF 외 파일도 포함
        keep_incoming: copy 모드에서 원본을 _incoming에 보관
        on_conflict: 충돌 시 처리 방식

    Returns:
        처리 통계
    """
    stats = ProcessingStats()

    # 출력 폴더 생성
    ensure_output_folders(root, dry_run)

    # copy 모드에서 keep_incoming 옵션 시 _incoming 폴더 생성
    incoming_path = root / "_incoming"
    if mode == "copy" and keep_incoming:
        if not incoming_path.exists():
            if dry_run:
                print(f"[DRY-RUN] CREATE DIR: {incoming_path}")
            else:
                incoming_path.mkdir(parents=True, exist_ok=True)
                print(f"[CREATE] DIR: {incoming_path}")

    # 처리할 파일 목록
    bundles = get_files_to_process(root, include_nonpdf)

    if not bundles:
        print(f"\n[INFO] 처리할 파일이 없습니다: {root}")
        return stats

    # 헤더 출력
    print(f"\n{'='*70}")
    print(f"대상 폴더: {root}")
    print(f"모드: {mode}")
    print(f"충돌 처리: {on_conflict}")
    print(f"Dry-run: {dry_run}")
    print(f"PDF 외 포함: {include_nonpdf}")
    print(f"처리 대상 파일 수: {len(bundles)}")
    print(f"{'='*70}\n")

    for bundle in bundles:
        file_path = bundle.main_file
        filename = file_path.name

        # PDF는 분류 규칙 적용, non-PDF는 항상 "기타"
        if file_path.suffix.lower() == ".pdf":
            category = classify_file(filename)
        else:
            category = "기타"
        dest_folder = root / category
        dest_path = dest_folder / filename

        # 충돌 해결
        resolved_path, conflict_action = resolve_conflict(dest_path, on_conflict)

        # 액션 문자열 생성
        action_prefix = "DRY-RUN:" if dry_run else ""
        action = "MOVE" if mode == "move" else "COPY"

        if resolved_path is None:
            # skip
            print(f"[{action_prefix}SKIP] {filename} (already exists in {category}/)")
            stats.conflicts_skipped += 1
            continue

        # 통계 업데이트
        stats.by_category[category] += 1
        stats.total_files += 1

        if conflict_action == "OVERWRITE":
            stats.conflicts_overwritten += 1
        elif conflict_action.startswith("RENAME"):
            stats.conflicts_renamed += 1

        # 메인 파일 로그
        conflict_suffix = f" [{conflict_action}]" if conflict_action else ""
        print(f"[{action_prefix}{action}] {filename} -> {category}/{resolved_path.name}{conflict_suffix}")

        # 메인 파일 이동/복사
        move_or_copy_file(file_path, resolved_path, mode, dry_run)

        # Manifest 파일 처리
        for manifest in bundle.manifests:
            manifest_name = manifest.name
            manifest_dest = dest_folder / manifest_name

            # manifest 충돌도 동일하게 처리
            if resolved_path.name != filename:
                # 메인 파일이 rename 되었으면 manifest도 같은 규칙 적용
                new_stem = resolved_path.stem
                # A(1).pdf -> A(1).manifest.yaml
                for ext in MANIFEST_EXTENSIONS:
                    if manifest_name.endswith(ext):
                        manifest_dest = dest_folder / f"{new_stem}{ext}"
                        break

            m_resolved, m_conflict = resolve_conflict(manifest_dest, on_conflict)

            if m_resolved is None:
                print(f"       [SKIP] {manifest_name} (manifest, exists)")
                continue

            m_conflict_suffix = f" [{m_conflict}]" if m_conflict else ""
            print(f"       [{action_prefix}{action}] {manifest_name} -> {category}/{m_resolved.name}{m_conflict_suffix}")

            move_or_copy_file(manifest, m_resolved, mode, dry_run)
            stats.manifests_moved += 1

        # keep_incoming 처리 (copy 모드)
        if mode == "copy" and keep_incoming and not dry_run:
            # 원본을 _incoming으로 이동
            incoming_dest = incoming_path / filename
            shutil.move(str(file_path), str(incoming_dest))
            print(f"       [BACKUP] {filename} -> _incoming/")

            # manifest도 _incoming으로
            for manifest in bundle.manifests:
                m_incoming_dest = incoming_path / manifest.name
                if manifest.exists():  # copy 모드이므로 아직 존재
                    shutil.move(str(manifest), str(m_incoming_dest))
                    print(f"       [BACKUP] {manifest.name} -> _incoming/")

    # 요약 출력
    print(f"\n{'='*70}")
    print("분류 결과 요약")
    print(f"{'='*70}")
    print(f"\n[카테고리별 파일 수]")
    for category in OUTPUT_FOLDERS:
        count = stats.by_category[category]
        if count > 0:
            print(f"  {category}: {count}개")

    print(f"\n[기타 통계]")
    print(f"  총 처리 파일: {stats.total_files}개")
    print(f"  Manifest 이동: {stats.manifests_moved}개")

    if stats.conflicts_skipped > 0:
        print(f"  충돌 SKIP: {stats.conflicts_skipped}개")
    if stats.conflicts_renamed > 0:
        print(f"  충돌 RENAME: {stats.conflicts_renamed}개")
    if stats.conflicts_overwritten > 0:
        print(f"  충돌 OVERWRITE: {stats.conflicts_overwritten}개")

    print(f"{'='*70}\n")

    return stats


# ============================================================================
# CLI
# ============================================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="보험 문서 자동 분류 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # Dry-run으로 미리 확인 (실제 이동 없음)
  python tools/organize_docs.py --root data/SAMSUNG --dry-run

  # 파일 이동 (기본값)
  python tools/organize_docs.py --root data/SAMSUNG --mode move

  # 파일 복사 + 원본 _incoming 보관
  python tools/organize_docs.py --root data/SAMSUNG --mode copy --keep-incoming

  # 충돌 시 skip
  python tools/organize_docs.py --root data/SAMSUNG --on-conflict skip

  # PDF 외 파일도 포함
  python tools/organize_docs.py --root data/SAMSUNG --include-nonpdf

분류 우선순위:
  1. 가입설계서 (가입설계서|설계서|proposal|illustration)
  2. 사업방법서 (사업방법서|사업방법|방법서|business|rule)
  3. 약관 (약관|terms|policy)
  4. 상품요약서 (상품요약서|요약서|summary|쉬운요약서|easy)
  5. 기타 (위에 해당 없음)
        """,
    )

    parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="대상 폴더 경로 (예: data/SAMSUNG)",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["move", "copy"],
        default="move",
        help="파일 처리 모드: move(이동) 또는 copy(복사) (default: move)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 실행 없이 결과만 미리 확인",
    )

    parser.add_argument(
        "--include-nonpdf",
        action="store_true",
        help="PDF 외 파일도 포함 (non-PDF는 항상 '기타'로 분류)",
    )

    parser.add_argument(
        "--keep-incoming",
        action="store_true",
        help="copy 모드에서 원본 파일을 _incoming 폴더에 보관",
    )

    parser.add_argument(
        "--on-conflict",
        type=str,
        choices=["rename", "skip", "overwrite"],
        default="rename",
        help="충돌 시 처리 방식 (default: rename)",
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

    # keep_incoming은 copy 모드에서만 유효
    if args.keep_incoming and args.mode != "copy":
        print("[WARN] --keep-incoming 옵션은 --mode copy에서만 유효합니다.")

    # 실행
    organize_documents(
        root=root,
        mode=args.mode,
        dry_run=args.dry_run,
        include_nonpdf=args.include_nonpdf,
        keep_incoming=args.keep_incoming,
        on_conflict=args.on_conflict,
    )

    return 0


if __name__ == "__main__":
    exit(main())
