"""
Document Viewer API Router

GET /documents/{document_id}/page/{page} - PDF 페이지를 이미지로 렌더링
GET /documents/{document_id}/page/{page}/spans - 텍스트 하이라이트 bbox 반환
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import psycopg
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from psycopg.rows import dict_row
from pydantic import BaseModel

router = APIRouter(tags=["documents"])

# 캐시 디렉토리
CACHE_DIR = Path("artifacts/page_cache")


def get_db_url() -> str:
    """환경변수에서 DB URL 가져오기"""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


def get_document_source_path(document_id: int) -> str | None:
    """
    DB에서 document_id로 source_path 조회

    보안: document_id만 사용, 사용자 입력 경로 절대 사용 금지
    """
    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_path FROM documents WHERE id = %s",
                (document_id,),
            )
            row = cur.fetchone()
            if row:
                return row["source_path"]
    return None


def get_cache_path(document_id: int, page: int, scale: float) -> Path:
    """캐시 파일 경로 생성"""
    return CACHE_DIR / f"{document_id}_{page}_{scale:.1f}.png"


def render_pdf_page(source_path: str, page: int, scale: float) -> bytes:
    """
    PDF 페이지를 PNG로 렌더링

    Args:
        source_path: PDF 파일 경로 (DB에서 가져온 값)
        page: 1-based 페이지 번호
        scale: 렌더링 스케일 (1.0 ~ 4.0)

    Returns:
        PNG 이미지 바이트

    Raises:
        FileNotFoundError: 파일 없음
        ValueError: 페이지 범위 초과
        RuntimeError: 렌더링 실패
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"PDF file not found")

    try:
        doc = fitz.open(source_path)
    except Exception as e:
        raise RuntimeError(f"Failed to open PDF")

    try:
        # 페이지 범위 확인 (page는 1-based, fitz는 0-based)
        page_count = len(doc)
        if page < 1 or page > page_count:
            raise ValueError(f"Page {page} out of range (1-{page_count})")

        # 페이지 렌더링
        pdf_page = doc[page - 1]  # 0-based index
        mat = fitz.Matrix(scale, scale)
        pix = pdf_page.get_pixmap(matrix=mat)

        # PNG로 변환
        png_bytes = pix.tobytes("png")
        return png_bytes

    finally:
        doc.close()


@lru_cache(maxsize=100)
def cached_render(document_id: int, page: int, scale: float) -> bytes:
    """
    메모리 캐시 + 디스크 캐시

    LRU 캐시로 최근 100개 요청 메모리 캐시
    """
    # 디스크 캐시 확인
    cache_path = get_cache_path(document_id, page, scale)
    if cache_path.exists():
        return cache_path.read_bytes()

    # source_path 조회
    source_path = get_document_source_path(document_id)
    if source_path is None:
        raise FileNotFoundError("Document not found")

    # 렌더링
    png_bytes = render_pdf_page(source_path, page, scale)

    # 디스크 캐시 저장
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(png_bytes)

    return png_bytes


@router.get("/documents/{document_id}/page/{page}")
async def get_document_page(
    document_id: int,
    page: int,
    scale: float = Query(default=2.0, ge=1.0, le=4.0, description="렌더링 스케일"),
) -> Response:
    """
    PDF 문서의 특정 페이지를 PNG 이미지로 반환

    - **document_id**: 문서 ID (DB에서 조회)
    - **page**: 페이지 번호 (1-based)
    - **scale**: 이미지 스케일 (1.0 ~ 4.0, 기본 2.0)

    Returns:
        PNG 이미지

    Errors:
        - 404: 문서 없음 또는 페이지 범위 초과
        - 500: 렌더링 실패
    """
    # scale을 1자리 소수점으로 정규화 (캐시 키 일관성)
    scale = round(scale, 1)

    try:
        png_bytes = cached_render(document_id, page, scale)
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
            },
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Document or page not found")

    except ValueError as e:
        # 페이지 범위 초과
        raise HTTPException(status_code=404, detail="Page out of range")

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail="Failed to render page")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/documents/{document_id}/info")
async def get_document_info(document_id: int) -> dict:
    """
    문서 정보 조회 (페이지 수 등)

    Returns:
        - page_count: 총 페이지 수
        - source_path: 파일 경로
    """
    source_path = get_document_source_path(document_id)
    if source_path is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    try:
        doc = fitz.open(source_path)
        page_count = len(doc)
        doc.close()

        return {
            "document_id": document_id,
            "page_count": page_count,
            "source_path": source_path,
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read PDF")


# -----------------------------------------------------------------------------
# Highlight Spans API
# -----------------------------------------------------------------------------

# 쿼리 최대 길이 제한
MAX_QUERY_LENGTH = 200


class SpanHit(BaseModel):
    """단일 하이라이트 영역"""

    bbox: list[float]  # [x0, y0, x1, y1]
    score: float
    text: str


class SpansResponse(BaseModel):
    """하이라이트 영역 응답"""

    document_id: int
    page: int
    hits: list[SpanHit]


def normalize_text(text: str) -> str:
    """
    텍스트 정규화: 공백/특수문자 축약, 소문자화
    """
    # 유니코드 정규화 (NFC)
    text = unicodedata.normalize("NFC", text)
    # 공백 정규화 (연속 공백 → 단일 공백)
    text = re.sub(r"\s+", " ", text)
    # 앞뒤 공백 제거
    text = text.strip()
    return text


def fuzzy_match_score(query: str, target: str) -> float:
    """
    두 텍스트의 유사도 점수 (0.0 ~ 1.0)
    """
    query_norm = normalize_text(query).lower()
    target_norm = normalize_text(target).lower()

    if not query_norm or not target_norm:
        return 0.0

    return SequenceMatcher(None, query_norm, target_norm).ratio()


def find_text_spans(
    source_path: str,
    page: int,
    query: str,
    max_hits: int = 5,
    min_score: float = 0.5,
) -> list[dict[str, Any]]:
    """
    PDF 페이지에서 쿼리 텍스트와 매칭되는 영역 찾기

    Args:
        source_path: PDF 파일 경로
        page: 1-based 페이지 번호
        query: 검색할 텍스트
        max_hits: 최대 반환 개수
        min_score: 최소 유사도 점수

    Returns:
        매칭된 영역 리스트 [{"bbox": [x0, y0, x1, y1], "score": 0.9, "text": "..."}]
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError("PDF file not found")

    query_norm = normalize_text(query)
    if not query_norm:
        return []

    try:
        doc = fitz.open(source_path)
    except Exception:
        raise RuntimeError("Failed to open PDF")

    try:
        page_count = len(doc)
        if page < 1 or page > page_count:
            raise ValueError(f"Page {page} out of range (1-{page_count})")

        pdf_page = doc[page - 1]

        # 방법 1: 정확한 텍스트 검색 (search_for)
        # PyMuPDF의 search_for는 정확한 문자열 검색
        exact_rects = pdf_page.search_for(query_norm[:50])  # 앞 50자로 검색
        if exact_rects:
            hits = []
            for rect in exact_rects[:max_hits]:
                # 검색된 영역의 텍스트 추출
                matched_text = pdf_page.get_textbox(rect)
                hits.append(
                    {
                        "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                        "score": 1.0,
                        "text": matched_text[:100] if matched_text else query_norm[:50],
                    }
                )
            return hits

        # 방법 2: 블록 단위 fuzzy 매칭
        # "blocks"는 [x0, y0, x1, y1, "text", block_no, block_type]
        blocks = pdf_page.get_text("blocks")

        candidates = []
        for block in blocks:
            if len(block) < 5:
                continue
            if block[6] != 0:  # block_type: 0 = text
                continue

            block_text = str(block[4])
            score = fuzzy_match_score(query_norm, block_text)

            if score >= min_score:
                candidates.append(
                    {
                        "bbox": [block[0], block[1], block[2], block[3]],
                        "score": score,
                        "text": block_text[:100],
                    }
                )

        # 점수 내림차순 정렬
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:max_hits]

    finally:
        doc.close()


@router.get("/documents/{document_id}/page/{page}/spans")
async def get_page_spans(
    document_id: int,
    page: int,
    q: str = Query(..., description="하이라이트할 텍스트", min_length=1),
    max_hits: int = Query(default=5, ge=1, le=20, description="최대 반환 개수"),
) -> SpansResponse:
    """
    PDF 페이지에서 텍스트 하이라이트 영역 찾기

    - **document_id**: 문서 ID
    - **page**: 페이지 번호 (1-based)
    - **q**: 검색할 텍스트 (최대 200자)
    - **max_hits**: 최대 반환 개수 (기본 5, 최대 20)

    Returns:
        hits: 매칭된 영역 리스트 (bbox, score, text)

    Note:
        - 매칭 실패 시 hits=[] 반환 (200 OK)
        - bbox는 PDF 좌표계 기준 (스케일 미적용)
    """
    # 쿼리 길이 제한
    query = q[:MAX_QUERY_LENGTH]

    source_path = get_document_source_path(document_id)
    if source_path is None:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        hits = find_text_spans(source_path, page, query, max_hits)
        return SpansResponse(
            document_id=document_id,
            page=page,
            hits=[SpanHit(**h) for h in hits],
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF file not found")

    except ValueError as e:
        raise HTTPException(status_code=404, detail="Page out of range")

    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to process PDF")

    except Exception:
        # 매칭 실패 등은 빈 결과로 반환
        return SpansResponse(document_id=document_id, page=page, hits=[])
