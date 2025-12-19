"""
Slot Extractor Service - U-4.8 Comparison Slots v0.1

암진단비 담보군에 대한 슬롯 기반 비교 추출

A2 정책 유지:
  - comparable=true 슬롯: 가입설계서/상품요약서/사업방법서에서 추출
  - comparable=false 슬롯: 약관에서 추출 (비교 계산 미사용)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

import yaml
from pathlib import Path

from .llm_trace import LLMTrace
from .amount_extractor import (
    extract_amount,
    extract_diagnosis_lump_sum,
    extract_surgery_amount,
    extract_surgery_count_limit,
)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SlotEvidenceRef:
    """슬롯 근거 참조"""
    document_id: int
    page_start: int | None
    chunk_id: int | None = None


@dataclass
class SlotInsurerValue:
    """슬롯 보험사별 값"""
    insurer_code: str
    value: str | None
    confidence: Literal["high", "medium", "low", "not_found"] = "medium"
    reason: str | None = None
    evidence_refs: list[SlotEvidenceRef] = field(default_factory=list)
    trace: LLMTrace | None = None  # LLM usage trace


@dataclass
class ComparisonSlot:
    """비교 슬롯"""
    slot_key: str
    label: str
    comparable: bool
    insurers: list[SlotInsurerValue] = field(default_factory=list)
    diff_summary: str | None = None


# =============================================================================
# Slot Definitions (from YAML or inline)
# =============================================================================

# =============================================================================
# Slot Definition Registry (coverage_type별 슬롯 정의)
# =============================================================================

# 암진단비 슬롯 정의
CANCER_DIAGNOSIS_SLOTS = [
    {
        "slot_key": "diagnosis_lump_sum_amount",  # 범용화: 진단비 일시금 전용 슬롯
        "label": "진단비 지급금액(일시금)",
        "comparable": True,
        "source_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
        "extractor": "diagnosis_lump_sum",  # 추출기 지정
    },
    {
        "slot_key": "existence_status",
        "label": "담보 존재 여부",
        "comparable": True,
        "source_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
    },
    {
        "slot_key": "payout_condition_summary",
        "label": "지급조건 요약",
        "comparable": True,
        "source_doc_types": ["상품요약서", "사업방법서", "가입설계서"],
    },
    {
        "slot_key": "diagnosis_scope_definition",
        "label": "진단 범위 정의",
        "comparable": False,
        "source_doc_types": ["약관"],
    },
    {
        "slot_key": "waiting_period",
        "label": "대기기간",
        "comparable": False,
        "source_doc_types": ["약관"],
    },
]

# 암진단비 관련 coverage_codes
# A4200_1: 암진단비(유사암제외) - 표준코드
# A4210: 유사암진단비
# A4209: 암진단비
# A4299_1: 암진단비(유사암제외) - 삼성화재 variant
CANCER_COVERAGE_CODES = {"A4200_1", "A4210", "A4209", "A4299_1"}

# =============================================================================
# U-4.12: 뇌/심혈관 진단비 슬롯 정의 (stub)
# =============================================================================

CEREBRO_CARDIOVASCULAR_SLOTS = [
    {
        "slot_key": "diagnosis_lump_sum_amount",
        "label": "진단비 지급금액(일시금)",
        "comparable": True,
        "source_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
        "extractor": "diagnosis_lump_sum",
    },
    {
        "slot_key": "existence_status",
        "label": "담보 존재 여부",
        "comparable": True,
        "source_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
    },
    {
        "slot_key": "waiting_period",
        "label": "대기기간",
        "comparable": False,
        "source_doc_types": ["약관"],
    },
]

# =============================================================================
# U-4.12: 수술비 슬롯 정의 (stub)
# =============================================================================

SURGERY_BENEFIT_SLOTS = [
    {
        "slot_key": "surgery_amount",
        "label": "수술비 지급금액",
        "comparable": True,
        "source_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
        "extractor": "surgery_amount",  # stub
    },
    {
        "slot_key": "surgery_count_limit",
        "label": "수술 횟수 제한",
        "comparable": True,
        "source_doc_types": ["상품요약서", "사업방법서"],
        "extractor": "count_limit",  # stub
    },
    {
        "slot_key": "existence_status",
        "label": "담보 존재 여부",
        "comparable": True,
        "source_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
    },
]

# Coverage Type별 슬롯 정의 레지스트리
SLOT_DEFINITIONS_BY_COVERAGE_TYPE = {
    "cancer_diagnosis": CANCER_DIAGNOSIS_SLOTS,
    "cerebro_cardiovascular_diagnosis": CEREBRO_CARDIOVASCULAR_SLOTS,
    "surgery_benefit": SURGERY_BENEFIT_SLOTS,
}

# Coverage code → Coverage type 매핑
# coverage_standard 기준 정확한 매핑 (U-4.14)
COVERAGE_CODE_TO_TYPE = {
    # 암진단비
    "A4200_1": "cancer_diagnosis",
    "A4210": "cancer_diagnosis",
    "A4209": "cancer_diagnosis",
    "A4299_1": "cancer_diagnosis",
    # 뇌/심혈관 진단비 (U-4.14 수정: A41xx 계열)
    "A4101": "cerebro_cardiovascular_diagnosis",  # 뇌혈관질환진단비
    "A4102": "cerebro_cardiovascular_diagnosis",  # 뇌출혈진단비
    "A4103": "cerebro_cardiovascular_diagnosis",  # 뇌졸중진단비
    "A4104_1": "cerebro_cardiovascular_diagnosis",  # 심장질환진단비
    "A4105": "cerebro_cardiovascular_diagnosis",  # 허혈성심장질환진단비
    # 수술비 (U-4.14 수정: A5xxx 계열)
    "A5100": "surgery_benefit",  # 질병수술비
    "A5104_1": "surgery_benefit",  # 뇌혈관질환수술비
    "A5107_1": "surgery_benefit",  # 허혈성심장질환수술비
    "A5200": "surgery_benefit",  # 암수술비(유사암제외)
    "A5298_001": "surgery_benefit",  # 유사암수술비
    "A5300": "surgery_benefit",  # 상해수술비
}

# Default YAML path
DEFAULT_SLOT_DEFINITIONS_YAML = "config/slot_definitions.yaml"


def load_slot_definitions_from_yaml(yaml_path: str | None = None) -> dict | None:
    """
    YAML에서 슬롯 정의 로드 (U-4.12: 외부화)

    Returns:
        YAML 데이터 dict 또는 None (파일 없거나 파싱 실패 시)
    """
    if yaml_path is None:
        yaml_path = DEFAULT_SLOT_DEFINITIONS_YAML

    path = Path(yaml_path)
    if not path.exists():
        # 프로젝트 루트 기준으로 시도
        project_root = Path(__file__).parent.parent.parent
        path = project_root / yaml_path

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except yaml.YAMLError:
            return None
    return None


def get_slots_for_coverage_type(coverage_type: str, yaml_path: str | None = None) -> list[dict]:
    """
    Coverage type에 해당하는 슬롯 정의 반환

    우선순위:
      1. YAML 파일 (있으면)
      2. 코드 내 하드코딩 (fallback)
    """
    # YAML 시도
    yaml_data = load_slot_definitions_from_yaml(yaml_path)
    if yaml_data and "coverage_types" in yaml_data:
        ct_data = yaml_data["coverage_types"].get(coverage_type)
        if ct_data and "slots" in ct_data:
            return ct_data["slots"]

    # Fallback: 코드 내 정의
    return SLOT_DEFINITIONS_BY_COVERAGE_TYPE.get(coverage_type, CANCER_DIAGNOSIS_SLOTS)


def load_slot_definitions(yaml_path: str | None = None) -> list[dict]:
    """슬롯 정의 로드 (YAML 또는 기본값) - 하위 호환성 유지"""
    yaml_data = load_slot_definitions_from_yaml(yaml_path)
    if yaml_data and "coverage_types" in yaml_data:
        # 첫 번째 coverage_type의 slots 반환 (하위 호환성)
        for ct_data in yaml_data["coverage_types"].values():
            if "slots" in ct_data:
                return ct_data["slots"]
    return CANCER_DIAGNOSIS_SLOTS


# =============================================================================
# Slot Extraction Functions
# =============================================================================

def extract_diagnosis_lump_sum_slot(evidence_list: list, insurer_code: str) -> SlotInsurerValue:
    """
    진단비 지급금액(일시금) 슬롯 추출 (범용화된 추출기)

    진단비 일시금만 추출 (일당/특약 금액 제외)
    우선순위:
      1. doc_type: 상품요약서 > 사업방법서 > 가입설계서
      2. confidence: high > medium (within same doc_type)

    Note: compare_axis evidence doesn't have pre-populated amount field.
    We call extract_diagnosis_lump_sum() directly on each evidence preview.

    This extractor can be used for any coverage type that requires lump-sum diagnosis amount.
    """
    doc_type_priority = {"상품요약서": 3, "사업방법서": 2, "가입설계서": 1}
    confidence_priority = {"high": 2, "medium": 1, "low": 0, "not_found": -1}
    trace = LLMTrace.from_llm_flag()  # Track LLM usage based on flag

    best_amount = None
    best_doc_priority = 0
    best_conf_priority = -1
    best_refs = []
    found_daily_only = False  # 일당/특약 금액만 발견했는지 추적

    for ev in evidence_list:
        # A2 정책: 약관 제외
        if ev.doc_type == "약관":
            continue

        doc_priority = doc_type_priority.get(ev.doc_type, 0)

        # Skip if doc_type priority is lower
        if doc_priority < best_doc_priority:
            continue

        # Get preview text
        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        # U-4.10: Extract diagnosis lump-sum amount only
        lump_sum_result = extract_diagnosis_lump_sum(preview, doc_type=ev.doc_type)

        if lump_sum_result.amount_text and lump_sum_result.confidence not in ("low", "not_found"):
            conf_priority = confidence_priority.get(lump_sum_result.confidence, 0)

            # Update if: higher doc_type OR same doc_type with higher confidence
            if doc_priority > best_doc_priority or (doc_priority == best_doc_priority and conf_priority > best_conf_priority):
                best_amount = lump_sum_result.amount_text
                best_doc_priority = doc_priority
                best_conf_priority = conf_priority
                best_refs = [SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )]
        elif lump_sum_result.reason and "일당/특약" in lump_sum_result.reason:
            # 일당/특약 금액만 발견됨
            found_daily_only = True

    if best_amount:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=best_amount,
            confidence="high" if best_doc_priority >= 2 else "medium",
            evidence_refs=best_refs,
            trace=trace,
        )

    # U-4.10: 일당/특약 금액만 발견된 경우 명확한 사유 제공
    if found_daily_only:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=None,
            confidence="not_found",
            reason="진단비 일시금 금액 미확인 (일당/특약 금액만 존재)",
            trace=trace,
        )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value=None,
        confidence="not_found",
        reason="가입설계서/상품요약서/사업방법서에서 진단비 일시금 미확인",
        trace=trace,
    )


# 하위 호환성을 위한 alias (deprecated, 향후 제거 예정)
extract_payout_amount = extract_diagnosis_lump_sum_slot


# =============================================================================
# U-4.13: Surgery Benefit Slot Extractors
# =============================================================================

def extract_surgery_amount_slot(evidence_list: list, insurer_code: str) -> SlotInsurerValue:
    """
    수술비 지급금액 슬롯 추출 (U-4.13)

    수술비 일시금 추출 (진단비와 구별)
    우선순위:
      1. doc_type: 상품요약서 > 사업방법서 > 가입설계서
      2. confidence: high > medium (within same doc_type)
    """
    doc_type_priority = {"상품요약서": 3, "사업방법서": 2, "가입설계서": 1}
    confidence_priority = {"high": 2, "medium": 1, "low": 0, "not_found": -1}
    trace = LLMTrace.from_llm_flag()

    best_amount = None
    best_doc_priority = 0
    best_conf_priority = -1
    best_refs = []

    for ev in evidence_list:
        # A2 정책: 약관 제외
        if ev.doc_type == "약관":
            continue

        doc_priority = doc_type_priority.get(ev.doc_type, 0)

        # Skip if doc_type priority is lower
        if doc_priority < best_doc_priority:
            continue

        # Get preview text
        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        # Extract surgery amount
        surgery_result = extract_surgery_amount(preview, doc_type=ev.doc_type)

        if surgery_result.amount_text and surgery_result.confidence not in ("low", "not_found"):
            conf_priority = confidence_priority.get(surgery_result.confidence, 0)

            # Update if: higher doc_type OR same doc_type with higher confidence
            if doc_priority > best_doc_priority or (doc_priority == best_doc_priority and conf_priority > best_conf_priority):
                best_amount = surgery_result.amount_text
                best_doc_priority = doc_priority
                best_conf_priority = conf_priority
                best_refs = [SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )]

    if best_amount:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=best_amount,
            confidence="high" if best_doc_priority >= 2 else "medium",
            evidence_refs=best_refs,
            trace=trace,
        )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value=None,
        confidence="not_found",
        reason="가입설계서/상품요약서/사업방법서에서 수술비 금액 미확인",
        trace=trace,
    )


def extract_surgery_count_limit_slot(evidence_list: list, insurer_code: str) -> SlotInsurerValue:
    """
    수술 횟수 제한 슬롯 추출 (U-4.13)

    수술 횟수 제한 정보 추출 (연 N회, 통산 N회 등)
    """
    doc_type_priority = {"상품요약서": 3, "사업방법서": 2, "가입설계서": 1}
    trace = LLMTrace.from_llm_flag()

    best_count = None
    best_doc_priority = 0
    best_refs = []

    for ev in evidence_list:
        # A2 정책: 약관 제외
        if ev.doc_type == "약관":
            continue

        doc_priority = doc_type_priority.get(ev.doc_type, 0)

        # Skip if doc_type priority is lower
        if doc_priority < best_doc_priority:
            continue

        # Get preview text
        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        # Extract surgery count limit
        count_result = extract_surgery_count_limit(preview)

        if count_result.count_text and count_result.confidence not in ("low", "not_found"):
            if doc_priority > best_doc_priority:
                best_count = count_result.count_text
                best_doc_priority = doc_priority
                best_refs = [SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )]

    if best_count:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=best_count,
            confidence="medium",
            evidence_refs=best_refs,
            trace=trace,
        )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value=None,
        confidence="not_found",
        reason="수술 횟수 제한 정보 미확인",
        trace=trace,
    )


def extract_existence_status(evidence_list: list, insurer_code: str) -> SlotInsurerValue:
    """
    담보 존재 여부 슬롯 추출

    found: 1개 이상 evidence 존재
    not_found: evidence 없음
    """
    trace = LLMTrace.rule_only(reason="not_needed")  # Existence check is always rule-based
    compare_evidence = [
        ev for ev in evidence_list
        if ev.doc_type in ("가입설계서", "상품요약서", "사업방법서")
    ]

    if compare_evidence:
        refs = [
            SlotEvidenceRef(
                document_id=ev.document_id,
                page_start=ev.page_start,
                chunk_id=getattr(ev, 'chunk_id', None),
            )
            for ev in compare_evidence[:3]  # 최대 3개
        ]
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value="있음",
            confidence="high",
            evidence_refs=refs,
            trace=trace,
        )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value="없음",
        confidence="not_found",
        reason="가입설계서/상품요약서/사업방법서에서 해당 담보 미발견",
        trace=trace,
    )


def extract_payout_condition_summary(
    evidence_list: list,
    insurer_code: str,
    coverage_type: str = "cancer",
) -> SlotInsurerValue:
    """
    지급조건 요약 슬롯 추출

    condition_snippet이 있으면 사용, 없으면 preview에서 추출.
    암진단비의 경우, 암 관련 키워드가 포함된 evidence를 우선 선택.
    """
    doc_type_priority = {"상품요약서": 3, "사업방법서": 2, "가입설계서": 1}
    trace = LLMTrace.from_llm_flag()  # Track LLM usage based on flag

    # Compare evidence only (exclude 약관)
    compare_evidence = [
        ev for ev in evidence_list
        if ev.doc_type in ("가입설계서", "상품요약서", "사업방법서")
    ]

    # Track which doc types were searched for placeholder
    searched_doc_types = set(ev.doc_type for ev in compare_evidence)

    best_snippet = None
    best_priority = 0
    best_refs = []

    # Pass 1: 암 관련 키워드가 포함된 evidence에서 추출 (cancer-specific)
    cancer_keywords = ["암", "유사암", "악성신생물", "갑상선암", "기타피부암", "경계성종양", "제자리암"]

    for ev in compare_evidence:
        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        # Check if evidence contains cancer-related keywords
        has_cancer_keyword = any(kw in preview for kw in cancer_keywords)
        if not has_cancer_keyword:
            continue

        priority = doc_type_priority.get(ev.doc_type, 0)

        # condition_snippet 우선
        if hasattr(ev, 'condition_snippet') and ev.condition_snippet and ev.condition_snippet.snippet:
            snippet = ev.condition_snippet.snippet
            # Verify snippet is cancer-related
            if any(kw in snippet for kw in cancer_keywords):
                if priority > best_priority:
                    best_snippet = snippet[:200]
                    best_priority = priority
                    best_refs = [SlotEvidenceRef(
                        document_id=ev.document_id,
                        page_start=ev.page_start,
                        chunk_id=getattr(ev, 'chunk_id', None),
                    )]
        # fallback: preview에서 조건 관련 문장 추출
        elif priority > best_priority:
            condition_match = _extract_condition_from_preview(ev.preview, cancer_specific=True)
            if condition_match:
                best_snippet = condition_match[:200]
                best_priority = priority
                best_refs = [SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )]

    # Pass 2: cancer-specific에서 못 찾으면, 일반 조건 키워드로 fallback
    if not best_snippet:
        for ev in compare_evidence:
            preview = getattr(ev, 'preview', '') or ''
            if not preview:
                continue

            priority = doc_type_priority.get(ev.doc_type, 0)
            if priority <= best_priority:
                continue

            # condition_snippet 우선
            if hasattr(ev, 'condition_snippet') and ev.condition_snippet and ev.condition_snippet.snippet:
                best_snippet = ev.condition_snippet.snippet[:200]
                best_priority = priority
                best_refs = [SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )]
            # fallback: preview에서 조건 관련 문장 추출
            elif hasattr(ev, 'preview') and ev.preview:
                condition_match = _extract_condition_from_preview(ev.preview, cancer_specific=False)
                if condition_match:
                    best_snippet = condition_match[:200]
                    best_priority = priority
                    best_refs = [SlotEvidenceRef(
                        document_id=ev.document_id,
                        page_start=ev.page_start,
                        chunk_id=getattr(ev, 'chunk_id', None),
                    )]

    if best_snippet:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=best_snippet,
            confidence="medium",
            evidence_refs=best_refs,
            trace=trace,
        )

    # Deterministic placeholder when no candidate found
    searched_docs_str = "/".join(sorted(searched_doc_types)) if searched_doc_types else "없음"
    placeholder = f"조건 정보 미검출 (검색: {searched_docs_str})"

    # If we have evidence but couldn't extract condition, still provide refs
    if compare_evidence:
        best_ev = max(compare_evidence, key=lambda e: doc_type_priority.get(e.doc_type, 0))
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=placeholder,
            confidence="low",
            reason="지급조건 정보 미확인",
            evidence_refs=[SlotEvidenceRef(
                document_id=best_ev.document_id,
                page_start=best_ev.page_start,
                chunk_id=getattr(best_ev, 'chunk_id', None),
            )],
            trace=trace,
        )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value=placeholder,
        confidence="not_found",
        reason="가입설계서/상품요약서/사업방법서 증거 없음",
        trace=trace,
    )


def _extract_condition_from_preview(preview: str, cancer_specific: bool = False) -> str | None:
    """
    preview 텍스트에서 지급조건 관련 문장 추출

    Args:
        preview: 검색할 텍스트
        cancer_specific: True면 암 관련 키워드 + 조건 키워드 조합으로 검색
    """
    # 암 특정 조건 키워드 (암 관련 문맥에서만 사용)
    cancer_condition_keywords = [
        "암(유사암 제외)으로 진단",
        "암으로 진단 확정",
        "암보장개시일 이후",
        "유사암으로 진단",
        "암 진단 확정",
        "(유사암 제외)",
        "(유사암제외)",
    ]

    # 일반 조건 키워드
    general_keywords = ["진단 확정", "최초 진단", "보험기간 중", "진단확정"]

    # Pass 1: cancer-specific 키워드 우선 (if requested)
    if cancer_specific:
        for keyword in cancer_condition_keywords:
            if keyword in preview:
                idx = preview.find(keyword)
                start = max(0, idx - 30)
                end = min(len(preview), idx + len(keyword) + 150)
                return preview[start:end].strip()

    # Pass 2: 일반 조건 키워드
    for keyword in general_keywords:
        if keyword in preview:
            # 키워드 포함 문장 추출 (앞뒤)
            idx = preview.find(keyword)
            start = max(0, idx - 30)
            end = min(len(preview), idx + len(keyword) + 100)
            snippet = preview[start:end].strip()

            # cancer_specific 모드에서는 암 관련 컨텐츠인지 확인
            if cancer_specific:
                cancer_terms = ["암", "유사암"]
                if any(term in snippet for term in cancer_terms):
                    return snippet
            else:
                return snippet

    return None


def extract_diagnosis_scope(policy_evidence: list, insurer_code: str) -> SlotInsurerValue:
    """
    진단 범위 정의 슬롯 추출 (약관에서)

    A2 정책: 이 슬롯은 비교 계산에 사용하지 않음
    """
    trace = LLMTrace.rule_only(reason="not_needed")  # Definition lookup is rule-based
    policy_only = [ev for ev in policy_evidence if ev.doc_type == "약관"]

    if policy_only:
        # 암 정의 관련 키워드 검색
        for ev in policy_only:
            preview = getattr(ev, 'preview', '') or ''
            if any(kw in preview for kw in ["암의 정의", "악성신생물", "유사암", "경계성종양"]):
                return SlotInsurerValue(
                    insurer_code=insurer_code,
                    value=preview[:300],
                    confidence="medium",
                    evidence_refs=[SlotEvidenceRef(
                        document_id=ev.document_id,
                        page_start=ev.page_start,
                        chunk_id=getattr(ev, 'chunk_id', None),
                    )],
                    trace=trace,
                )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value=None,
        confidence="not_found",
        reason="약관에서 진단 범위 정의 미확인",
        trace=trace,
    )


def extract_waiting_period(policy_evidence: list, insurer_code: str) -> SlotInsurerValue:
    """
    대기기간 슬롯 추출 (약관에서)

    A2 정책: 이 슬롯은 비교 계산에 사용하지 않음
    """
    trace = LLMTrace.rule_only(reason="not_needed")  # Pattern matching is rule-based
    policy_only = [ev for ev in policy_evidence if ev.doc_type == "약관"]

    for ev in policy_only:
        preview = getattr(ev, 'preview', '') or ''
        # 대기기간 패턴 매칭
        match = re.search(r'(\d+)\s*(일|개월)\s*(면책|대기)', preview)
        if match:
            period = f"{match.group(1)}{match.group(2)}"
            return SlotInsurerValue(
                insurer_code=insurer_code,
                value=period,
                confidence="high",
                evidence_refs=[SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )],
                trace=trace,
            )

        # 암보장개시일 키워드
        if "암보장개시일" in preview:
            return SlotInsurerValue(
                insurer_code=insurer_code,
                value="암보장개시일 적용",
                confidence="medium",
                evidence_refs=[SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )],
                trace=trace,
            )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value=None,
        confidence="not_found",
        reason="약관에서 대기기간 정보 미확인",
        trace=trace,
    )


# =============================================================================
# Main Extraction Function
# =============================================================================

# Coverage type별 coverage_codes 매핑 (U-4.14 수정: 신정원 표준코드 반영)
CEREBRO_CARDIOVASCULAR_CODES = {"A4101", "A4102", "A4103", "A4104_1", "A4105"}
SURGERY_BENEFIT_CODES = {"A5100", "A5104_1", "A5107_1", "A5200", "A5298_001", "A5300", "A9630_1"}


def _determine_coverage_type(coverage_codes: list[str] | None) -> str | None:
    """coverage_codes에서 coverage_type 결정"""
    if not coverage_codes:
        return None

    code_set = set(coverage_codes)

    if code_set & CANCER_COVERAGE_CODES:
        return "cancer_diagnosis"
    if code_set & CEREBRO_CARDIOVASCULAR_CODES:
        return "cerebro_cardiovascular_diagnosis"
    if code_set & SURGERY_BENEFIT_CODES:
        return "surgery_benefit"

    return None


def extract_slots(
    insurers: list[str],
    compare_axis: list,
    policy_axis: list,
    coverage_codes: list[str] | None = None,
    query: str = "",  # U-4.16: 쿼리 전달하여 조건부 슬롯 추출
) -> list[ComparisonSlot]:
    """
    슬롯 추출 메인 함수 (U-4.13: 다중 coverage_type 지원, U-4.16: 조건부 슬롯)

    Args:
        insurers: 보험사 코드 리스트
        compare_axis: compare_axis 결과 (가입설계서/상품요약서/사업방법서)
        policy_axis: policy_axis 결과 (약관)
        coverage_codes: 필터할 coverage_codes
        query: 원본 쿼리 (조건부 슬롯 추출용)

    Returns:
        추출된 슬롯 리스트
    """
    coverage_type = _determine_coverage_type(coverage_codes)

    if coverage_type is None:
        return []

    # 보험사별 evidence 그룹화
    compare_by_insurer: dict[str, list] = {ic: [] for ic in insurers}
    policy_by_insurer: dict[str, list] = {ic: [] for ic in insurers}

    for item in compare_axis:
        if item.insurer_code in compare_by_insurer:
            compare_by_insurer[item.insurer_code].extend(item.evidence)

    for item in policy_axis:
        if item.insurer_code in policy_by_insurer:
            policy_by_insurer[item.insurer_code].extend(item.evidence)

    # Coverage type별 슬롯 추출
    if coverage_type == "surgery_benefit":
        return _extract_surgery_benefit_slots(insurers, compare_by_insurer, policy_by_insurer, query)
    elif coverage_type == "cerebro_cardiovascular_diagnosis":
        return _extract_cerebro_cardiovascular_slots(insurers, compare_by_insurer, policy_by_insurer)
    else:  # cancer_diagnosis (기본)
        return _extract_cancer_diagnosis_slots(insurers, compare_by_insurer, policy_by_insurer, query)


def _extract_cancer_diagnosis_slots(
    insurers: list[str],
    compare_by_insurer: dict[str, list],
    policy_by_insurer: dict[str, list],
    query: str = "",
) -> list[ComparisonSlot]:
    """암진단비 슬롯 추출 (U-4.16: subtype 슬롯 추가)"""
    slots = []

    # 1. diagnosis_lump_sum_amount (범용화: 진단비 일시금 전용)
    lump_sum_slot = ComparisonSlot(
        slot_key="payout_amount",  # 하위 호환성 유지
        label="진단비 지급금액(일시금)",
        comparable=True,
        insurers=[
            extract_diagnosis_lump_sum_slot(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    lump_sum_slot.diff_summary = _generate_slot_diff_summary(lump_sum_slot)
    slots.append(lump_sum_slot)

    # 2. existence_status
    existence_slot = ComparisonSlot(
        slot_key="existence_status",
        label="담보 존재 여부",
        comparable=True,
        insurers=[
            extract_existence_status(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    existence_slot.diff_summary = _generate_slot_diff_summary(existence_slot)
    slots.append(existence_slot)

    # 3. payout_condition_summary
    condition_slot = ComparisonSlot(
        slot_key="payout_condition_summary",
        label="지급조건 요약",
        comparable=True,
        insurers=[
            extract_payout_condition_summary(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    condition_slot.diff_summary = _generate_slot_diff_summary(condition_slot)
    slots.append(condition_slot)

    # 4. diagnosis_scope_definition (약관 - comparable=False)
    diagnosis_slot = ComparisonSlot(
        slot_key="diagnosis_scope_definition",
        label="진단 범위 정의",
        comparable=False,
        insurers=[
            extract_diagnosis_scope(policy_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    slots.append(diagnosis_slot)

    # 5. waiting_period (약관 - comparable=False)
    waiting_slot = ComparisonSlot(
        slot_key="waiting_period",
        label="대기기간",
        comparable=False,
        insurers=[
            extract_waiting_period(policy_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    slots.append(waiting_slot)

    # U-4.16: 경계성종양/제자리암/유사암 관련 쿼리인 경우 subtype 슬롯 추출
    subtype_keywords = ["제자리암", "상피내암", "경계성종양", "경계성 종양", "유사암"]
    query_lower = query.lower()
    if any(kw in query_lower for kw in subtype_keywords):
        # 모든 evidence 합쳐서 검색 (compare + policy)
        all_evidence_by_insurer = {
            ic: compare_by_insurer.get(ic, []) + policy_by_insurer.get(ic, [])
            for ic in insurers
        }

        # 6. subtype_in_situ_covered (제자리암 보장 여부)
        in_situ_slot = ComparisonSlot(
            slot_key="subtype_in_situ_covered",
            label="제자리암 보장 여부",
            comparable=True,
            insurers=[
                extract_subtype_coverage_slot(all_evidence_by_insurer.get(ic, []), ic, "in_situ", query)
                for ic in insurers
            ],
        )
        in_situ_slot.diff_summary = _generate_slot_diff_summary(in_situ_slot)
        slots.append(in_situ_slot)

        # 7. subtype_borderline_covered (경계성종양 보장 여부)
        borderline_slot = ComparisonSlot(
            slot_key="subtype_borderline_covered",
            label="경계성종양 보장 여부",
            comparable=True,
            insurers=[
                extract_subtype_coverage_slot(all_evidence_by_insurer.get(ic, []), ic, "borderline", query)
                for ic in insurers
            ],
        )
        borderline_slot.diff_summary = _generate_slot_diff_summary(borderline_slot)
        slots.append(borderline_slot)

        # 8. subtype_similar_cancer_covered (유사암 보장 여부)
        similar_slot = ComparisonSlot(
            slot_key="subtype_similar_cancer_covered",
            label="유사암 보장 여부",
            comparable=True,
            insurers=[
                extract_subtype_coverage_slot(all_evidence_by_insurer.get(ic, []), ic, "similar_cancer", query)
                for ic in insurers
            ],
        )
        similar_slot.diff_summary = _generate_slot_diff_summary(similar_slot)
        slots.append(similar_slot)

        # 9. subtype_definition_excerpt (정의/조건 발췌)
        definition_slot = ComparisonSlot(
            slot_key="subtype_definition_excerpt",
            label="암 유형 정의/조건 발췌",
            comparable=False,
            insurers=[
                extract_subtype_definition_slot(all_evidence_by_insurer.get(ic, []), ic, query)
                for ic in insurers
            ],
        )
        slots.append(definition_slot)

    return slots


def _extract_cerebro_cardiovascular_slots(
    insurers: list[str],
    compare_by_insurer: dict[str, list],
    policy_by_insurer: dict[str, list],
) -> list[ComparisonSlot]:
    """뇌/심혈관 진단비 슬롯 추출 (U-4.13)"""
    slots = []

    # 1. diagnosis_lump_sum_amount (진단비 일시금 - 암진단비와 동일 추출기 사용)
    lump_sum_slot = ComparisonSlot(
        slot_key="diagnosis_lump_sum_amount",
        label="진단비 지급금액(일시금)",
        comparable=True,
        insurers=[
            extract_diagnosis_lump_sum_slot(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    lump_sum_slot.diff_summary = _generate_slot_diff_summary(lump_sum_slot)
    slots.append(lump_sum_slot)

    # 2. existence_status
    existence_slot = ComparisonSlot(
        slot_key="existence_status",
        label="담보 존재 여부",
        comparable=True,
        insurers=[
            extract_existence_status(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    existence_slot.diff_summary = _generate_slot_diff_summary(existence_slot)
    slots.append(existence_slot)

    # 3. waiting_period (약관 - comparable=False)
    waiting_slot = ComparisonSlot(
        slot_key="waiting_period",
        label="대기기간",
        comparable=False,
        insurers=[
            extract_waiting_period(policy_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    slots.append(waiting_slot)

    return slots


def _extract_surgery_benefit_slots(
    insurers: list[str],
    compare_by_insurer: dict[str, list],
    policy_by_insurer: dict[str, list],
    query: str = "",
) -> list[ComparisonSlot]:
    """수술비 슬롯 추출 (U-4.13 + U-4.16)"""
    slots = []

    # 1. surgery_amount (수술비 지급금액)
    surgery_amount_slot = ComparisonSlot(
        slot_key="surgery_amount",
        label="수술비 지급금액",
        comparable=True,
        insurers=[
            extract_surgery_amount_slot(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    surgery_amount_slot.diff_summary = _generate_slot_diff_summary(surgery_amount_slot)
    slots.append(surgery_amount_slot)

    # 2. surgery_count_limit (수술 횟수 제한)
    count_limit_slot = ComparisonSlot(
        slot_key="surgery_count_limit",
        label="수술 횟수 제한",
        comparable=True,
        insurers=[
            extract_surgery_count_limit_slot(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    count_limit_slot.diff_summary = _generate_slot_diff_summary(count_limit_slot)
    slots.append(count_limit_slot)

    # 3. existence_status
    existence_slot = ComparisonSlot(
        slot_key="existence_status",
        label="담보 존재 여부",
        comparable=True,
        insurers=[
            extract_existence_status(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    existence_slot.diff_summary = _generate_slot_diff_summary(existence_slot)
    slots.append(existence_slot)

    # U-4.16: 다빈치/로봇 수술 관련 쿼리인 경우 추가 슬롯 추출
    query_lower = query.lower()
    if any(kw in query_lower for kw in ["다빈치", "로봇", "da vinci", "robot"]):
        # 4. surgery_method (수술 방식)
        # 모든 evidence 합쳐서 검색 (compare + policy)
        all_evidence_by_insurer = {
            ic: compare_by_insurer.get(ic, []) + policy_by_insurer.get(ic, [])
            for ic in insurers
        }
        surgery_method_slot = ComparisonSlot(
            slot_key="surgery_method",
            label="수술 방식",
            comparable=True,
            insurers=[
                extract_surgery_method_slot(all_evidence_by_insurer.get(ic, []), ic, query)
                for ic in insurers
            ],
        )
        surgery_method_slot.diff_summary = _generate_slot_diff_summary(surgery_method_slot)
        slots.append(surgery_method_slot)

        # 5. method_condition (수술방식 적용조건)
        method_condition_slot = ComparisonSlot(
            slot_key="method_condition",
            label="수술방식 적용조건",
            comparable=False,
            insurers=[
                extract_method_condition_slot(all_evidence_by_insurer.get(ic, []), ic, query)
                for ic in insurers
            ],
        )
        slots.append(method_condition_slot)

    return slots


# =============================================================================
# U-4.16: 다빈치/로봇 수술 슬롯 추출
# =============================================================================

# 다빈치/로봇 수술 키워드
SURGERY_METHOD_KEYWORDS = [
    "다빈치",
    "da vinci",
    "davinci",
    "로봇수술",
    "로봇 수술",
    "robot",
    "복강경",
]


def extract_surgery_method_slot(evidence_list: list, insurer_code: str, query: str = "") -> SlotInsurerValue:
    """
    수술 방식 슬롯 추출 (U-4.16)

    다빈치/로봇수술 키워드를 탐지하여 수술 방식 반환
    값: 다빈치, 로봇수술, 로봇수술(다빈치 포함), 해당없음, Unknown
    """
    doc_type_priority = {"상품요약서": 3, "사업방법서": 2, "가입설계서": 1}
    trace = LLMTrace.rule_only(reason="not_needed")

    best_method = None
    best_doc_priority = 0
    best_refs = []
    found_davinci = False
    found_robot = False

    for ev in evidence_list:
        # A2 정책: 약관 제외 안함 (정의 확인 필요)
        doc_priority = doc_type_priority.get(ev.doc_type, 0)

        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        preview_lower = preview.lower()

        # 다빈치 키워드 탐지
        if any(kw in preview_lower for kw in ["다빈치", "da vinci", "davinci"]):
            found_davinci = True
            if doc_priority >= best_doc_priority:
                best_method = "다빈치"
                best_doc_priority = doc_priority
                best_refs = [SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )]

        # 로봇수술 키워드 탐지
        elif any(kw in preview_lower for kw in ["로봇수술", "로봇 수술", "robot"]):
            found_robot = True
            if doc_priority >= best_doc_priority and not found_davinci:
                best_method = "로봇수술"
                best_doc_priority = doc_priority
                best_refs = [SlotEvidenceRef(
                    document_id=ev.document_id,
                    page_start=ev.page_start,
                    chunk_id=getattr(ev, 'chunk_id', None),
                )]

    # 결과 반환
    if found_davinci and found_robot:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value="로봇수술(다빈치 포함)",
            confidence="high",
            evidence_refs=best_refs,
            trace=trace,
        )
    elif best_method:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=best_method,
            confidence="high" if best_doc_priority >= 2 else "medium",
            evidence_refs=best_refs,
            trace=trace,
        )

    # 쿼리에 다빈치/로봇이 있는데 못 찾은 경우
    query_lower = query.lower()
    if any(kw in query_lower for kw in ["다빈치", "로봇"]):
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value="Unknown",
            confidence="not_found",
            reason="해당 보험사 문서에서 다빈치/로봇수술 관련 정보 미확인",
            trace=trace,
        )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value="해당없음",
        confidence="low",
        reason="다빈치/로봇수술 관련 정보 미확인",
        trace=trace,
    )


def extract_method_condition_slot(evidence_list: list, insurer_code: str, query: str = "") -> SlotInsurerValue:
    """
    수술방식 적용조건 슬롯 추출 (U-4.16)

    다빈치/로봇수술 키워드 주변에서 조건 문구 추출
    """
    doc_type_priority = {"상품요약서": 3, "사업방법서": 2, "가입설계서": 1, "약관": 1}
    trace = LLMTrace.rule_only(reason="not_needed")

    best_condition = None
    best_doc_priority = 0
    best_refs = []

    surgery_keywords = ["다빈치", "da vinci", "davinci", "로봇수술", "로봇 수술"]
    condition_patterns = [
        r'(다빈치|로봇수술|로봇\s*수술)[^。.]*?(시|경우|때)[^。.]{0,100}',
        r'[^。.]{0,50}(다빈치|로봇수술|로봇\s*수술)[^。.]{0,100}',
    ]

    for ev in evidence_list:
        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        preview_lower = preview.lower()

        # 수술 키워드 포함 여부 확인
        if not any(kw in preview_lower for kw in surgery_keywords):
            continue

        doc_priority = doc_type_priority.get(ev.doc_type, 0)
        if doc_priority < best_doc_priority:
            continue

        # 조건 문구 추출 시도
        for pattern in condition_patterns:
            match = re.search(pattern, preview, re.IGNORECASE)
            if match:
                condition_text = match.group(0).strip()
                # 너무 짧거나 긴 경우 필터링
                if 10 <= len(condition_text) <= 200:
                    if doc_priority >= best_doc_priority:
                        best_condition = condition_text
                        best_doc_priority = doc_priority
                        best_refs = [SlotEvidenceRef(
                            document_id=ev.document_id,
                            page_start=ev.page_start,
                            chunk_id=getattr(ev, 'chunk_id', None),
                        )]
                    break

        # 패턴 매칭 실패 시 키워드 주변 텍스트 추출
        if not best_condition and doc_priority >= best_doc_priority:
            for kw in surgery_keywords:
                if kw in preview_lower:
                    idx = preview_lower.find(kw)
                    start = max(0, idx - 30)
                    end = min(len(preview), idx + len(kw) + 100)
                    snippet = preview[start:end].strip()
                    if len(snippet) >= 20:
                        best_condition = snippet
                        best_doc_priority = doc_priority
                        best_refs = [SlotEvidenceRef(
                            document_id=ev.document_id,
                            page_start=ev.page_start,
                            chunk_id=getattr(ev, 'chunk_id', None),
                        )]
                    break

    if best_condition:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=best_condition,
            confidence="medium",
            evidence_refs=best_refs,
            trace=trace,
        )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value=None,
        confidence="not_found",
        reason="수술방식 적용조건 정보 미확인",
        trace=trace,
    )


# =============================================================================
# U-4.16: 암 Subtype 보장 슬롯 추출 (경계성종양/제자리암)
# =============================================================================

# 암 subtype 키워드
CANCER_SUBTYPE_KEYWORDS = {
    "in_situ": ["제자리암", "상피내암", "carcinoma in situ"],
    "borderline": ["경계성종양", "경계성 종양", "borderline tumor"],
    "similar_cancer": ["유사암", "기타피부암", "갑상선암", "대장점막내암"],
}

# 보장 포함 키워드
COVERAGE_POSITIVE_KEYWORDS = ["보장", "지급", "보험금", "해당"]
# 보장 제외 키워드
COVERAGE_NEGATIVE_KEYWORDS = ["제외", "면책", "지급하지", "해당하지", "보장하지"]


def extract_subtype_coverage_slot(
    evidence_list: list,
    insurer_code: str,
    subtype: str,  # "in_situ", "borderline", "similar_cancer"
    query: str = ""
) -> SlotInsurerValue:
    """
    암 subtype 보장 여부 슬롯 추출 (U-4.16)

    제자리암/경계성종양/유사암의 보장 여부를 Y/N/Unknown으로 반환
    """
    doc_type_priority = {"상품요약서": 3, "사업방법서": 2, "가입설계서": 1, "약관": 1}
    trace = LLMTrace.rule_only(reason="not_needed")

    subtype_keywords = CANCER_SUBTYPE_KEYWORDS.get(subtype, [])
    if not subtype_keywords:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value="Unknown",
            confidence="not_found",
            reason=f"지원하지 않는 subtype: {subtype}",
            trace=trace,
        )

    best_result = None  # "Y", "N", or None
    best_confidence = 0  # higher is better
    best_refs = []
    found_subtype = False

    for ev in evidence_list:
        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        preview_lower = preview.lower()

        # Subtype 키워드 포함 여부 확인
        found_keyword = None
        for kw in subtype_keywords:
            if kw.lower() in preview_lower:
                found_keyword = kw
                found_subtype = True
                break

        if not found_keyword:
            continue

        doc_priority = doc_type_priority.get(ev.doc_type, 0)

        # 키워드 주변 텍스트 분석 (300자 윈도우)
        idx = preview_lower.find(found_keyword.lower())
        start = max(0, idx - 100)
        end = min(len(preview), idx + len(found_keyword) + 200)
        context = preview[start:end]

        # 포함/제외 키워드 탐지
        has_positive = any(pk in context for pk in COVERAGE_POSITIVE_KEYWORDS)
        has_negative = any(nk in context for nk in COVERAGE_NEGATIVE_KEYWORDS)

        # 판단
        if has_negative and not has_positive:
            result = "N"
            confidence = doc_priority + 1  # 제외 명시는 신뢰도 높음
        elif has_positive and not has_negative:
            result = "Y"
            confidence = doc_priority + 1
        elif has_positive and has_negative:
            # 둘 다 있으면 문맥 분석 필요 - 보수적으로 Unknown
            result = "Unknown"
            confidence = doc_priority
        else:
            # 키워드만 있고 포함/제외 판단 불가
            result = "Unknown"
            confidence = doc_priority - 1

        if confidence > best_confidence or (confidence == best_confidence and result != "Unknown"):
            best_result = result
            best_confidence = confidence
            best_refs = [SlotEvidenceRef(
                document_id=ev.document_id,
                page_start=ev.page_start,
                chunk_id=getattr(ev, 'chunk_id', None),
            )]

    if best_result:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=best_result,
            confidence="high" if best_result in ("Y", "N") and best_confidence >= 2 else "medium",
            evidence_refs=best_refs,
            trace=trace,
        )

    # Subtype 키워드를 아예 못 찾은 경우
    subtype_names = {"in_situ": "제자리암", "borderline": "경계성종양", "similar_cancer": "유사암"}
    return SlotInsurerValue(
        insurer_code=insurer_code,
        value="Unknown",
        confidence="not_found",
        reason=f"{subtype_names.get(subtype, subtype)} 관련 정보 미확인",
        trace=trace,
    )


def extract_subtype_definition_slot(evidence_list: list, insurer_code: str, query: str = "") -> SlotInsurerValue:
    """
    암 유형 정의/조건 발췌 슬롯 추출 (U-4.16)

    제자리암/경계성종양/유사암 관련 정의나 조건 문구 추출
    """
    doc_type_priority = {"약관": 3, "상품요약서": 2, "사업방법서": 2, "가입설계서": 1}
    trace = LLMTrace.rule_only(reason="not_needed")

    all_subtype_keywords = []
    for keywords in CANCER_SUBTYPE_KEYWORDS.values():
        all_subtype_keywords.extend(keywords)

    best_excerpt = None
    best_doc_priority = 0
    best_refs = []

    for ev in evidence_list:
        preview = getattr(ev, 'preview', '') or ''
        if not preview:
            continue

        preview_lower = preview.lower()

        # Subtype 키워드 포함 여부 확인
        found_keyword = None
        for kw in all_subtype_keywords:
            if kw.lower() in preview_lower:
                found_keyword = kw
                break

        if not found_keyword:
            continue

        doc_priority = doc_type_priority.get(ev.doc_type, 0)
        if doc_priority < best_doc_priority:
            continue

        # 키워드 주변 텍스트 추출 (정의 문구 포함)
        idx = preview_lower.find(found_keyword.lower())
        start = max(0, idx - 50)
        end = min(len(preview), idx + len(found_keyword) + 150)
        excerpt = preview[start:end].strip()

        if len(excerpt) >= 30 and doc_priority >= best_doc_priority:
            best_excerpt = excerpt
            best_doc_priority = doc_priority
            best_refs = [SlotEvidenceRef(
                document_id=ev.document_id,
                page_start=ev.page_start,
                chunk_id=getattr(ev, 'chunk_id', None),
            )]

    if best_excerpt:
        return SlotInsurerValue(
            insurer_code=insurer_code,
            value=best_excerpt[:200],  # 최대 200자
            confidence="medium",
            evidence_refs=best_refs,
            trace=trace,
        )

    return SlotInsurerValue(
        insurer_code=insurer_code,
        value=None,
        confidence="not_found",
        reason="암 유형 정의/조건 정보 미확인",
        trace=trace,
    )


def _generate_slot_diff_summary(slot: ComparisonSlot) -> str | None:
    """슬롯별 차이 요약 생성"""
    if not slot.comparable:
        return None

    values = []
    not_found_insurers = []

    for iv in slot.insurers:
        if iv.confidence == "not_found" or iv.value is None:
            not_found_insurers.append(iv.insurer_code)
        else:
            values.append((iv.insurer_code, iv.value))

    if not values:
        return "모든 보험사에서 정보 미확인"

    if not_found_insurers:
        found_str = ", ".join(f"{ic}: {v}" for ic, v in values)
        not_found_str = ", ".join(not_found_insurers)
        return f"{found_str}. {not_found_str}은(는) 미확인."

    if len(set(v for _, v in values)) == 1:
        return f"동일: {values[0][1]}"

    return ", ".join(f"{ic}: {v}" for ic, v in values)
