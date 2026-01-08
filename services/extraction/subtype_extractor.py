"""
Subtype Extractor Service - STEP 4.1

다중 Subtype 비교를 위한 추출 서비스.
경계성 종양, 제자리암 등 질병 하위 개념의 정의·포함 여부·조건 중심 비교 제공.

헌법 준수:
  - 모든 subtype 정의는 config/rules/subtype_slots.yaml에서 로드
  - 코드 내 하드코딩 금지
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SubtypeDefinition:
    """Subtype 정의"""
    code: str  # BORDERLINE_TUMOR, CIS_CARCINOMA, etc.
    name: str  # 경계성 종양, 제자리암
    aliases: list[str]
    domain: str  # CANCER, CARDIO, etc.
    description: str
    comparison_focus: list[str]  # 정의, 보장 여부, 지급 조건


@dataclass
class ExtractedSubtype:
    """질의에서 추출된 Subtype"""
    code: str
    name: str
    matched_alias: str  # 질의에서 매칭된 실제 문자열


@dataclass
class SubtypeComparisonItem:
    """Subtype별 보험사 비교 항목"""
    subtype_code: str
    subtype_name: str
    info_type: str  # definition, coverage, conditions, etc.
    info_label: str  # 정의, 보장 여부, 지급 조건
    insurer_code: str
    value: str | None
    confidence: Literal["high", "medium", "low", "not_found"] = "medium"
    evidence_ref: dict | None = None


@dataclass
class SubtypeComparisonResult:
    """Subtype 비교 결과"""
    subtypes: list[str]  # 추출된 subtype 코드 리스트
    comparison_items: list[SubtypeComparisonItem] = field(default_factory=list)
    is_multi_subtype: bool = False  # 복수 subtype 비교 여부


# =============================================================================
# Config Loading (SSOT from YAML)
# =============================================================================

_SUBTYPE_CONFIG: dict | None = None
_SUBTYPE_DEFINITIONS: dict[str, SubtypeDefinition] | None = None


def _get_config_path() -> Path:
    """Config 파일 경로 반환"""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "config" / "rules" / "subtype_slots.yaml"


def _load_subtype_config() -> dict:
    """Subtype 설정 로드 (캐시)"""
    global _SUBTYPE_CONFIG

    if _SUBTYPE_CONFIG is not None:
        return _SUBTYPE_CONFIG

    config_path = _get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Subtype config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        _SUBTYPE_CONFIG = yaml.safe_load(f)

    return _SUBTYPE_CONFIG


def _get_subtype_definitions() -> dict[str, SubtypeDefinition]:
    """Subtype 정의 로드 (캐시)"""
    global _SUBTYPE_DEFINITIONS

    if _SUBTYPE_DEFINITIONS is not None:
        return _SUBTYPE_DEFINITIONS

    config = _load_subtype_config()
    subtypes_raw = config.get("subtypes", {})

    _SUBTYPE_DEFINITIONS = {}
    for code, data in subtypes_raw.items():
        _SUBTYPE_DEFINITIONS[code] = SubtypeDefinition(
            code=code,
            name=data.get("name", code),
            aliases=data.get("aliases", []),
            domain=data.get("domain", ""),
            description=data.get("description", ""),
            comparison_focus=data.get("comparison_focus", []),
        )

    return _SUBTYPE_DEFINITIONS


def reset_subtype_cache():
    """테스트용 캐시 리셋"""
    global _SUBTYPE_CONFIG, _SUBTYPE_DEFINITIONS
    _SUBTYPE_CONFIG = None
    _SUBTYPE_DEFINITIONS = None


# =============================================================================
# Subtype Extraction from Query
# =============================================================================

def extract_subtypes_from_query(query: str) -> list[ExtractedSubtype]:
    """
    질의에서 Subtype 추출

    Args:
        query: 사용자 질의

    Returns:
        추출된 Subtype 리스트 (발견 순서)
    """
    definitions = _get_subtype_definitions()
    query_lower = query.lower()

    extracted: list[ExtractedSubtype] = []
    found_codes: set[str] = set()

    # 모든 subtype의 alias를 검색
    for code, defn in definitions.items():
        for alias in defn.aliases:
            if alias.lower() in query_lower and code not in found_codes:
                extracted.append(ExtractedSubtype(
                    code=code,
                    name=defn.name,
                    matched_alias=alias,
                ))
                found_codes.add(code)
                break  # 첫 번째 매칭 alias만 사용

    return extracted


def is_multi_subtype_query(query: str) -> bool:
    """
    복수 Subtype 비교 질의인지 확인

    Args:
        query: 사용자 질의

    Returns:
        복수 subtype이 포함된 경우 True
    """
    extracted = extract_subtypes_from_query(query)
    return len(extracted) >= 2


def get_subtype_definition(code: str) -> SubtypeDefinition | None:
    """
    Subtype 코드로 정의 조회

    Args:
        code: Subtype 코드 (예: BORDERLINE_TUMOR)

    Returns:
        SubtypeDefinition 또는 None
    """
    definitions = _get_subtype_definitions()
    return definitions.get(code)


def get_all_subtype_codes() -> list[str]:
    """모든 Subtype 코드 반환"""
    definitions = _get_subtype_definitions()
    return list(definitions.keys())


def get_subtypes_by_domain(domain: str) -> list[SubtypeDefinition]:
    """
    도메인별 Subtype 목록 반환

    Args:
        domain: 도메인 (CANCER, CARDIO, etc.)

    Returns:
        해당 도메인의 SubtypeDefinition 리스트
    """
    definitions = _get_subtype_definitions()
    return [d for d in definitions.values() if d.domain == domain]


# =============================================================================
# Subtype Comparison Extraction
# =============================================================================

# Subtype별 키워드 (YAML에서 로드)
def _get_subtype_keywords(subtype_code: str) -> list[str]:
    """Subtype의 검색 키워드 반환"""
    defn = get_subtype_definition(subtype_code)
    if defn:
        return defn.aliases
    return []


# 보장 포함/제외 키워드
COVERAGE_POSITIVE_KEYWORDS = ["보장", "지급", "보험금", "해당"]
COVERAGE_NEGATIVE_KEYWORDS = ["제외", "면책", "지급하지", "해당하지", "보장하지"]
PARTIAL_PAYMENT_KEYWORDS = ["감액", "50%", "20%", "10%", "지급률", "일부지급", "부분지급"]

# STEP 4.7: 경계/감액/제한 키워드 (약관에서 추출)
BOUNDARY_KEYWORDS = [
    "감액", "지급률", "면책", "제외", "미지급", "한도", "특약",
    "해당하지 아니", "단", "다만", "50%", "20%", "10%", "1년", "90일",
    "대기기간", "면책기간", "보장개시일", "책임개시일"
]


def extract_subtype_comparison(
    query: str,
    evidence_by_insurer: dict[str, list],
    insurers: list[str],
) -> SubtypeComparisonResult:
    """
    Subtype 비교 정보 추출

    Args:
        query: 사용자 질의
        evidence_by_insurer: 보험사별 evidence 리스트
        insurers: 비교 대상 보험사 코드 리스트

    Returns:
        SubtypeComparisonResult
    """
    # 1. 질의에서 subtype 추출
    extracted = extract_subtypes_from_query(query)

    if not extracted:
        return SubtypeComparisonResult(subtypes=[], is_multi_subtype=False)

    subtype_codes = [e.code for e in extracted]
    is_multi = len(extracted) >= 2

    # 2. 각 subtype별로 보험사 정보 추출
    comparison_items: list[SubtypeComparisonItem] = []

    for subtype in extracted:
        defn = get_subtype_definition(subtype.code)
        if not defn:
            continue

        # comparison_focus에 따라 정보 추출
        for focus in defn.comparison_focus:
            for insurer_code in insurers:
                evidence_list = evidence_by_insurer.get(insurer_code, [])

                item = _extract_subtype_info(
                    subtype_code=subtype.code,
                    subtype_name=defn.name,
                    info_type=_focus_to_info_type(focus),
                    info_label=focus,
                    keywords=defn.aliases,
                    evidence_list=evidence_list,
                    insurer_code=insurer_code,
                )
                comparison_items.append(item)

    return SubtypeComparisonResult(
        subtypes=subtype_codes,
        comparison_items=comparison_items,
        is_multi_subtype=is_multi,
    )


def _focus_to_info_type(focus: str) -> str:
    """comparison_focus를 info_type으로 변환"""
    mapping = {
        "정의": "definition",
        "보장 여부": "coverage",
        "지급 조건": "conditions",
        "경계/감액/제한": "boundary",  # STEP 4.7
        "포함 질병": "included_diseases",
        "지급 비율": "payment_ratio",
        "보장 범위": "coverage_scope",
        "진단 기준": "diagnosis_criteria",
        "포함 질환": "included_diseases",
    }
    return mapping.get(focus, "other")


def _extract_subtype_info(
    subtype_code: str,
    subtype_name: str,
    info_type: str,
    info_label: str,
    keywords: list[str],
    evidence_list: list,
    insurer_code: str,
) -> SubtypeComparisonItem:
    """
    특정 Subtype의 특정 정보 타입 추출

    Args:
        subtype_code: Subtype 코드
        subtype_name: Subtype 이름
        info_type: 정보 타입 (definition, coverage, conditions)
        info_label: 정보 라벨 (정의, 보장 여부, 지급 조건)
        keywords: 검색 키워드
        evidence_list: 증거 리스트
        insurer_code: 보험사 코드

    Returns:
        SubtypeComparisonItem
    """
    # 약관 우선 (subtype 정의/조건은 약관이 원천)
    doc_type_priority = {"약관": 4, "사업방법서": 3, "상품요약서": 2, "가입설계서": 1}

    best_value = None
    best_confidence = "not_found"
    best_evidence_ref = None
    best_priority = 0

    for ev in evidence_list:
        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        preview_lower = preview.lower()

        # 키워드 매칭 확인
        found_keyword = None
        for kw in keywords:
            if kw.lower() in preview_lower:
                found_keyword = kw
                break

        if not found_keyword:
            continue

        doc_priority = doc_type_priority.get(ev.doc_type, 0)
        if doc_priority < best_priority:
            continue

        # 정보 타입에 따른 추출
        if info_type == "definition":
            value = _extract_definition(preview, found_keyword)
        elif info_type == "coverage":
            value, confidence = _extract_coverage_status(preview, found_keyword)
            if value and doc_priority >= best_priority:
                best_value = value
                best_confidence = confidence
                best_priority = doc_priority
                best_evidence_ref = {
                    "document_id": getattr(ev, 'document_id', None),
                    "page_start": getattr(ev, 'page_start', None),
                    "doc_type": ev.doc_type,  # STEP 4.7: 문서 유형 추가
                    "excerpt": preview[:100] if len(preview) > 100 else preview,  # STEP 4.7: 근거 발췌
                }
            continue
        elif info_type == "conditions":
            value = _extract_conditions(preview, found_keyword)
        elif info_type == "boundary":
            # STEP 4.7: 경계/감액/제한 추출
            value = _extract_boundary(preview, found_keyword)
        else:
            value = _extract_generic(preview, found_keyword)

        if value and doc_priority >= best_priority:
            best_value = value
            best_confidence = "high" if doc_priority >= 3 else "medium"
            best_priority = doc_priority
            best_evidence_ref = {
                "document_id": getattr(ev, 'document_id', None),
                "page_start": getattr(ev, 'page_start', None),
                "doc_type": ev.doc_type,  # STEP 4.7: 문서 유형 추가
                "excerpt": preview[:100] if len(preview) > 100 else preview,  # STEP 4.7: 근거 발췌
            }

    return SubtypeComparisonItem(
        subtype_code=subtype_code,
        subtype_name=subtype_name,
        info_type=info_type,
        info_label=info_label,
        insurer_code=insurer_code,
        value=best_value,
        confidence=best_confidence,
        evidence_ref=best_evidence_ref,
    )


def _extract_definition(preview: str, keyword: str) -> str | None:
    """정의 추출"""
    keyword_lower = keyword.lower()
    preview_lower = preview.lower()

    idx = preview_lower.find(keyword_lower)
    if idx == -1:
        return None

    # 키워드 주변 텍스트 추출 (정의 문구 포함)
    start = max(0, idx - 30)
    end = min(len(preview), idx + len(keyword) + 150)
    excerpt = preview[start:end].strip()

    if len(excerpt) >= 20:
        return excerpt[:200]

    return None


def _extract_coverage_status(preview: str, keyword: str) -> tuple[str | None, str]:
    """보장 여부 추출: (Y/N/Unknown, confidence)"""
    keyword_lower = keyword.lower()
    preview_lower = preview.lower()

    idx = preview_lower.find(keyword_lower)
    if idx == -1:
        return None, "not_found"

    # 키워드 주변 텍스트 분석
    start = max(0, idx - 100)
    end = min(len(preview), idx + len(keyword) + 200)
    context = preview[start:end].lower()

    has_positive = any(pk in context for pk in COVERAGE_POSITIVE_KEYWORDS)
    has_negative = any(nk in context for nk in COVERAGE_NEGATIVE_KEYWORDS)
    has_partial = any(pp in context for pp in PARTIAL_PAYMENT_KEYWORDS)

    if has_partial:
        return "부분보장", "medium"
    elif has_negative and not has_positive:
        return "N", "high"
    elif has_positive and not has_negative:
        return "Y", "high"
    elif has_positive and has_negative:
        return "Unknown", "low"
    else:
        return "Unknown", "low"


def _extract_conditions(preview: str, keyword: str) -> str | None:
    """지급 조건 추출"""
    keyword_lower = keyword.lower()
    preview_lower = preview.lower()

    idx = preview_lower.find(keyword_lower)
    if idx == -1:
        return None

    # 조건 관련 키워드 검색
    condition_keywords = ["경우", "시", "때", "조건", "요건", "지급"]

    # 키워드 이후 텍스트에서 조건 문구 찾기
    start = idx
    end = min(len(preview), idx + 300)
    context = preview[start:end]

    for ck in condition_keywords:
        if ck in context:
            ck_idx = context.find(ck)
            snippet_start = max(0, ck_idx - 50)
            snippet_end = min(len(context), ck_idx + 100)
            snippet = context[snippet_start:snippet_end].strip()
            if len(snippet) >= 20:
                return snippet[:150]

    # 조건 키워드 없으면 주변 텍스트
    return context[:150].strip() if len(context) >= 20 else None


def _extract_boundary(preview: str, keyword: str) -> str | None:
    """
    STEP 4.7: 경계/감액/제한 추출

    경계 조건: 감액, 지급률, 면책, 제외, 미지급, 한도, 대기기간 등
    """
    keyword_lower = keyword.lower()
    preview_lower = preview.lower()

    idx = preview_lower.find(keyword_lower)
    if idx == -1:
        return None

    # 경계/제한 관련 키워드 검색
    # 키워드 주변에서 경계 조건 문구 찾기
    start = max(0, idx - 50)
    end = min(len(preview), idx + len(keyword) + 250)
    context = preview[start:end]
    context_lower = context.lower()

    # 경계 조건 키워드 탐지
    found_boundary_keywords = []
    for bk in BOUNDARY_KEYWORDS:
        if bk.lower() in context_lower:
            found_boundary_keywords.append(bk)

    if found_boundary_keywords:
        # 첫 번째 발견된 경계 키워드 주변 텍스트 추출
        first_bk = found_boundary_keywords[0]
        bk_idx = context_lower.find(first_bk.lower())
        if bk_idx != -1:
            snippet_start = max(0, bk_idx - 30)
            snippet_end = min(len(context), bk_idx + 120)
            snippet = context[snippet_start:snippet_end].strip()
            if len(snippet) >= 15:
                return snippet[:150]

    # 경계 키워드 없으면 "특이 경계 조건 없음" 또는 주변 텍스트
    # 약관에서 경계 조건이 없다면 "해당 없음"으로 처리
    return None  # UI에서 "특이 경계 조건 없음"으로 표시


def _extract_generic(preview: str, keyword: str) -> str | None:
    """일반 정보 추출"""
    keyword_lower = keyword.lower()
    preview_lower = preview.lower()

    idx = preview_lower.find(keyword_lower)
    if idx == -1:
        return None

    start = max(0, idx - 30)
    end = min(len(preview), idx + len(keyword) + 120)
    excerpt = preview[start:end].strip()

    return excerpt[:150] if len(excerpt) >= 15 else None


# =============================================================================
# Utility Functions
# =============================================================================

def format_subtype_comparison_table(result: SubtypeComparisonResult, insurers: list[str]) -> str:
    """
    Subtype 비교 결과를 텍스트 테이블로 포맷

    Args:
        result: SubtypeComparisonResult
        insurers: 보험사 코드 리스트

    Returns:
        포맷된 테이블 문자열
    """
    if not result.subtypes or not result.comparison_items:
        return ""

    lines = []

    # 그룹화: subtype_code + info_type별
    grouped: dict[tuple[str, str], dict[str, SubtypeComparisonItem]] = {}
    for item in result.comparison_items:
        key = (item.subtype_code, item.info_type)
        if key not in grouped:
            grouped[key] = {}
        grouped[key][item.insurer_code] = item

    # 테이블 출력
    for (subtype_code, info_type), insurer_items in grouped.items():
        # 첫 번째 항목에서 메타 정보 추출
        first_item = next(iter(insurer_items.values()))
        header = f"[{first_item.subtype_name}] {first_item.info_label}"
        lines.append(header)
        lines.append("-" * 40)

        for insurer in insurers:
            item = insurer_items.get(insurer)
            if item:
                value = item.value if item.value else "(미확인)"
                lines.append(f"  {insurer}: {value}")

        lines.append("")

    return "\n".join(lines)
