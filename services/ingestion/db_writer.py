"""
Database Writer

Postgres + pgvector에 document/chunk 적재
psycopg 사용

BIGSERIAL 기반 ID 체계
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .chunker import Chunk
from .manifest import ManifestData


def get_db_url() -> str:
    """환경변수에서 DB URL 가져오기"""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


@dataclass
class DocumentRecord:
    """Document 레코드"""

    id: int
    sha256: str
    insurer_id: int | None
    product_id: int | None
    plan_id: int | None
    doc_type: str
    source_path: str
    meta: dict[str, Any]


@dataclass
class ChunkRecord:
    """Chunk 레코드"""

    id: int
    document_id: int
    insurer_id: int | None
    product_id: int | None
    plan_id: int | None
    doc_type: str
    content: str
    embedding: list[float]
    page_start: int
    page_end: int
    chunk_index: int
    meta: dict[str, Any]


class DBWriter:
    """데이터베이스 쓰기 담당"""

    def __init__(self, db_url: str | None = None):
        self._db_url = db_url or get_db_url()
        self._conn: psycopg.Connection | None = None

    def connect(self) -> None:
        """DB 연결"""
        if self._conn is None:
            self._conn = psycopg.connect(self._db_url, row_factory=dict_row)

    def close(self) -> None:
        """DB 연결 종료"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "DBWriter":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None:
            self.connect()
        return self._conn  # type: ignore

    # =========================================================================
    # Insurer
    # =========================================================================
    def get_or_create_insurer(self, insurer_code: str) -> int:
        """insurer 조회 또는 생성, insurer_id 반환"""
        with self.conn.cursor() as cur:
            # 조회
            cur.execute(
                "SELECT insurer_id FROM insurer WHERE insurer_code = %s",
                (insurer_code.upper(),),
            )
            row = cur.fetchone()
            if row:
                return row["insurer_id"]

            # 생성 (BIGSERIAL이므로 id 자동 생성)
            cur.execute(
                """
                INSERT INTO insurer (insurer_code, insurer_name)
                VALUES (%s, %s)
                ON CONFLICT (insurer_code) DO UPDATE SET insurer_code = EXCLUDED.insurer_code
                RETURNING insurer_id
                """,
                (insurer_code.upper(), insurer_code),
            )
            self.conn.commit()
            row = cur.fetchone()
            if row:
                return row["insurer_id"]

            # fallback: 다시 조회
            cur.execute(
                "SELECT insurer_id FROM insurer WHERE insurer_code = %s",
                (insurer_code.upper(),),
            )
            row = cur.fetchone()
            return row["insurer_id"] if row else 0

    # =========================================================================
    # Product
    # =========================================================================
    def get_or_create_product(
        self,
        insurer_id: int,
        product_name: str,
        product_version: str | None = None,
    ) -> int:
        """product 조회 또는 생성, product_id 반환"""
        with self.conn.cursor() as cur:
            # 조회
            if product_version:
                cur.execute(
                    """
                    SELECT product_id FROM product
                    WHERE insurer_id = %s AND product_name = %s AND product_version = %s
                    """,
                    (insurer_id, product_name, product_version),
                )
            else:
                cur.execute(
                    """
                    SELECT product_id FROM product
                    WHERE insurer_id = %s AND product_name = %s AND product_version IS NULL
                    """,
                    (insurer_id, product_name),
                )
            row = cur.fetchone()
            if row:
                return row["product_id"]

            # 생성 (BIGSERIAL이므로 id 자동 생성)
            cur.execute(
                """
                INSERT INTO product (insurer_id, product_name, product_version)
                VALUES (%s, %s, %s)
                RETURNING product_id
                """,
                (insurer_id, product_name, product_version),
            )
            self.conn.commit()
            row = cur.fetchone()
            if row:
                return row["product_id"]

            # fallback: 다시 조회
            if product_version:
                cur.execute(
                    """
                    SELECT product_id FROM product
                    WHERE insurer_id = %s AND product_name = %s AND product_version = %s
                    """,
                    (insurer_id, product_name, product_version),
                )
            else:
                cur.execute(
                    """
                    SELECT product_id FROM product
                    WHERE insurer_id = %s AND product_name = %s AND product_version IS NULL
                    """,
                    (insurer_id, product_name),
                )
            row = cur.fetchone()
            return row["product_id"] if row else 0

    # =========================================================================
    # Plan
    # =========================================================================
    def get_or_create_plan(
        self,
        product_id: int,
        plan_name: str | None,
        gender: str = "U",
        age_min: int | None = None,
        age_max: int | None = None,
        meta: dict | None = None,
    ) -> int | None:
        """plan 조회 또는 생성, plan_id 반환 (plan_name이 없으면 None)"""
        if not plan_name:
            return None

        with self.conn.cursor() as cur:
            # 조회
            cur.execute(
                """
                SELECT plan_id FROM product_plan
                WHERE product_id = %s AND plan_name = %s
                """,
                (product_id, plan_name),
            )
            row = cur.fetchone()
            if row:
                return row["plan_id"]

            # 생성 (BIGSERIAL이므로 id 자동 생성)
            cur.execute(
                """
                INSERT INTO product_plan (product_id, plan_name, gender, age_min, age_max, meta)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING plan_id
                """,
                (
                    product_id,
                    plan_name,
                    gender,
                    age_min,
                    age_max,
                    json.dumps(meta or {}),
                ),
            )
            self.conn.commit()
            row = cur.fetchone()
            if row:
                return row["plan_id"]

            # fallback: 다시 조회
            cur.execute(
                """
                SELECT plan_id FROM product_plan
                WHERE product_id = %s AND plan_name = %s
                """,
                (product_id, plan_name),
            )
            row = cur.fetchone()
            return row["plan_id"] if row else None

    # =========================================================================
    # Document
    # =========================================================================
    def document_exists(self, sha256: str) -> tuple[bool, int | None]:
        """문서 존재 여부 및 document_id 반환"""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT document_id FROM document WHERE sha256 = %s",
                (sha256,),
            )
            row = cur.fetchone()
            if row:
                return True, row["document_id"]
            return False, None

    def insert_document(
        self,
        sha256: str,
        insurer_id: int | None,
        product_id: int | None,
        plan_id: int | None,
        doc_type: str,
        source_path: str,
        meta: dict[str, Any] | None = None,
    ) -> int:
        """document 삽입, document_id 반환"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document (sha256, insurer_id, product_id, plan_id, doc_type, source_path, meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sha256) DO NOTHING
                RETURNING document_id
                """,
                (
                    sha256,
                    insurer_id,
                    product_id,
                    plan_id,
                    doc_type,
                    source_path,
                    json.dumps(meta or {}),
                ),
            )
            self.conn.commit()
            row = cur.fetchone()
            if row:
                return row["document_id"]

            # ON CONFLICT 발생 시 기존 ID 조회
            cur.execute(
                "SELECT document_id FROM document WHERE sha256 = %s",
                (sha256,),
            )
            row = cur.fetchone()
            return row["document_id"] if row else 0

    # =========================================================================
    # Chunk
    # =========================================================================
    def insert_chunk(
        self,
        document_id: int,
        insurer_id: int | None,
        product_id: int | None,
        plan_id: int | None,
        doc_type: str,
        content: str,
        embedding: list[float],
        page_start: int,
        page_end: int,
        chunk_index: int,
        meta: dict[str, Any] | None = None,
    ) -> int:
        """chunk 삽입, chunk_id 반환"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chunk (
                    document_id, insurer_id, product_id, plan_id,
                    doc_type, content, embedding, page_start, page_end,
                    chunk_index, meta
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING chunk_id
                """,
                (
                    document_id,
                    insurer_id,
                    product_id,
                    plan_id,
                    doc_type,
                    content,
                    embedding,
                    page_start,
                    page_end,
                    chunk_index,
                    json.dumps(meta or {}),
                ),
            )
            self.conn.commit()
            row = cur.fetchone()
            return row["chunk_id"] if row else 0

    def insert_chunks_batch(
        self,
        chunks: list[dict[str, Any]],
    ) -> int:
        """
        청크 배치 삽입, 삽입된 수 반환

        chunks format:
        {
            "document_id": int,
            "insurer_id": int | None,
            "product_id": int | None,
            "plan_id": int | None,
            "doc_type": str,
            "content": str,
            "embedding": list[float],
            "page_start": int,
            "page_end": int,
            "chunk_index": int,
            "meta": str (JSON),
        }
        """
        if not chunks:
            return 0

        with self.conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO chunk (
                    document_id, insurer_id, product_id, plan_id,
                    doc_type, content, embedding, page_start, page_end,
                    chunk_index, meta
                )
                VALUES (
                    %(document_id)s, %(insurer_id)s, %(product_id)s, %(plan_id)s,
                    %(doc_type)s, %(content)s, %(embedding)s, %(page_start)s, %(page_end)s,
                    %(chunk_index)s, %(meta)s
                )
                """,
                chunks,
            )
            self.conn.commit()
            return len(chunks)

    def delete_chunks_by_document(self, document_id: int) -> int:
        """문서의 모든 청크 삭제, 삭제된 수 반환"""
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chunk WHERE document_id = %s",
                (document_id,),
            )
            self.conn.commit()
            return cur.rowcount

    # =========================================================================
    # Helper
    # =========================================================================
    def resolve_ids_from_manifest(
        self,
        manifest: ManifestData,
        default_product_name: str = "UNKNOWN_PRODUCT",
    ) -> tuple[int | None, int | None, int | None]:
        """
        manifest에서 insurer_id, product_id, plan_id 해결

        Returns:
            (insurer_id, product_id, plan_id) - 모두 BIGINT (int)
        """
        insurer_id: int | None = None
        product_id: int | None = None
        plan_id: int | None = None

        # insurer
        if manifest.insurer_code:
            insurer_id = self.get_or_create_insurer(manifest.insurer_code)

        # product
        if insurer_id:
            product_name = manifest.product.product_name or default_product_name
            product_version = manifest.product.product_version
            product_id = self.get_or_create_product(
                insurer_id, product_name, product_version
            )

        # plan
        if product_id and manifest.plan.plan_name:
            plan_id = self.get_or_create_plan(
                product_id=product_id,
                plan_name=manifest.plan.plan_name,
                gender=manifest.plan.gender,
                age_min=manifest.plan.age_min,
                age_max=manifest.plan.age_max,
                meta=manifest.plan.meta,
            )

        return insurer_id, product_id, plan_id
