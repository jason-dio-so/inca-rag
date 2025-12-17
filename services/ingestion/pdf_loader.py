"""
PDF Loader

PDF 파일에서 페이지 단위 텍스트 추출
PyMuPDF (fitz) 사용
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class PageContent:
    """페이지 내용"""

    page_no: int  # 1-indexed
    text: str
    char_count: int


@dataclass
class PDFContent:
    """PDF 전체 내용"""

    path: Path
    pages: list[PageContent]
    total_pages: int
    total_chars: int

    @property
    def full_text(self) -> str:
        """전체 텍스트 (페이지 구분 없이)"""
        return "\n\n".join(page.text for page in self.pages)


def load_pdf(pdf_path: Path) -> PDFContent:
    """
    PDF 파일에서 페이지별 텍스트 추출

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        PDFContent

    Raises:
        FileNotFoundError: 파일이 없을 때
        RuntimeError: PDF 처리 실패
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일이 없습니다: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise RuntimeError(f"PDF 열기 실패: {pdf_path} - {e}")

    pages: list[PageContent] = []
    total_chars = 0

    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")

            # 텍스트 정리
            text = _clean_text(text)

            char_count = len(text)
            total_chars += char_count

            pages.append(
                PageContent(
                    page_no=page_idx + 1,  # 1-indexed
                    text=text,
                    char_count=char_count,
                )
            )
    finally:
        doc.close()

    return PDFContent(
        path=pdf_path,
        pages=pages,
        total_pages=len(pages),
        total_chars=total_chars,
    )


def _clean_text(text: str) -> str:
    """텍스트 정리"""
    # 연속된 공백/줄바꿈 정리
    import re

    # 연속된 줄바꿈을 2개로 제한
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 연속된 공백을 1개로
    text = re.sub(r"[ \t]+", " ", text)

    # 앞뒤 공백 제거
    text = text.strip()

    return text


def extract_pages_with_text(
    pdf_path: Path, min_chars: int = 10
) -> list[tuple[int, str]]:
    """
    PDF에서 텍스트가 있는 페이지만 추출

    Args:
        pdf_path: PDF 파일 경로
        min_chars: 최소 문자 수 (이하면 빈 페이지로 간주)

    Returns:
        [(page_no, text), ...] 리스트
    """
    content = load_pdf(pdf_path)

    result = []
    for page in content.pages:
        if page.char_count >= min_chars:
            result.append((page.page_no, page.text))

    return result
