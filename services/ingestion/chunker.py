"""
Page-Aware Chunker

PDF 페이지 정보를 유지하면서 token 기준 청킹
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .pdf_loader import PDFContent, PageContent


@dataclass
class Chunk:
    """청크 데이터"""

    content: str
    page_start: int  # 시작 페이지 (1-indexed)
    page_end: int  # 끝 페이지 (1-indexed)
    chunk_index: int  # 문서 내 청크 순서 (0-indexed)
    token_count: int
    char_count: int
    section: str | None = None  # 섹션 제목 (있으면)
    meta: dict[str, Any] = field(default_factory=dict)


def estimate_tokens(text: str) -> int:
    """
    토큰 수 추정 (간단한 휴리스틱)
    한글: 글자당 약 0.5~1 토큰
    영어: 단어당 약 1.3 토큰
    """
    # 한글 문자 수
    korean_chars = len(re.findall(r"[가-힣]", text))
    # 영어 단어 수
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    # 숫자
    numbers = len(re.findall(r"\d+", text))
    # 기타 문자
    other = len(text) - korean_chars - sum(len(w) for w in re.findall(r"[a-zA-Z]+", text))

    # 추정 토큰 수
    tokens = (
        korean_chars * 0.7  # 한글
        + english_words * 1.3  # 영어
        + numbers * 0.5  # 숫자
        + other * 0.1  # 기타
    )

    return max(1, int(tokens))


class PageAwareChunker:
    """페이지 정보를 유지하는 청커"""

    def __init__(
        self,
        target_tokens: int = 1000,
        min_tokens: int = 200,
        max_tokens: int = 1500,
        overlap_tokens: int = 100,
    ):
        """
        Args:
            target_tokens: 목표 토큰 수
            min_tokens: 최소 토큰 수 (이하면 이전 청크에 병합)
            max_tokens: 최대 토큰 수 (초과하면 분할)
            overlap_tokens: 청크 간 오버랩 토큰 수
        """
        self.target_tokens = target_tokens
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_pdf_content(self, pdf_content: PDFContent) -> list[Chunk]:
        """
        PDF 내용을 청크로 분할

        Args:
            pdf_content: PDFContent 객체

        Returns:
            Chunk 리스트
        """
        if not pdf_content.pages:
            return []

        chunks: list[Chunk] = []
        current_text = ""
        current_page_start = 1
        current_page_end = 1

        for page in pdf_content.pages:
            page_text = page.text
            page_tokens = estimate_tokens(page_text)

            # 현재 텍스트 + 페이지 텍스트의 토큰 수
            combined_text = current_text + "\n\n" + page_text if current_text else page_text
            combined_tokens = estimate_tokens(combined_text)

            if combined_tokens <= self.max_tokens:
                # 병합 가능
                current_text = combined_text
                current_page_end = page.page_no
            else:
                # 현재 청크 저장
                if current_text:
                    chunk = self._create_chunk(
                        content=current_text,
                        page_start=current_page_start,
                        page_end=current_page_end,
                        chunk_index=len(chunks),
                    )
                    chunks.append(chunk)

                # 페이지가 너무 크면 분할
                if page_tokens > self.max_tokens:
                    page_chunks = self._split_large_page(page, len(chunks))
                    chunks.extend(page_chunks)
                    current_text = ""
                    current_page_start = page.page_no + 1
                    current_page_end = page.page_no + 1
                else:
                    # 새 청크 시작
                    current_text = page_text
                    current_page_start = page.page_no
                    current_page_end = page.page_no

        # 마지막 청크
        if current_text:
            chunk = self._create_chunk(
                content=current_text,
                page_start=current_page_start,
                page_end=current_page_end,
                chunk_index=len(chunks),
            )
            chunks.append(chunk)

        # 너무 작은 청크 병합
        chunks = self._merge_small_chunks(chunks)

        # 인덱스 재정렬
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i

        return chunks

    def _create_chunk(
        self,
        content: str,
        page_start: int,
        page_end: int,
        chunk_index: int,
    ) -> Chunk:
        """청크 생성"""
        return Chunk(
            content=content.strip(),
            page_start=page_start,
            page_end=page_end,
            chunk_index=chunk_index,
            token_count=estimate_tokens(content),
            char_count=len(content),
        )

    def _split_large_page(self, page: PageContent, start_index: int) -> list[Chunk]:
        """큰 페이지를 여러 청크로 분할"""
        text = page.text
        chunks: list[Chunk] = []

        # 문단 단위로 분할
        paragraphs = re.split(r"\n\n+", text)

        current_text = ""
        for para in paragraphs:
            para_tokens = estimate_tokens(para)

            if not current_text:
                current_text = para
            elif estimate_tokens(current_text + "\n\n" + para) <= self.target_tokens:
                current_text += "\n\n" + para
            else:
                # 청크 저장
                chunk = self._create_chunk(
                    content=current_text,
                    page_start=page.page_no,
                    page_end=page.page_no,
                    chunk_index=start_index + len(chunks),
                )
                chunks.append(chunk)
                current_text = para

        # 마지막 청크
        if current_text:
            chunk = self._create_chunk(
                content=current_text,
                page_start=page.page_no,
                page_end=page.page_no,
                chunk_index=start_index + len(chunks),
            )
            chunks.append(chunk)

        return chunks

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """작은 청크들을 병합"""
        if len(chunks) <= 1:
            return chunks

        merged: list[Chunk] = []

        for chunk in chunks:
            if not merged:
                merged.append(chunk)
                continue

            last = merged[-1]

            # 마지막 청크가 작거나, 현재 청크가 작으면 병합 시도
            if last.token_count < self.min_tokens or chunk.token_count < self.min_tokens:
                combined_tokens = last.token_count + chunk.token_count
                if combined_tokens <= self.max_tokens:
                    # 병합
                    last.content = last.content + "\n\n" + chunk.content
                    last.page_end = chunk.page_end
                    last.token_count = combined_tokens
                    last.char_count = len(last.content)
                    continue

            merged.append(chunk)

        return merged


def chunk_pages(
    pages: list[tuple[int, str]],
    target_tokens: int = 1000,
    min_tokens: int = 200,
    max_tokens: int = 1500,
) -> list[Chunk]:
    """
    편의 함수: (page_no, text) 리스트를 청크로 분할

    Args:
        pages: [(page_no, text), ...] 리스트
        target_tokens: 목표 토큰 수
        min_tokens: 최소 토큰 수
        max_tokens: 최대 토큰 수

    Returns:
        Chunk 리스트
    """
    from pathlib import Path

    # PDFContent 형태로 변환
    page_contents = [
        PageContent(page_no=pn, text=txt, char_count=len(txt)) for pn, txt in pages
    ]

    pdf_content = PDFContent(
        path=Path("dummy"),
        pages=page_contents,
        total_pages=len(page_contents),
        total_chars=sum(pc.char_count for pc in page_contents),
    )

    chunker = PageAwareChunker(
        target_tokens=target_tokens,
        min_tokens=min_tokens,
        max_tokens=max_tokens,
    )

    return chunker.chunk_pdf_content(pdf_content)
