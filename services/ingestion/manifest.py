"""
Manifest 로드/검증 모듈

manifest_v1 스키마 지원
manifest가 없을 경우 fallback 처리
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# 쉬운요약서 감지 패턴
EASY_SUMMARY_PATTERN = re.compile(r"쉬운요약서|쉬운\s*요약서|easy", re.IGNORECASE)


@dataclass
class ProductInfo:
    """상품 정보"""

    product_name: str | None = None
    product_version: str | None = None
    product_code: str | None = None


@dataclass
class PlanInfo:
    """플랜 정보"""

    plan_name: str | None = None
    gender: str = "U"  # U/M/F
    age_min: int | None = None
    age_max: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentInfo:
    """문서 정보"""

    title: str | None = None
    effective_date: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def subtype(self) -> str | None:
        return self.meta.get("subtype")


@dataclass
class IngestionInfo:
    """Ingestion 설정"""

    chunk_strategy: str | None = None
    chunk_tokens: int | None = None
    notes: str | None = None


@dataclass
class ManifestData:
    """Manifest 전체 데이터"""

    schema_version: str = "manifest_v1"
    insurer_code: str | None = None
    doc_type: str | None = None
    product: ProductInfo = field(default_factory=ProductInfo)
    plan: PlanInfo = field(default_factory=PlanInfo)
    document: DocumentInfo = field(default_factory=DocumentInfo)
    ingestion: IngestionInfo = field(default_factory=IngestionInfo)

    # 원본 경로 (디버깅용)
    source_path: Path | None = None


def load_manifest(manifest_path: Path) -> ManifestData | None:
    """
    manifest 파일 로드

    Returns:
        ManifestData 또는 None (로드 실패)
    """
    if not manifest_path.exists():
        return None

    try:
        content = manifest_path.read_text(encoding="utf-8")

        if manifest_path.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(content)
        elif manifest_path.suffix == ".json":
            data = json.loads(content)
        else:
            return None

        if not data:
            return None

        return _parse_manifest_data(data, manifest_path)

    except Exception:
        return None


def _parse_manifest_data(data: dict, source_path: Path) -> ManifestData:
    """dict를 ManifestData로 파싱"""
    manifest = ManifestData(source_path=source_path)

    manifest.schema_version = data.get("schema_version", "manifest_v1")
    manifest.insurer_code = data.get("insurer_code")
    manifest.doc_type = data.get("doc_type")

    # product
    product_data = data.get("product", {}) or {}
    manifest.product = ProductInfo(
        product_name=product_data.get("product_name"),
        product_version=product_data.get("product_version"),
        product_code=product_data.get("product_code"),
    )

    # plan
    plan_data = data.get("plan", {}) or {}
    manifest.plan = PlanInfo(
        plan_name=plan_data.get("plan_name"),
        gender=plan_data.get("gender", "U") or "U",
        age_min=plan_data.get("age_min"),
        age_max=plan_data.get("age_max"),
        meta=plan_data.get("meta", {}) or {},
    )

    # document
    doc_data = data.get("document", {}) or {}
    doc_meta = doc_data.get("meta", {}) or {}
    manifest.document = DocumentInfo(
        title=doc_data.get("title"),
        effective_date=doc_data.get("effective_date"),
        meta=doc_meta,
    )

    # ingestion
    ing_data = data.get("ingestion", {}) or {}
    manifest.ingestion = IngestionInfo(
        chunk_strategy=ing_data.get("chunk_strategy"),
        chunk_tokens=ing_data.get("chunk_tokens"),
        notes=ing_data.get("notes"),
    )

    return manifest


def create_fallback_manifest(
    pdf_path: Path,
    root: Path,
    insurer_code: str | None = None,
    doc_type: str | None = None,
) -> ManifestData:
    """
    manifest가 없을 때 fallback으로 생성

    - insurer_code: 경로에서 추출 또는 인자
    - doc_type: 경로에서 추출 또는 인자
    - subtype: 파일명에서 추론 (쉬운요약서 → easy)
    """
    manifest = ManifestData()

    # insurer_code
    if insurer_code:
        manifest.insurer_code = insurer_code.upper()
    else:
        try:
            relative = pdf_path.relative_to(root)
            if relative.parts:
                manifest.insurer_code = relative.parts[0].upper()
        except ValueError:
            pass

    # doc_type
    if doc_type:
        manifest.doc_type = doc_type
    else:
        valid_doc_types = {"약관", "사업방법서", "상품요약서", "가입설계서", "기타"}
        try:
            relative = pdf_path.relative_to(root)
            if len(relative.parts) >= 2:
                folder = relative.parts[1]
                if folder in valid_doc_types:
                    manifest.doc_type = folder
        except ValueError:
            pass

    # subtype 추론 (상품요약서인 경우)
    if manifest.doc_type == "상품요약서":
        filename = pdf_path.name
        if EASY_SUMMARY_PATTERN.search(filename):
            manifest.document.meta["subtype"] = "easy"
        else:
            manifest.document.meta["subtype"] = "standard"

    return manifest


def resolve_manifest(
    pdf_path: Path,
    root: Path,
    insurer_code: str | None = None,
    doc_type: str | None = None,
) -> ManifestData:
    """
    PDF에 대한 manifest 해결

    1. PDF 옆의 manifest 파일이 있으면 로드
    2. 없으면 fallback 생성

    Returns:
        ManifestData
    """
    from .utils import find_manifest_for_pdf

    manifest_path = find_manifest_for_pdf(pdf_path)

    if manifest_path:
        manifest = load_manifest(manifest_path)
        if manifest:
            # manifest에서 누락된 필드 보완
            if not manifest.insurer_code and insurer_code:
                manifest.insurer_code = insurer_code.upper()
            if not manifest.doc_type and doc_type:
                manifest.doc_type = doc_type

            # 상품요약서인데 subtype이 없으면 파일명에서 추론
            if manifest.doc_type == "상품요약서" and not manifest.document.subtype:
                filename = pdf_path.name
                if EASY_SUMMARY_PATTERN.search(filename):
                    manifest.document.meta["subtype"] = "easy"
                else:
                    manifest.document.meta["subtype"] = "standard"

            return manifest

    # fallback
    return create_fallback_manifest(pdf_path, root, insurer_code, doc_type)
