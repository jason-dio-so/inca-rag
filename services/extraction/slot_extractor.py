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
from .amount_extractor import extract_amount, extract_diagnosis_lump_sum


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

# 암진단비 슬롯 정의
CANCER_DIAGNOSIS_SLOTS = [
    {
        "slot_key": "payout_amount",
        "label": "진단비 지급금액(일시금)",  # U-4.10: 일시금 명시
        "comparable": True,
        "source_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
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


def load_slot_definitions(yaml_path: str | None = None) -> list[dict]:
    """슬롯 정의 로드 (YAML 또는 기본값)"""
    if yaml_path:
        path = Path(yaml_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("slots", CANCER_DIAGNOSIS_SLOTS)
    return CANCER_DIAGNOSIS_SLOTS


# =============================================================================
# Slot Extraction Functions
# =============================================================================

def extract_payout_amount(evidence_list: list, insurer_code: str) -> SlotInsurerValue:
    """
    진단비 지급금액(일시금) 슬롯 추출

    U-4.10: 진단비 일시금만 추출 (일당/특약 금액 제외)
    우선순위:
      1. doc_type: 상품요약서 > 사업방법서 > 가입설계서
      2. confidence: high > medium (within same doc_type)

    Note: compare_axis evidence doesn't have pre-populated amount field.
    We call extract_diagnosis_lump_sum() directly on each evidence preview.
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

def extract_slots(
    insurers: list[str],
    compare_axis: list,
    policy_axis: list,
    coverage_codes: list[str] | None = None,
) -> list[ComparisonSlot]:
    """
    슬롯 추출 메인 함수

    Args:
        insurers: 보험사 코드 리스트
        compare_axis: compare_axis 결과 (가입설계서/상품요약서/사업방법서)
        policy_axis: policy_axis 결과 (약관)
        coverage_codes: 필터할 coverage_codes

    Returns:
        추출된 슬롯 리스트
    """
    # 암진단비 관련 요청인지 확인
    target_codes = coverage_codes or []
    is_cancer_query = bool(set(target_codes) & CANCER_COVERAGE_CODES)

    if not is_cancer_query:
        # 암진단비가 아니면 빈 슬롯 반환
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

    slots = []

    # 1. payout_amount (U-4.10: 진단비 일시금만)
    payout_slot = ComparisonSlot(
        slot_key="payout_amount",
        label="진단비 지급금액(일시금)",
        comparable=True,
        insurers=[
            extract_payout_amount(compare_by_insurer.get(ic, []), ic)
            for ic in insurers
        ],
    )
    payout_slot.diff_summary = _generate_slot_diff_summary(payout_slot)
    slots.append(payout_slot)

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

    return slots


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
