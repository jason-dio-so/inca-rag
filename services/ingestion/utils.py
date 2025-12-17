"""
유틸리티 함수: sha256, path helpers, logging 설정
"""

from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path
from typing import Any


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """로깅 설정"""
    logger = logging.getLogger("ingestion")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def sha256_file(file_path: Path) -> str:
    """파일의 SHA256 해시 계산"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """바이트 데이터의 SHA256 해시 계산"""
    return hashlib.sha256(data).hexdigest()


def extract_insurer_code(path: Path, root: Path) -> str | None:
    """
    경로에서 insurer_code 추출
    예: data/SAMSUNG/약관/xxx.pdf -> SAMSUNG
    """
    try:
        relative = path.relative_to(root)
        parts = relative.parts
        if len(parts) >= 1:
            return parts[0].upper()
    except ValueError:
        pass
    return None


def extract_doc_type_from_path(path: Path, root: Path) -> str | None:
    """
    경로에서 doc_type 추출 (두 번째 폴더)
    예: data/SAMSUNG/약관/xxx.pdf -> 약관
    """
    valid_doc_types = {"약관", "사업방법서", "상품요약서", "가입설계서", "기타"}
    try:
        relative = path.relative_to(root)
        parts = relative.parts
        if len(parts) >= 2:
            doc_type = parts[1]
            if doc_type in valid_doc_types:
                return doc_type
    except ValueError:
        pass
    return None


def find_manifest_for_pdf(pdf_path: Path) -> Path | None:
    """
    PDF 옆의 manifest 파일 찾기
    우선순위: .manifest.yaml > .manifest.yml > .manifest.json
    """
    stem = pdf_path.stem
    parent = pdf_path.parent

    for ext in [".manifest.yaml", ".manifest.yml", ".manifest.json"]:
        manifest_path = parent / f"{stem}{ext}"
        if manifest_path.exists():
            return manifest_path

    return None


def find_pdfs_recursive(root: Path, insurer_code: str | None = None) -> list[Path]:
    """
    루트 아래의 모든 PDF 파일을 재귀 탐색
    insurer_code가 지정되면 해당 폴더만 탐색
    """
    if insurer_code:
        search_path = root / insurer_code.lower()
        if not search_path.exists():
            # 대소문자 변형 시도
            search_path = root / insurer_code.upper()
            if not search_path.exists():
                search_path = root / insurer_code
    else:
        search_path = root

    if not search_path.exists():
        return []

    return sorted(search_path.rglob("*.pdf"))


def truncate_text(text: str, max_length: int = 100) -> str:
    """텍스트를 최대 길이로 자르기"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


class IngestionStats:
    """Ingestion 통계 수집"""

    def __init__(self):
        self.documents_processed = 0
        self.documents_inserted = 0
        self.documents_skipped = 0
        self.chunks_created = 0
        self.total_pages = 0
        self.coverage_hits: dict[str, int] = {}
        self.errors: list[str] = []

    def add_coverage_hit(self, code: str) -> None:
        self.coverage_hits[code] = self.coverage_hits.get(code, 0) + 1

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def summary(self) -> str:
        lines = [
            "\n" + "=" * 60,
            "Ingestion 결과 요약",
            "=" * 60,
            f"  처리 문서 수: {self.documents_processed}",
            f"  문서 insert: {self.documents_inserted}",
            f"  문서 skip (중복): {self.documents_skipped}",
            f"  총 페이지 수: {self.total_pages}",
            f"  생성 chunk 수: {self.chunks_created}",
        ]

        if self.coverage_hits:
            lines.append("\n  Coverage 매칭 통계:")
            sorted_hits = sorted(
                self.coverage_hits.items(), key=lambda x: x[1], reverse=True
            )
            for code, count in sorted_hits[:10]:
                lines.append(f"    {code}: {count}")

        if self.errors:
            lines.append(f"\n  에러: {len(self.errors)}건")
            for err in self.errors[:5]:
                lines.append(f"    - {err}")

        lines.append("=" * 60)
        return "\n".join(lines)
