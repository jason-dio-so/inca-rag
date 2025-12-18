#!/usr/bin/env python3
"""
Ingestion CLI

PDF 문서를 처리하여 Postgres+pgvector에 적재

Usage:
    python services/ingestion/ingest.py --root data --insurer SAMSUNG
    python services/ingestion/ingest.py --root data --insurer SAMSUNG --dry-run
    python services/ingestion/ingest.py --root data --insurer SAMSUNG --doc-type 약관 --limit 5
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# 모듈 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.ingestion.chunker import Chunk, PageAwareChunker
from services.ingestion.coverage_extractor import extract_coverage, get_extractor
from services.ingestion.db_writer import DBWriter
from services.ingestion.embedding import embed_text, get_embedding_provider
from services.ingestion.manifest import ManifestData, resolve_manifest
from services.ingestion.pdf_loader import PDFContent, load_pdf
from services.ingestion.plan_detector import detect_plan_id
from services.ingestion.utils import (
    IngestionStats,
    extract_doc_type_from_path,
    extract_insurer_code,
    find_pdfs_recursive,
    setup_logging,
    sha256_file,
    truncate_text,
)


def process_single_document(
    pdf_path: Path,
    root: Path,
    manifest: ManifestData,
    chunker: PageAwareChunker,
    db_writer: DBWriter | None,
    stats: IngestionStats,
    logger: logging.Logger,
    dry_run: bool = False,
    default_product_name: str = "UNKNOWN_PRODUCT",
) -> bool:
    """
    단일 PDF 문서 처리

    Returns:
        True if document was processed (inserted), False if skipped
    """
    try:
        # 1. SHA256 계산
        file_sha256 = sha256_file(pdf_path)
        logger.info(f"Processing: {pdf_path.name} (sha256: {file_sha256[:16]}...)")

        # 2. 중복 체크
        if db_writer and not dry_run:
            exists, existing_doc_id = db_writer.document_exists(file_sha256)
            if exists:
                logger.info(f"  SKIP: Document already exists (id: {existing_doc_id})")
                stats.documents_skipped += 1
                return False

        # 3. PDF 로드
        pdf_content = load_pdf(pdf_path)
        stats.total_pages += pdf_content.total_pages
        logger.info(f"  Pages: {pdf_content.total_pages}, Chars: {pdf_content.total_chars}")

        # 4. 청킹
        chunks = chunker.chunk_pdf_content(pdf_content)
        logger.info(f"  Chunks: {len(chunks)}")

        # 5. ID 해결 (insurer, product, plan)
        insurer_id = None
        product_id = None
        plan_id = None

        if db_writer and not dry_run:
            insurer_id, product_id, plan_id = db_writer.resolve_ids_from_manifest(
                manifest, default_product_name
            )
            logger.debug(
                f"  IDs: insurer={insurer_id}, product={product_id}, plan={plan_id}"
            )

            # 5-1. Plan 자동 감지 (manifest에 plan 정보가 없는 경우)
            if plan_id is None and manifest.insurer_code:
                try:
                    detector_result = detect_plan_id(
                        conn=db_writer.conn,
                        insurer_code=manifest.insurer_code,
                        source_path=str(pdf_path),
                        doc_title=manifest.document.title,
                        meta=manifest.document.meta,
                    )
                    if detector_result.plan_id:
                        plan_id = detector_result.plan_id
                        logger.info(f"  Plan auto-detected: {plan_id} ({detector_result.reason})")
                    elif detector_result.detected_info.gender or detector_result.detected_info.age_min:
                        logger.debug(f"  Plan detection: {detector_result.reason}")
                except Exception as e:
                    logger.warning(f"  Plan detection failed: {e}")

        # 6. Document 메타 준비
        doc_meta: dict[str, Any] = {}
        if manifest.document.meta:
            doc_meta.update(manifest.document.meta)
        if manifest.document.title:
            doc_meta["title"] = manifest.document.title
        if manifest.document.effective_date:
            doc_meta["effective_date"] = manifest.document.effective_date

        # 7. Document 삽입
        doc_type = manifest.doc_type or "기타"

        # SOURCE_PATH_ROOT 환경변수로 경로 변환 (컨테이너 배포용)
        # 예: SOURCE_PATH_ROOT=/app/data, root=data → /Users/.../data/samsung/... → /app/data/samsung/...
        source_path_root = os.environ.get("SOURCE_PATH_ROOT")
        if source_path_root:
            # root 기준 상대경로를 SOURCE_PATH_ROOT에 연결
            rel_path = pdf_path.relative_to(root)
            source_path = str(Path(source_path_root) / rel_path)
        else:
            source_path = str(pdf_path)

        doc_id: int | None = None
        if db_writer and not dry_run:
            doc_id = db_writer.insert_document(
                sha256=file_sha256,
                insurer_id=insurer_id,
                product_id=product_id,
                plan_id=plan_id,
                doc_type=doc_type,
                source_path=source_path,
                meta=doc_meta,
            )
            logger.info(f"  Document inserted: {doc_id}")
        else:
            doc_id = 0  # dry-run용 임시 ID
            logger.info(f"  [DRY-RUN] Document would be inserted")

        stats.documents_inserted += 1

        # 8. Chunk 처리 및 삽입
        chunk_records: list[dict[str, Any]] = []

        for chunk in chunks:
            # Coverage 추출 (DB 매핑 우선, insurer_id/doc_type 전달)
            coverage_meta = extract_coverage(
                content=chunk.content,
                insurer_id=insurer_id,
                doc_type=doc_type,
            )

            if coverage_meta:
                code = coverage_meta.get("coverage_code", "")
                if code:
                    stats.add_coverage_hit(code)

            # Chunk 메타
            chunk_meta: dict[str, Any] = {
                "token_count": chunk.token_count,
                "char_count": chunk.char_count,
            }
            if coverage_meta:
                chunk_meta["entities"] = coverage_meta
            if chunk.section:
                chunk_meta["section"] = chunk.section

            # Embedding
            embedding = embed_text(chunk.content)

            # Chunk 레코드 (chunk_id는 BIGSERIAL 자동생성)
            chunk_record = {
                "document_id": doc_id,
                "insurer_id": insurer_id,
                "product_id": product_id,
                "plan_id": plan_id,
                "doc_type": doc_type,
                "content": chunk.content,
                "embedding": embedding,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "chunk_index": chunk.chunk_index,
                "meta": json.dumps(chunk_meta),
            }
            chunk_records.append(chunk_record)

        # Batch insert
        if db_writer and not dry_run:
            inserted = db_writer.insert_chunks_batch(chunk_records)
            logger.info(f"  Chunks inserted: {inserted}")
        else:
            logger.info(f"  [DRY-RUN] {len(chunk_records)} chunks would be inserted")

        stats.chunks_created += len(chunks)
        return True

    except Exception as e:
        error_msg = f"Error processing {pdf_path}: {e}"
        logger.error(error_msg)
        stats.add_error(error_msg)
        return False


def run_ingestion(
    root: Path,
    insurer_code: str | None = None,
    doc_type_filter: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    default_product_name: str = "UNKNOWN_PRODUCT",
    chunk_tokens: int = 1000,
    db_url: str | None = None,
) -> IngestionStats:
    """
    Ingestion 실행

    Args:
        root: 데이터 루트 경로
        insurer_code: 특정 보험사만 처리 (None이면 전체)
        doc_type_filter: 특정 doc_type만 처리
        limit: 처리할 문서 수 제한
        dry_run: DB 쓰기 없이 실행
        default_product_name: product_name이 없을 때 기본값
        chunk_tokens: 청크 목표 토큰 수
        db_url: DB 연결 URL

    Returns:
        IngestionStats
    """
    logger = setup_logging()
    stats = IngestionStats()

    # Chunker 초기화
    chunker = PageAwareChunker(
        target_tokens=chunk_tokens,
        min_tokens=200,
        max_tokens=1500,
    )

    # PDF 파일 목록
    pdfs = find_pdfs_recursive(root, insurer_code)

    # doc_type 필터
    if doc_type_filter:
        pdfs = [
            p
            for p in pdfs
            if extract_doc_type_from_path(p, root) == doc_type_filter
        ]

    # limit 적용
    if limit:
        pdfs = pdfs[:limit]

    logger.info(f"Found {len(pdfs)} PDF files to process")

    if not pdfs:
        logger.warning("No PDF files found")
        return stats

    # DB Writer
    db_writer: DBWriter | None = None
    if not dry_run:
        try:
            db_writer = DBWriter(db_url)
            db_writer.connect()
            logger.info("Database connected")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            logger.info("Continuing in dry-run mode")
            dry_run = True

    try:
        for pdf_path in pdfs:
            stats.documents_processed += 1

            # Manifest 해결
            detected_insurer = extract_insurer_code(pdf_path, root)
            detected_doc_type = extract_doc_type_from_path(pdf_path, root)

            manifest = resolve_manifest(
                pdf_path=pdf_path,
                root=root,
                insurer_code=detected_insurer,
                doc_type=detected_doc_type,
            )

            # 문서 처리
            process_single_document(
                pdf_path=pdf_path,
                root=root,
                manifest=manifest,
                chunker=chunker,
                db_writer=db_writer,
                stats=stats,
                logger=logger,
                dry_run=dry_run,
                default_product_name=default_product_name,
            )

    finally:
        if db_writer:
            db_writer.close()
            logger.info("Database connection closed")

    # 결과 출력
    print(stats.summary())
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="보험 문서 Ingestion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 삼성 문서 전체 처리
  python services/ingestion/ingest.py --root data --insurer SAMSUNG

  # Dry-run (DB 쓰기 없이)
  python services/ingestion/ingest.py --root data --insurer SAMSUNG --dry-run

  # 특정 doc_type만 처리
  python services/ingestion/ingest.py --root data --insurer SAMSUNG --doc-type 약관

  # 문서 수 제한
  python services/ingestion/ingest.py --root data --insurer SAMSUNG --limit 5

  # 전체 보험사 처리
  python services/ingestion/ingest.py --root data
        """,
    )

    parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="데이터 루트 경로 (예: data)",
    )

    parser.add_argument(
        "--insurer",
        type=str,
        default=None,
        help="특정 보험사 코드 (예: SAMSUNG, LOTTE). 생략하면 전체",
    )

    parser.add_argument(
        "--doc-type",
        type=str,
        default=None,
        choices=["약관", "사업방법서", "상품요약서", "가입설계서", "기타"],
        help="특정 문서 유형만 처리",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처리할 문서 수 제한",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB 쓰기 없이 실행 (통계만 출력)",
    )

    parser.add_argument(
        "--default-product",
        type=str,
        default="UNKNOWN_PRODUCT",
        help="manifest에 product_name이 없을 때 사용할 기본값",
    )

    parser.add_argument(
        "--chunk-tokens",
        type=int,
        default=1000,
        help="청크 목표 토큰 수 (기본: 1000)",
    )

    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (기본: DATABASE_URL 환경변수)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )

    args = parser.parse_args()

    # 로깅 레벨
    if args.verbose:
        logging.getLogger("ingestion").setLevel(logging.DEBUG)

    # 경로 검증
    root = Path(args.root)
    if not root.exists():
        print(f"[ERROR] 경로가 존재하지 않습니다: {root}")
        return 1

    # 실행
    stats = run_ingestion(
        root=root,
        insurer_code=args.insurer,
        doc_type_filter=args.doc_type,
        limit=args.limit,
        dry_run=args.dry_run,
        default_product_name=args.default_product,
        chunk_tokens=args.chunk_tokens,
        db_url=args.db_url,
    )

    # 에러가 있으면 비정상 종료
    if stats.errors:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
