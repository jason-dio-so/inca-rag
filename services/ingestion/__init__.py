"""
Ingestion Module

보험 문서 PDF를 처리하여 Postgres+pgvector에 적재
"""

from .chunker import Chunk, PageAwareChunker, chunk_pages
from .coverage_extractor import CoverageExtractor, CoverageMatch, extract_coverage
from .coverage_ontology import COVERAGE_ONTOLOGY, CoverageCode, get_coverage_by_code
from .db_writer import DBWriter
from .embedding import (
    DummyEmbeddingProvider,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    create_provider,
    embed_text,
    embed_texts,
    get_embedding_provider,
    set_embedding_provider,
)
from .manifest import ManifestData, load_manifest, resolve_manifest
from .pdf_loader import PDFContent, PageContent, load_pdf
from .utils import IngestionStats, sha256_file, setup_logging

__all__ = [
    # Chunker
    "Chunk",
    "PageAwareChunker",
    "chunk_pages",
    # Coverage
    "CoverageCode",
    "CoverageExtractor",
    "CoverageMatch",
    "COVERAGE_ONTOLOGY",
    "extract_coverage",
    "get_coverage_by_code",
    # DB
    "DBWriter",
    # Embedding
    "DummyEmbeddingProvider",
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "create_provider",
    "embed_text",
    "embed_texts",
    "get_embedding_provider",
    "set_embedding_provider",
    # Manifest
    "ManifestData",
    "load_manifest",
    "resolve_manifest",
    # PDF
    "PDFContent",
    "PageContent",
    "load_pdf",
    # Utils
    "IngestionStats",
    "sha256_file",
    "setup_logging",
]
