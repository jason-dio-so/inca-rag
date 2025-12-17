#!/usr/bin/env python3
"""
보험 문서 자동 분류 스크립트

PDF 파일을 파일명 키워드 기반으로 다음 폴더로 분류:
- 약관, 사업방법서, 상품요약서, 가입설계서, 기타

Usage:
    python tools/organize_docs.py --root data/SAMSUNG --mode move --dry-run
    python tools/organize_docs.py --root data/SAMSUNG --mode copy --keep-incoming
"""

import argparse
import re
import shutil
from pathlib import Path


# 분류 규칙 정의 (우선순위: 가입설계서 > 사업방법서 > 약관 > 상품요약서 > 기타)
CATEGORY_RULES: list[tuple[str, re.Pattern]] = [
    ("가입설계서", re.compile(r"가입설계서|설계서|proposal|illustration", re.IGNORECASE)),
    ("사업방법서", re.compile(r"사업방법서|사업방법|방법서|business|rule", re.IGNORECASE)),
    ("약관", re.compile(r"약관|terms|policy", re.IGNORECASE)),
    ("상품요약서", re.compile(r"상품요약서|요약서|summary|쉬운요약서|easy", re.IGNORECASE)),
]

# 출력 폴더 목록
OUTPUT_FOLDERS = ["약관", "사업방법서", "상품요약서", "가입설계서", "기타"]


def classify_file(filename: str) -> str:
    """
    파일명을 기반으로 카테고리 분류
    우선순위: 가입설계서 > 사업방법서 > 약관 > 상품요약서 > 기타
    """
    for category, pattern in CATEGORY_RULES:
        if pattern.search(filename):
            return category
    return "기타"


def get_files_to_process(root: Path) -> list[Path]:
    """
    루트 폴더 바로 아래의 파일들만 반환 (하위 폴더 제외)
    """
    files = []
    for item in root.iterdir():
        # 파일만 대상 (폴더 제외)
        if item.is_file():
            files.append(item)
    return sorted(files)


def ensure_output_folders(root: Path, dry_run: bool = False) -> None:
    """
    출력 폴더들 생성
    """
    for folder in OUTPUT_FOLDERS:
        folder_path = root / folder
        if not folder_path.exists():
            if dry_run:
                print(f"[DRY-RUN] 폴더 생성: {folder_path}")
            else:
                folder_path.mkdir(parents=True, exist_ok=True)
                print(f"[CREATE] 폴더 생성: {folder_path}")


def organize_documents(
    root: Path,
    mode: str = "move",
    dry_run: bool = False,
    keep_incoming: bool = False,
) -> dict[str, list[str]]:
    """
    문서 분류 실행

    Args:
        root: 대상 폴더 경로
        mode: 'move' 또는 'copy'
        dry_run: True면 실제 실행 없이 출력만
        keep_incoming: copy 모드에서 원본을 _incoming에 보관

    Returns:
        카테고리별 분류된 파일 목록
    """
    results: dict[str, list[str]] = {cat: [] for cat in OUTPUT_FOLDERS}

    # 출력 폴더 생성
    ensure_output_folders(root, dry_run)

    # copy 모드에서 keep_incoming 옵션 시 _incoming 폴더 생성
    incoming_path = root / "_incoming"
    if mode == "copy" and keep_incoming and not dry_run:
        incoming_path.mkdir(parents=True, exist_ok=True)

    # 처리할 파일 목록
    files = get_files_to_process(root)

    if not files:
        print(f"[INFO] 처리할 파일이 없습니다: {root}")
        return results

    print(f"\n{'='*60}")
    print(f"대상 폴더: {root}")
    print(f"모드: {mode}")
    print(f"Dry-run: {dry_run}")
    print(f"처리 대상 파일 수: {len(files)}")
    print(f"{'='*60}\n")

    for file_path in files:
        filename = file_path.name
        category = classify_file(filename)
        dest_folder = root / category
        dest_path = dest_folder / filename

        # 결과 기록
        results[category].append(filename)

        # 로그 출력
        action = "MOVE" if mode == "move" else "COPY"
        if dry_run:
            action = f"DRY-RUN:{action}"

        print(f"[{action}] {filename}")
        print(f"         → {category}/")

        if not dry_run:
            # 실제 파일 이동/복사
            if mode == "move":
                shutil.move(str(file_path), str(dest_path))
            else:  # copy
                shutil.copy2(str(file_path), str(dest_path))

                # keep_incoming 옵션: 원본을 _incoming으로 이동
                if keep_incoming:
                    incoming_dest = incoming_path / filename
                    shutil.move(str(file_path), str(incoming_dest))
                    print(f"         원본 → _incoming/")

    # 요약 출력
    print(f"\n{'='*60}")
    print("분류 결과 요약:")
    print(f"{'='*60}")
    for category in OUTPUT_FOLDERS:
        count = len(results[category])
        if count > 0:
            print(f"  {category}: {count}개")
    print(f"{'='*60}\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="보험 문서 자동 분류 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # Dry-run으로 미리 확인
  python tools/organize_docs.py --root data/SAMSUNG --dry-run

  # 파일 이동 (기본값)
  python tools/organize_docs.py --root data/SAMSUNG --mode move

  # 파일 복사 + 원본 _incoming 보관
  python tools/organize_docs.py --root data/SAMSUNG --mode copy --keep-incoming
        """,
    )

    parser.add_argument(
        "--root",
        type=str,
        default="data/SAMSUNG",
        help="대상 폴더 경로 (default: data/SAMSUNG)",
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
        "--keep-incoming",
        action="store_true",
        help="copy 모드에서 원본 파일을 _incoming 폴더에 보관",
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
        keep_incoming=args.keep_incoming,
    )

    return 0


if __name__ == "__main__":
    exit(main())
