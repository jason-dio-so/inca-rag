"""
Compare API Router

POST /compare - 2-Phase Retrieval 비교 검색
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.retrieval.compare_service import compare, CompareResponse
from services.extraction.subtype_extractor import (
    extract_subtypes_from_query,
    extract_subtype_comparison,
    is_multi_subtype_query,
    get_subtype_definition,
    SubtypeComparisonResult,
)
from api.config_loader import (
    get_coverage_domains,
    get_domain_keywords,
    get_coverage_roles,
    get_derived_keywords,
    get_display_names,
    get_coverage_priority_score,
    get_insurer_aliases,
    get_compare_patterns,
    get_coverage_keywords,
    get_insurer_only_patterns,
    get_default_insurers,
    get_recovery_messages,
    # STEP 3.6: Intent Keywords
    get_compare_trigger_keywords,
    get_lookup_force_keywords,
    get_ui_events_no_intent_change,
    # STEP 3.7: Coverage Resolution
    get_similarity_thresholds,
    get_resolution_status_codes,
    get_failure_messages,
    get_domain_representative_coverages,
    get_max_recommendations,
)

router = APIRouter(tags=["compare"])


# =============================================================================
# STEP 2.9: Query Anchor Model
# =============================================================================

class QueryAnchor(BaseModel):
    """
    Query Anchor - 대화형 질의에서 기준 담보와 의도를 유지

    세션 단위로 유지되며, 후속 질의에서 담보 컨텍스트 유지에 사용됨

    STEP 3.6: intent 필드 추가
    - lookup: 단일 보험사 정보 조회
    - compare: 복수 보험사 비교
    """
    coverage_code: str = Field(..., description="대표 담보 코드")
    coverage_name: str | None = Field(None, description="대표 담보 명칭")
    domain: str | None = Field(None, description="담보 도메인 (CANCER, CARDIO 등)")
    original_query: str = Field(..., description="anchor 생성 시점의 원본 질의")
    # STEP 3.6: Intent Locking
    intent: Literal["lookup", "compare"] = Field(
        default="lookup",
        description="질의 의도 (lookup=단일조회, compare=비교)"
    )


class CompareRequest(BaseModel):
    """비교 검색 요청"""
    # STEP 3.5: min_length 제거 - 0개도 허용 (auto-recovery 적용)
    insurers: list[str] = Field(default=[], description="비교할 보험사 코드 리스트")
    query: str = Field(..., description="사용자 질의", min_length=1)
    coverage_codes: list[str] | None = Field(None, description="필터할 coverage_code 리스트")
    top_k_per_insurer: int = Field(10, description="보험사별 최대 결과 수", ge=1, le=100)
    compare_doc_types: list[str] = Field(
        default=["가입설계서", "상품요약서", "사업방법서"],
        description="Compare Axis 대상 doc_type",
    )
    policy_doc_types: list[str] = Field(
        default=["약관"],
        description="Policy Axis 대상 doc_type",
    )
    policy_keywords: list[str] = Field(
        default=[],
        description="약관 검색 키워드",
    )
    # Step I: Plan 자동 선택
    age: int | None = Field(None, description="피보험자 나이 (plan 자동 선택용)", ge=0, le=150)
    gender: Literal["M", "F"] | None = Field(None, description="피보험자 성별 (M/F)")
    # STEP 2.9: Query Anchor
    anchor: QueryAnchor | None = Field(None, description="이전 질의의 anchor (후속 질의 시 전달)")
    # STEP 3.6: UI 이벤트 타입 (intent 변경 차단용)
    ui_event_type: str | None = Field(
        None,
        description="UI 이벤트 타입 (coverage_button_click 등 - intent 변경 차단)"
    )
    # STEP 3.9: Anchor Persistence - 담보 고정 요청
    locked_coverage_code: str | None = Field(
        None,
        description="고정할 담보 코드 (제공 시 coverage resolver 스킵) - deprecated, use locked_coverage_codes"
    )
    # STEP 4.5: Multi-subtype 지원 - 복수 담보 고정
    locked_coverage_codes: list[str] | None = Field(
        None,
        description="고정할 담보 코드 목록 (복수 subtype 비교 시 사용)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "insurers": ["SAMSUNG", "MERITZ"],
                    "query": "경계성 종양 암진단비",
                    "coverage_codes": ["A4200_1", "A4210"],
                    "top_k_per_insurer": 10,
                    "compare_doc_types": ["가입설계서", "상품요약서", "사업방법서"],
                    "policy_doc_types": ["약관"],
                    "policy_keywords": ["경계성", "유사암", "제자리암"],
                    "age": 35,
                    "gender": "M",
                }
            ]
        }
    }


class AmountInfoResponse(BaseModel):
    """금액 정보"""
    amount_value: int | None
    amount_text: str | None
    unit: str | None
    confidence: str
    method: str


class ConditionInfoResponse(BaseModel):
    """지급조건 정보"""
    snippet: str | None
    matched_terms: list[str]


class EvidenceResponse(BaseModel):
    """검색 결과 근거"""
    document_id: int
    doc_type: str
    page_start: int | None
    preview: str
    score: float
    amount: AmountInfoResponse | None = None
    condition_snippet: ConditionInfoResponse | None = None


class CompareAxisItemResponse(BaseModel):
    """Compare Axis 결과 항목"""
    insurer_code: str
    coverage_code: str
    coverage_name: str | None
    doc_type_counts: dict[str, int]
    evidence: list[EvidenceResponse]


class PolicyAxisItemResponse(BaseModel):
    """Policy Axis 결과 항목"""
    insurer_code: str
    keyword: str
    evidence: list[EvidenceResponse]


class InsurerCompareCellResponse(BaseModel):
    """비교표 셀: 보험사별 결과"""
    insurer_code: str
    doc_type_counts: dict[str, int]
    best_evidence: list[EvidenceResponse]


class CoverageCompareRowResponse(BaseModel):
    """비교표 행: coverage_code 기준"""
    coverage_code: str
    coverage_name: str | None
    insurers: list[InsurerCompareCellResponse]


class EvidenceRefResponse(BaseModel):
    """근거 참조"""
    insurer_code: str
    document_id: int
    page_start: int | None


class DiffBulletResponse(BaseModel):
    """차이점 문장"""
    text: str
    evidence_refs: list[EvidenceRefResponse]


class DiffSummaryItemResponse(BaseModel):
    """coverage_code별 차이점 요약"""
    coverage_code: str
    coverage_name: str | None
    bullets: list[DiffBulletResponse]


# =============================================================================
# STEP 3.7: Coverage Resolution Response Models
# =============================================================================

class SuggestedCoverageResponse(BaseModel):
    """추천 담보 항목"""
    coverage_code: str
    coverage_name: str | None
    similarity: float
    insurer_code: str | None = None


class CoverageResolutionResponse(BaseModel):
    """
    STEP 3.7-δ-β: Coverage Resolution 결과
    STEP 4.1: SUBTYPE_MULTI 추가

    status (resolution_state):
    - RESOLVED: 확정된 coverage_code 존재 (candidates == 1 && similarity >= confident)
    - UNRESOLVED: 후보는 있지만 확정 불가 (candidates >= 1, 유저 선택 필요)
    - INVALID: 매핑 불가 (candidates == 0, 재입력 필요)
    - SUBTYPE_MULTI: 복수 Subtype 비교 (경계성 종양 + 제자리암 등)
    """
    status: Literal["RESOLVED", "UNRESOLVED", "INVALID", "SUBTYPE_MULTI"]
    resolved_coverage_code: str | None = None
    message: str | None = None
    suggested_coverages: list[SuggestedCoverageResponse] = []
    detected_domain: str | None = None


# =============================================================================
# U-4.8: Comparison Slots
# =============================================================================

class SlotEvidenceRefResponse(BaseModel):
    """슬롯 근거 참조"""
    document_id: int
    page_start: int | None
    chunk_id: int | None = None


class LLMTraceResponse(BaseModel):
    """LLM 사용 추적 정보"""
    method: Literal["rule", "llm", "hybrid"]
    llm_used: bool
    llm_reason: Literal["flag_off", "ambiguity_high", "parse_fail", "cost_guard", "not_needed"] | None = None
    model: str | None = None


class SlotInsurerValueResponse(BaseModel):
    """슬롯 보험사별 값"""
    insurer_code: str
    value: str | None
    confidence: Literal["high", "medium", "low", "not_found"] = "medium"
    reason: str | None = None  # not_found일 때 이유
    evidence_refs: list[SlotEvidenceRefResponse] = []
    trace: LLMTraceResponse | None = None  # LLM usage trace


class ComparisonSlotResponse(BaseModel):
    """비교 슬롯 항목"""
    slot_key: str
    label: str
    comparable: bool
    insurers: list[SlotInsurerValueResponse]
    diff_summary: str | None = None  # 슬롯별 차이 요약


# =============================================================================
# STEP 4.1: Subtype Comparison Models
# =============================================================================

class SubtypeComparisonItemResponse(BaseModel):
    """Subtype별 보험사 비교 항목"""
    subtype_code: str
    subtype_name: str
    info_type: str  # definition, coverage, conditions
    info_label: str  # 정의, 보장 여부, 지급 조건
    insurer_code: str
    value: str | None
    confidence: Literal["high", "medium", "low", "not_found"] = "medium"
    evidence_ref: dict | None = None


class SubtypeComparisonResponse(BaseModel):
    """
    STEP 4.1: Subtype 비교 결과

    경계성 종양, 제자리암 등 질병 하위 개념의
    정의·포함 여부·조건 중심 비교 제공
    """
    subtypes: list[str] = []  # 추출된 subtype 코드 리스트
    comparison_items: list[SubtypeComparisonItemResponse] = []
    is_multi_subtype: bool = False  # 복수 subtype 비교 여부


class CompareResponseModel(BaseModel):
    """비교 검색 응답"""
    # STEP 3.7-δ-β: Resolution State (최상위 게이트 필드)
    # STEP 4.1: SUBTYPE_MULTI 추가
    resolution_state: Literal["RESOLVED", "UNRESOLVED", "INVALID", "SUBTYPE_MULTI"]
    resolved_coverage_code: str | None = None
    # 결과 필드들 (resolution_state != RESOLVED 시 null/empty)
    compare_axis: list[CompareAxisItemResponse] | None = None
    policy_axis: list[PolicyAxisItemResponse] | None = None
    coverage_compare_result: list[CoverageCompareRowResponse] | None = None
    diff_summary: list[DiffSummaryItemResponse] | None = None
    # U-4.8: Comparison Slots
    slots: list[ComparisonSlotResponse] | None = None
    # STEP 4.1: Subtype Comparison (경계성 종양, 제자리암 등)
    subtype_comparison: SubtypeComparisonResponse | None = None
    # resolved_coverage_codes: 질의에서 자동 추론된 coverage_code 목록
    resolved_coverage_codes: list[str] | None = None
    # STEP 2.5: 대표 담보 / 연관 담보 / 사용자 요약
    primary_coverage_code: str | None = None
    primary_coverage_name: str | None = None
    related_coverage_codes: list[str] = []
    user_summary: str | None = None
    # STEP 2.9: Query Anchor (다음 질의에 전달할 anchor)
    anchor: QueryAnchor | None = None
    # STEP 3.5: Insurer Auto-Recovery 메시지
    recovery_message: str | None = None
    # STEP 3.7: Coverage Resolution 결과 (상세 정보)
    coverage_resolution: CoverageResolutionResponse | None = None
    debug: dict[str, Any]


def _convert_evidence(e) -> EvidenceResponse:
    """Evidence를 EvidenceResponse로 변환 (amount/condition_snippet 포함)"""
    amount_resp = None
    if e.amount is not None:
        amount_resp = AmountInfoResponse(
            amount_value=e.amount.amount_value,
            amount_text=e.amount.amount_text,
            unit=e.amount.unit,
            confidence=e.amount.confidence,
            method=e.amount.method,
        )

    condition_resp = None
    if e.condition_snippet is not None:
        condition_resp = ConditionInfoResponse(
            snippet=e.condition_snippet.snippet,
            matched_terms=e.condition_snippet.matched_terms,
        )

    return EvidenceResponse(
        document_id=e.document_id,
        doc_type=e.doc_type,
        page_start=e.page_start,
        preview=e.preview,
        score=e.score,
        amount=amount_resp,
        condition_snippet=condition_resp,
    )


# =============================================================================
# STEP 2.5 + 2.7 + 2.7-α: 대표 담보 선택 및 사용자 요약 생성
# =============================================================================
# 모든 의미 규칙은 config/ 디렉토리의 YAML 파일에서 로드됨
#
# 설정 파일 목록:
# - config/coverage_domain.yaml  : coverage_code → domain 매핑
# - config/domain_priority.yaml  : domain → 대표 담보 우선순위
# - config/coverage_role.yaml    : coverage_code → MAIN/DERIVED 구분
# - config/domain_keywords.yaml  : 질의 키워드 → domain 매핑
# - config/derived_keywords.yaml : 파생 담보 요청 키워드 매핑
# - config/display_names.yaml    : 표시용 이름 매핑
#
# 핵심 원칙:
# - 코드 수정 없이 설정 파일만으로 규칙 변경 가능
# - 질의 계열과 다른 담보가 대표로 선택되는 문제 차단

# =============================================================================
# STEP 2.9: Query Anchor / Follow-up Query Detection
# =============================================================================

def _has_coverage_keyword(query: str) -> bool:
    """
    질의에 coverage 키워드가 포함되어 있는지 확인

    Returns:
        True if query contains coverage keywords (anchor 재설정 필요)
    """
    coverage_keywords = get_coverage_keywords()
    query_lower = query.lower()

    for keyword in coverage_keywords:
        if keyword.lower() in query_lower:
            return True
    return False


def _is_insurer_only_query(query: str, anchor: QueryAnchor | None) -> bool:
    """
    insurer-only 후속 질의인지 판별

    조건:
    1. anchor가 존재해야 함
    2. coverage 키워드가 없어야 함
    3. insurer 키워드만 존재하거나, insurer-only 패턴이 있어야 함

    Returns:
        True if this is an insurer-only follow-up query
    """
    if anchor is None:
        return False

    # coverage 키워드가 있으면 insurer-only가 아님
    if _has_coverage_keyword(query):
        return False

    # insurer 키워드가 있는지 확인
    insurers = _extract_insurers_from_query(query)
    if insurers:
        return True

    # insurer-only 패턴 확인
    insurer_only_patterns = get_insurer_only_patterns()
    for pattern in insurer_only_patterns:
        if pattern in query:
            # 패턴이 있더라도 insurer 키워드가 있어야 함
            if insurers:
                return True

    return False


def _detect_follow_up_query_type(
    query: str,
    anchor: QueryAnchor | None,
) -> tuple[str, dict[str, Any]]:
    """
    후속 질의 유형 판별

    Returns:
        (query_type, debug_info)
        query_type:
          - "new": 신규 질의 (anchor 생성)
          - "insurer_only": insurer만 변경하는 후속 질의 (anchor 유지)
          - "intent_extension": intent 확장 후속 질의 (anchor 유지 + intent 추가)
    """
    debug_info = {
        "has_anchor": anchor is not None,
        "has_coverage_keyword": _has_coverage_keyword(query),
        "extracted_insurers": _extract_insurers_from_query(query),
    }

    # anchor가 없으면 신규 질의
    if anchor is None:
        debug_info["reason"] = "no_anchor"
        return "new", debug_info

    # coverage 키워드가 있으면 anchor 재설정 (신규 질의)
    if _has_coverage_keyword(query):
        debug_info["reason"] = "coverage_keyword_found"
        return "new", debug_info

    # insurer 키워드만 있으면 insurer-only 후속 질의
    insurers = debug_info["extracted_insurers"]
    if insurers:
        debug_info["reason"] = "insurer_only_followup"
        return "insurer_only", debug_info

    # 그 외에는 신규 질의로 처리 (안전한 기본값)
    debug_info["reason"] = "fallback_to_new"
    return "new", debug_info


# =============================================================================
# STEP 2.6: Insurer Scope Resolver (룰 기반, LLM 미사용)
# =============================================================================

# STEP 2.8: INSURER_ALIASES와 COMPARE_PATTERNS는 config 파일로 외부화됨
# - config/mappings/insurer_alias.yaml
# - config/rules/compare_patterns.yaml
# get_insurer_aliases(), get_compare_patterns() 함수로 접근


def _extract_insurers_from_query(query: str) -> list[str]:
    """
    Query 문자열에서 보험사 명칭을 룰 기반으로 추출

    Returns:
        추출된 insurer code 리스트 (중복 제거, 순서 유지)
    """
    found_insurers: list[str] = []
    query_lower = query.lower()

    # STEP 2.8: config에서 alias 로드
    insurer_aliases = get_insurer_aliases()

    # 긴 alias부터 먼저 매칭 (예: "삼성화재"가 "삼성"보다 먼저)
    sorted_aliases = sorted(insurer_aliases.keys(), key=len, reverse=True)

    for alias in sorted_aliases:
        alias_lower = alias.lower()
        if alias_lower in query_lower:
            insurer_code = insurer_aliases[alias]
            if insurer_code not in found_insurers:
                found_insurers.append(insurer_code)

    return found_insurers


def _has_explicit_compare_intent(query: str) -> bool:
    """
    Query가 명시적으로 비교 의도를 가지는지 판별

    Returns:
        True if query contains explicit comparison patterns
    """
    # STEP 2.8: config에서 패턴 로드
    compare_patterns = get_compare_patterns()
    for pattern in compare_patterns:
        if pattern in query:
            return True
    return False


# =============================================================================
# STEP 3.6: Intent Detection & Locking
# =============================================================================

def _detect_intent_from_query(query: str) -> tuple[Literal["lookup", "compare"], dict[str, Any]]:
    """
    STEP 3.6: Query에서 intent(lookup/compare) 감지

    핵심 원칙:
    - 기본 Intent는 lookup (단일 보험사 정보 조회)
    - 비교 키워드가 명시적으로 포함된 경우에만 compare
    - lookup_force_keywords가 있으면 compare 트리거 무시

    Returns:
        (intent, debug_info)
    """
    debug_info: dict[str, Any] = {
        "has_compare_trigger": False,
        "has_lookup_force": False,
        "matched_compare_keyword": None,
        "matched_lookup_keyword": None,
    }

    query_lower = query.lower()

    # lookup 강제 키워드 확인
    lookup_force_keywords = get_lookup_force_keywords()
    for keyword in lookup_force_keywords:
        if keyword in query_lower:
            debug_info["has_lookup_force"] = True
            debug_info["matched_lookup_keyword"] = keyword
            break

    # 비교 트리거 키워드 확인
    compare_trigger_keywords = get_compare_trigger_keywords()
    for keyword in compare_trigger_keywords:
        if keyword in query_lower:
            debug_info["has_compare_trigger"] = True
            debug_info["matched_compare_keyword"] = keyword
            break

    # lookup 강제가 있으면 lookup 유지
    if debug_info["has_lookup_force"]:
        debug_info["intent_reason"] = "lookup_force_keyword"
        return "lookup", debug_info

    # 비교 트리거가 있으면 compare
    if debug_info["has_compare_trigger"]:
        debug_info["intent_reason"] = "compare_trigger_keyword"
        return "compare", debug_info

    # 기본값: lookup
    debug_info["intent_reason"] = "default_lookup"
    return "lookup", debug_info


# =============================================================================
# STEP 3.7-δ-β: Coverage Resolution State Evaluation
# =============================================================================

def _evaluate_coverage_resolution(
    query: str,
    resolved_coverage_codes: list[str] | None,
    coverage_recommendations: list[dict[str, Any]] | None,
) -> tuple[CoverageResolutionResponse, dict[str, Any]]:
    """
    STEP 3.7-δ-β: Coverage Resolution 상태 평가

    상태 분류 로직:
    - candidates == 0 → INVALID (재입력 필요)
    - candidates == 1 && similarity >= confident → RESOLVED (확정)
    - candidates >= 1 but not confident → UNRESOLVED (선택 필요)

    Args:
        query: 사용자 질의
        resolved_coverage_codes: 자동 추론된 coverage_code 목록
        coverage_recommendations: 추천 결과 (similarity 포함)

    Returns:
        (CoverageResolutionResponse, debug_info)
    """
    thresholds = get_similarity_thresholds()
    failure_messages = get_failure_messages()
    max_recommendations = get_max_recommendations()

    num_candidates = len(resolved_coverage_codes) if resolved_coverage_codes else 0

    debug_info: dict[str, Any] = {
        "thresholds": thresholds,
        "num_candidates": num_candidates,
        "recommendations_count": len(coverage_recommendations) if coverage_recommendations else 0,
    }

    # ==========================================================================
    # Case 1: candidates == 0 → INVALID
    # ==========================================================================
    if num_candidates == 0:
        detected_domain = _detect_query_domain(query)
        debug_info["detected_domain"] = detected_domain

        if detected_domain:
            # 도메인은 추정됨 → INVALID with domain suggestions
            domain_coverages = get_domain_representative_coverages()
            domain_info = domain_coverages.get(detected_domain, {})
            domain_display = domain_info.get("display_name", detected_domain)

            suggested = [
                SuggestedCoverageResponse(
                    coverage_code=cov["code"],
                    coverage_name=cov["name"],
                    similarity=0.0,
                )
                for cov in domain_info.get("coverages", [])[:max_recommendations]
            ]

            message = failure_messages.get("clarify_domain", "").format(domain=domain_display)

            debug_info["status"] = "INVALID"
            debug_info["reason"] = "no_candidates_domain_detected"

            return CoverageResolutionResponse(
                status="INVALID",
                resolved_coverage_code=None,
                message=message,
                suggested_coverages=suggested,
                detected_domain=detected_domain,
            ), debug_info
        else:
            # 도메인도 추정 불가 → INVALID
            message = failure_messages.get("clarify_general", "담보명을 좀 더 구체적으로 입력해 주세요.")

            debug_info["status"] = "INVALID"
            debug_info["reason"] = "no_candidates_no_domain"

            return CoverageResolutionResponse(
                status="INVALID",
                resolved_coverage_code=None,
                message=message,
                suggested_coverages=[],
                detected_domain=None,
            ), debug_info

    # ==========================================================================
    # Case 2: candidates >= 1 → RESOLVED or UNRESOLVED
    # ==========================================================================
    confident_threshold = thresholds.get("confident", 0.5)

    # similarity 정보 수집 (1위, 2위 - 서로 다른 coverage_code 기준)
    sorted_recommendations = sorted(
        coverage_recommendations or [],
        key=lambda x: x.get("similarity", 0),
        reverse=True
    )

    best_similarity = sorted_recommendations[0].get("similarity", 0.0) if sorted_recommendations else 0.0
    best_code = sorted_recommendations[0].get("coverage_code") if sorted_recommendations else None

    # 2위 찾기: 1위와 다른 coverage_code 중 가장 높은 similarity
    second_similarity = 0.0
    second_code = None
    for r in sorted_recommendations[1:]:
        if r.get("coverage_code") != best_code:
            second_similarity = r.get("similarity", 0.0)
            second_code = r.get("coverage_code")
            break

    similarity_gap = best_similarity - second_similarity

    debug_info["best_similarity"] = best_similarity
    debug_info["best_code"] = best_code
    debug_info["second_similarity"] = second_similarity
    debug_info["second_code"] = second_code
    debug_info["similarity_gap"] = similarity_gap

    # RESOLVED 조건 (완화):
    # 1) candidates == 1 && similarity >= confident
    # 2) best_similarity >= confident && gap >= 0.15 (1위가 압도적)
    # 3) best_similarity >= 0.9 (완벽 매칭에 가까움)
    gap_threshold = 0.15
    perfect_match_threshold = 0.9
    is_single_confident = num_candidates == 1 and best_similarity >= confident_threshold
    is_gap_confident = best_similarity >= confident_threshold and similarity_gap >= gap_threshold
    is_perfect_match = best_similarity >= perfect_match_threshold

    if is_single_confident or is_gap_confident or is_perfect_match:
        resolved_code = best_code

        if is_single_confident:
            reason = "single_candidate_confident"
        elif is_perfect_match:
            reason = "perfect_match"
        else:
            reason = "gap_confident"

        debug_info["status"] = "RESOLVED"
        debug_info["reason"] = reason

        return CoverageResolutionResponse(
            status="RESOLVED",
            resolved_coverage_code=resolved_code,
            message=None,
            suggested_coverages=[],
            detected_domain=None,
        ), debug_info

    # ==========================================================================
    # UNRESOLVED: candidates >= 1 but not confident
    # ==========================================================================
    display_names = get_display_names()
    coverage_names_map = display_names.get("coverage_names", {})

    suggested = []
    seen_codes = set()
    if coverage_recommendations:
        for r in sorted(coverage_recommendations, key=lambda x: x.get("similarity", 0), reverse=True):
            code = r.get("coverage_code")
            if code and code not in seen_codes:
                suggested.append(
                    SuggestedCoverageResponse(
                        coverage_code=code,
                        coverage_name=coverage_names_map.get(code, r.get("coverage_name")),
                        similarity=r.get("similarity", 0.0),
                        insurer_code=r.get("insurer_code"),
                    )
                )
                seen_codes.add(code)
                if len(suggested) >= max_recommendations:
                    break

    message = failure_messages.get("suggest_intro", "아래 담보 중 하나를 선택해 주세요:")

    debug_info["status"] = "UNRESOLVED"
    debug_info["reason"] = "candidates_not_confident"

    return CoverageResolutionResponse(
        status="UNRESOLVED",
        resolved_coverage_code=None,
        message=message,
        suggested_coverages=suggested,
        detected_domain=None,
    ), debug_info


def _resolve_intent(
    query: str,
    anchor: QueryAnchor | None,
    ui_event_type: str | None,
    query_insurers: list[str],
) -> tuple[Literal["lookup", "compare"], dict[str, Any]]:
    """
    STEP 3.6: Intent Locking - 최종 intent 결정

    핵심 원칙:
    1) UI 이벤트로 인한 intent 변경 금지
    2) anchor에 intent가 있으면 유지 (명시적 변경 신호 없는 한)
    3) 명시적 비교 키워드가 있을 때만 compare로 변경
    4) insurer 변경, coverage 변경은 intent 변경 사유가 아님

    Returns:
        (final_intent, debug_info)
    """
    debug_info: dict[str, Any] = {
        "anchor_intent": anchor.intent if anchor else None,
        "ui_event_type": ui_event_type,
        "ui_event_blocked_change": False,
        "intent_locked": False,
        "query_insurers_count": len(query_insurers),
    }

    # 1) UI 이벤트로 인한 요청인 경우 - intent 변경 금지
    no_intent_change_events = get_ui_events_no_intent_change()
    if ui_event_type and ui_event_type in no_intent_change_events:
        debug_info["ui_event_blocked_change"] = True
        if anchor:
            debug_info["intent_locked"] = True
            debug_info["intent_reason"] = "ui_event_blocked_anchor_preserved"
            return anchor.intent, debug_info
        else:
            # anchor가 없는데 UI 이벤트인 경우 (비정상) → lookup 기본값
            debug_info["intent_reason"] = "ui_event_no_anchor_default_lookup"
            return "lookup", debug_info

    # 2) Query에서 intent 감지
    query_intent, query_intent_debug = _detect_intent_from_query(query)
    debug_info["query_intent"] = query_intent
    debug_info["query_intent_debug"] = query_intent_debug

    # 3) anchor가 있는 경우 - Intent Locking 적용
    if anchor:
        # 명시적 비교 키워드가 있으면 compare로 전환 허용
        if query_intent_debug.get("has_compare_trigger") and not query_intent_debug.get("has_lookup_force"):
            debug_info["intent_reason"] = "explicit_compare_override"
            return "compare", debug_info

        # 그 외에는 anchor intent 유지
        debug_info["intent_locked"] = True
        debug_info["intent_reason"] = "anchor_intent_preserved"
        return anchor.intent, debug_info

    # 4) anchor가 없는 경우 - 새로운 intent 결정
    # 복수 보험사가 질의에 명시된 경우 compare 가능성
    if len(query_insurers) > 1 and query_intent == "compare":
        debug_info["intent_reason"] = "new_query_multi_insurer_compare"
        return "compare", debug_info

    # 기본값 또는 query에서 감지된 intent 사용
    debug_info["intent_reason"] = f"new_query_{query_intent}"
    return query_intent, debug_info


def _resolve_insurer_scope(
    request_insurers: list[str],
    query: str,
) -> tuple[list[str], dict[str, Any]]:
    """
    STEP 2.6: Insurer Scope 결정 (룰 기반, LLM 미사용)

    핵심 원칙:
    - Query에 특정 insurer가 명시되면, 그 insurer(들)로 scope를 제한
    - 사용자가 요청하지 않은 insurer가 결과에 암묵적으로 등장하지 않도록 차단

    Rules:
    - Rule A-1: query에 insurer가 명시된 경우 → query 기준으로 scope 결정
               (request insurers와 교집합 또는 query insurers만 사용)
    - Rule A-2: query에 insurer가 없고 request에 있는 경우 → request 값 사용
    - Rule B: query에 명시적 비교 표현("vs", "비교")이 있으면 → 복수 insurer 허용
    - Rule C: 둘 다 없는 경우 → 에러

    Args:
        request_insurers: Request body에서 받은 insurers 리스트
        query: 사용자 질의 문자열

    Returns:
        (final_insurers, debug_info)
    """
    debug_info: dict[str, Any] = {
        "insurer_scope_method": None,
        "request_insurers": request_insurers,
        "query_extracted_insurers": [],
        "has_compare_intent": False,
        "scope_narrowed": False,
        "scope_expanded": False,
    }

    # Query에서 insurer 추출
    query_insurers = _extract_insurers_from_query(query)
    debug_info["query_extracted_insurers"] = query_insurers

    # 비교 의도 확인
    has_compare_intent = _has_explicit_compare_intent(query)
    debug_info["has_compare_intent"] = has_compare_intent

    # Case 1: Query에 insurer가 명시된 경우 → Query 기준으로 scope 결정
    if query_insurers:
        # 비교 의도가 있고 복수 insurer가 query에 있으면 그대로 사용
        if has_compare_intent and len(query_insurers) > 1:
            debug_info["insurer_scope_method"] = "query_compare_explicit"
            return query_insurers, debug_info

        # 단일 insurer만 query에 있으면 → 해당 insurer로 좁힘
        if len(query_insurers) == 1:
            debug_info["insurer_scope_method"] = "query_single_explicit"
            debug_info["scope_narrowed"] = len(request_insurers) > 1
            return query_insurers, debug_info

        # Query에서 추출된 insurers 사용 (request와 무관하게)
        debug_info["insurer_scope_method"] = "query_extracted"
        return query_insurers, debug_info

    # Case 2: Query에 insurer가 없고, request에 있는 경우
    if request_insurers and len(request_insurers) > 0:
        debug_info["insurer_scope_method"] = "request_explicit"
        return request_insurers, debug_info

    # Case 3: 둘 다 없는 경우 → STEP 3.5 Auto-Recovery 적용
    # 기본 insurer 정책 적용 (하드코딩 금지 - config에서 로드)
    default_insurers = get_default_insurers()
    debug_info["insurer_scope_method"] = "auto_recovery_default"
    debug_info["recovery_applied"] = True
    debug_info["recovery_reason"] = "no_insurer_selected"
    return default_insurers, debug_info


def _detect_query_domain(query: str) -> str | None:
    """
    STEP 2.7-α: Query에서 담보/질병 계열(domain) 판별

    핵심 원칙:
    - Query에 특정 계열 키워드가 있으면 해당 domain 반환
    - 여러 계열이 동시에 등장하면 None 반환 (기존 로직 유지)
    - 긴 키워드 우선 매칭 (예: "암수술"이 "수술"보다 먼저)

    Returns:
        domain: "CANCER", "CARDIO", "INJURY", "SURGERY" 또는 None
    """
    query_lower = query.lower()

    # 설정 파일에서 키워드 로드
    domain_keywords = get_domain_keywords()

    # 모든 키워드를 (keyword, domain) 튜플로 수집 후 길이 내림차순 정렬
    all_keywords: list[tuple[str, str]] = []
    for domain, keywords in domain_keywords.items():
        for keyword in keywords:
            all_keywords.append((keyword, domain))

    # 길이 내림차순 정렬 (긴 키워드 우선)
    all_keywords.sort(key=lambda x: len(x[0]), reverse=True)

    # 매칭된 domain들 수집
    matched_domains: set[str] = set()
    for keyword, domain in all_keywords:
        if keyword in query_lower:
            matched_domains.add(domain)

    # 단일 계열만 매칭된 경우 해당 domain 반환
    if len(matched_domains) == 1:
        return matched_domains.pop()

    # 복수 계열 또는 미매칭 → None (기존 로직 유지)
    return None


def _detect_derived_intent(query: str) -> tuple[bool, str | None]:
    """
    STEP 2.7: Query가 파생 담보를 명시적으로 요청하는지 판별

    Returns:
        (is_derived_intent, target_code_or_group)
        - is_derived_intent: 파생 담보 요청 여부
        - target_code_or_group: 요청된 coverage_code 또는 "subtype" 등 그룹명
    """
    query_lower = query.lower()

    # 설정 파일에서 키워드 로드
    derived_keywords = get_derived_keywords()

    # 모든 키워드를 (keyword, code) 튜플로 수집 후 키워드 길이 기준 정렬
    # 긴 키워드부터 먼저 매칭 (예: "유사암제외"가 "유사암"보다 먼저)
    all_keywords: list[tuple[str, str]] = []
    for code_or_group, keywords in derived_keywords.items():
        for keyword in keywords:
            all_keywords.append((keyword, code_or_group))

    # 길이 내림차순 정렬
    all_keywords.sort(key=lambda x: len(x[0]), reverse=True)

    for keyword, code_or_group in all_keywords:
        if keyword in query_lower:
            return True, code_or_group

    return False, None


def _select_primary_coverage(
    resolved_codes: list[str] | None,
    coverage_compare_result: list,
    query: str = "",
) -> tuple[str | None, str | None, list[str]]:
    """
    STEP 2.7 + 2.7-α: 대표 담보 1개 선택 및 연관 담보 분리

    처리 순서 (STEP 2.7-α):
    1) query_domain 판별
    2) coverage_code 후보 → domain 기준 필터링
    3) 메인 담보 우선 정책 적용 (STEP 2.7)
    4) 대표 담보 1개 확정
    5) 동일 domain의 나머지 → related_coverages

    핵심 원칙:
    - Query가 "암진단비"면 암 계열만 대표 후보
    - 다른 계열(상해 등)은 대표에서 완전 제외 + 연관 담보에도 미포함

    Returns:
        (primary_code, primary_name, related_codes)
    """
    if not resolved_codes:
        return None, None, []

    # 설정 파일에서 로드
    coverage_domains = get_coverage_domains()
    coverage_roles = get_coverage_roles()

    # =========================================================================
    # STEP 2.7-α: Domain 기반 필터링 (최우선)
    # =========================================================================
    query_domain = _detect_query_domain(query)

    if query_domain:
        # Query에서 계열이 확정된 경우 → 해당 계열 코드만 남김
        domain_filtered_codes = [
            c for c in resolved_codes
            if coverage_domains.get(c) == query_domain
        ]

        # 필터링 후 코드가 있으면 해당 코드들만 사용
        # 없으면 (domain 매핑이 없는 코드만 남은 경우) 기존 resolved_codes 사용
        if domain_filtered_codes:
            candidate_codes = domain_filtered_codes
        else:
            # Domain 매핑이 없는 코드들 중에서 선택 (fallback)
            candidate_codes = [
                c for c in resolved_codes
                if c not in coverage_domains
            ]
            if not candidate_codes:
                # 모든 코드가 다른 domain → 첫 번째 코드로 fallback
                candidate_codes = resolved_codes
    else:
        # Domain 확정 안됨 → 기존 로직 (모든 코드 대상)
        candidate_codes = resolved_codes

    # =========================================================================
    # STEP 2.7: Query 의도 파악 (메인/파생)
    # =========================================================================
    is_derived_intent, target_code = _detect_derived_intent(query)

    # 메인/파생 그룹 분류 (domain 필터링된 candidate_codes 기준)
    # coverage_role.yaml: MAIN / DERIVED
    main_codes = [c for c in candidate_codes if coverage_roles.get(c, "").upper() == "MAIN"]
    derived_codes = [c for c in candidate_codes if coverage_roles.get(c, "").upper() == "DERIVED"]
    unknown_codes = [c for c in candidate_codes if c not in coverage_roles]

    # 파생 담보 명시 요청인 경우
    if is_derived_intent and target_code:
        # subtype은 특별 처리 (기존 로직 유지)
        if target_code == "subtype":
            # subtype 관련은 기존 우선순위 그대로
            sorted_codes = sorted(
                candidate_codes,
                key=lambda c: get_coverage_priority_score(c)
            )
            primary_code = sorted_codes[0]
            # 동일 domain만 related로 (STEP 2.7-α)
            related_codes = [
                c for c in sorted_codes[1:]
                if not query_domain or coverage_domains.get(c) == query_domain
            ]
        else:
            # 특정 파생 담보 요청
            if target_code in candidate_codes:
                primary_code = target_code
                related_codes = [
                    c for c in candidate_codes if c != target_code
                ]
            else:
                # 요청한 담보가 없으면 파생 담보 중에서 선택
                if derived_codes:
                    sorted_derived = sorted(
                        derived_codes,
                        key=lambda c: get_coverage_priority_score(c)
                    )
                    primary_code = sorted_derived[0]
                    related_codes = [c for c in candidate_codes if c != primary_code]
                else:
                    # 파생 담보도 없으면 기존 로직
                    sorted_codes = sorted(
                        candidate_codes,
                        key=lambda c: get_coverage_priority_score(c)
                    )
                    primary_code = sorted_codes[0]
                    related_codes = sorted_codes[1:] if len(sorted_codes) > 1 else []
    else:
        # 메인 담보 의도 (일반 질의)
        # 메인 담보가 있으면 메인 담보 우선, 없으면 파생 담보 사용
        if main_codes:
            sorted_main = sorted(
                main_codes,
                key=lambda c: get_coverage_priority_score(c)
            )
            primary_code = sorted_main[0]
            # 동일 domain만 related로 (STEP 2.7-α)
            related_codes = [
                c for c in candidate_codes if c != primary_code
            ]
        elif derived_codes:
            sorted_derived = sorted(
                derived_codes,
                key=lambda c: get_coverage_priority_score(c)
            )
            primary_code = sorted_derived[0]
            related_codes = [c for c in candidate_codes if c != primary_code]
        elif unknown_codes:
            sorted_unknown = sorted(
                unknown_codes,
                key=lambda c: get_coverage_priority_score(c)
            )
            primary_code = sorted_unknown[0]
            related_codes = sorted_unknown[1:] if len(sorted_unknown) > 1 else []
        else:
            return None, None, []

    # 이름 찾기: 설정 파일에서 또는 coverage_compare_result에서
    display_names = get_display_names()
    primary_name = display_names.get("coverage_names", {}).get(primary_code)
    if not primary_name:
        for row in coverage_compare_result:
            if row.coverage_code == primary_code and row.coverage_name:
                primary_name = row.coverage_name
                break

    return primary_code, primary_name, related_codes


def _generate_user_summary(
    query: str,
    insurers: list[str],
    primary_code: str | None,
    primary_name: str | None,
    slots: list,
    coverage_compare_result: list,
) -> str:
    """
    사용자 친화적 요약 문장 생성

    금지사항:
    - "[담보명] SAMSUNG은 ○○ 근거가 있고…" 형식 금지
    - coverage_code 나열 금지
    - 보험사별 내부 비교 로그 금지

    허용:
    - "삼성 암진단비는 약관 기준으로 일반암 진단 시 일시금이 지급됩니다."
    - "유사암은 별도 담보로 분리되어 보장됩니다."
    """
    lines = []

    # 설정 파일에서 표시 이름 로드
    display_names = get_display_names()
    insurer_display = display_names.get("insurer_names", {})

    # 보험사 이름 변환
    insurer_names = [insurer_display.get(ic, ic) for ic in insurers]
    insurer_str = ", ".join(insurer_names)

    # 담보 이름
    coverage_name = primary_name or "해당 담보"

    # 기본 요약
    if len(insurers) == 1:
        lines.append(f"{insurer_str}의 {coverage_name} 정보를 조회했습니다.")
    else:
        lines.append(f"{insurer_str}의 {coverage_name}를 비교했습니다.")

    # 슬롯 기반 요약 추가
    if slots:
        # existence_status 슬롯 확인
        existence_slot = next(
            (s for s in slots if s.slot_key == "existence_status"),
            None
        )
        if existence_slot:
            has_coverage = []
            no_coverage = []
            for iv in existence_slot.insurers:
                name = insurer_display.get(iv.insurer_code, iv.insurer_code)
                if iv.value == "있음":
                    has_coverage.append(name)
                elif iv.value == "없음" or iv.confidence == "not_found":
                    no_coverage.append(name)

            if has_coverage and not no_coverage:
                if len(has_coverage) > 1:
                    lines.append(f"모든 보험사에서 해당 담보를 보장합니다.")
            elif has_coverage and no_coverage:
                lines.append(
                    f"{', '.join(has_coverage)}에서 보장하며, "
                    f"{', '.join(no_coverage)}은(는) 해당 담보가 확인되지 않습니다."
                )

        # payout_amount 또는 diagnosis_lump_sum_amount 슬롯 확인
        amount_slot = next(
            (s for s in slots if s.slot_key in ["payout_amount", "diagnosis_lump_sum_amount"]),
            None
        )
        if amount_slot:
            amounts = []
            for iv in amount_slot.insurers:
                if iv.value and iv.confidence in ("high", "medium"):
                    name = insurer_display.get(iv.insurer_code, iv.insurer_code)
                    amounts.append(f"{name} {iv.value}")
            if amounts:
                lines.append(f"지급금액: {', '.join(amounts)}")

    # 연관 담보 안내
    related_count = len(coverage_compare_result) - 1 if coverage_compare_result else 0
    if related_count > 0:
        lines.append(f"\n관련 담보 {related_count}개가 함께 조회되었습니다. (연관 담보 섹션 참조)")

    # 상세 안내
    lines.append("\n자세한 비교 내용은 오른쪽 패널을 확인해주세요.")

    return "\n".join(lines)


def _convert_slots(slots: list) -> list[ComparisonSlotResponse]:
    """슬롯 결과를 API 응답 모델로 변환"""
    return [
        ComparisonSlotResponse(
            slot_key=slot.slot_key,
            label=slot.label,
            comparable=slot.comparable,
            insurers=[
                SlotInsurerValueResponse(
                    insurer_code=iv.insurer_code,
                    value=iv.value,
                    confidence=iv.confidence,
                    reason=iv.reason,
                    evidence_refs=[
                        SlotEvidenceRefResponse(
                            document_id=ref.document_id,
                            page_start=ref.page_start,
                            chunk_id=getattr(ref, 'chunk_id', None),
                        )
                        for ref in iv.evidence_refs
                    ],
                    trace=LLMTraceResponse(
                        method=iv.trace.method,
                        llm_used=iv.trace.llm_used,
                        llm_reason=iv.trace.llm_reason,
                        model=iv.trace.model,
                    ) if iv.trace else None,
                )
                for iv in slot.insurers
            ],
            diff_summary=slot.diff_summary,
        )
        for slot in slots
    ]


def _convert_response(
    result: CompareResponse,
    final_insurers: list[str],
    query: str,
    insurer_scope_debug: dict[str, Any],
    anchor_debug: dict[str, Any] | None = None,
    input_anchor: QueryAnchor | None = None,
    recovery_message: str | None = None,
    # STEP 3.6: Intent Locking
    resolved_intent: Literal["lookup", "compare"] = "lookup",
    intent_debug: dict[str, Any] | None = None,
    # STEP 3.7: Coverage Resolution
    coverage_resolution: CoverageResolutionResponse | None = None,
    resolution_debug: dict[str, Any] | None = None,
    # STEP 4.1: Subtype Comparison
    subtype_comparison: SubtypeComparisonResponse | None = None,
) -> CompareResponseModel:
    """내부 결과를 API 응답 모델로 변환"""
    # STEP 2.5 + 2.7: 대표 담보 선택 (query 의도 기반)
    primary_code, primary_name, related_codes = _select_primary_coverage(
        result.resolved_coverage_codes,
        result.coverage_compare_result,
        query=query,  # STEP 2.7: query 전달하여 메인/파생 의도 파악
    )

    # 슬롯 변환
    converted_slots = _convert_slots(getattr(result, 'slots', []))

    # STEP 2.5: 사용자 친화적 요약 생성 (STEP 2.6: final_insurers만 사용)
    user_summary = _generate_user_summary(
        query=query,
        insurers=final_insurers,
        primary_code=primary_code,
        primary_name=primary_name,
        slots=getattr(result, 'slots', []),
        coverage_compare_result=result.coverage_compare_result,
    )

    # STEP 2.6: debug에 insurer scope 정보 추가
    merged_debug = {**result.debug, "insurer_scope": insurer_scope_debug}

    # STEP 2.9: anchor debug 정보 추가
    if anchor_debug:
        merged_debug["anchor"] = anchor_debug

    # STEP 3.6: intent debug 정보 추가
    if intent_debug:
        merged_debug["intent"] = intent_debug

    # STEP 3.7: resolution debug 정보 추가
    if resolution_debug:
        merged_debug["coverage_resolution"] = resolution_debug

    # STEP 2.9 + 3.6 + 3.7: 새 anchor 생성 (intent 포함)
    # 기존 anchor 유지 조건:
    # 1. insurer_only 후속 질의인 경우
    # 2. UI 이벤트로 인해 intent가 locked된 경우 (STEP 3.6)
    # Anchor 생성 차단 조건 (STEP 3.7):
    # - coverage_resolution.status != "resolved"
    new_anchor: QueryAnchor | None = None
    should_preserve_anchor = (
        (anchor_debug and anchor_debug.get("query_type") == "insurer_only") or
        (intent_debug and intent_debug.get("intent_locked") and intent_debug.get("ui_event_blocked_change"))
    )

    # ==========================================================================
    # STEP 3.7-δ-β: Resolution State Gate
    # STEP 4.1: SUBTYPE_MULTI는 특별 처리 (담보 선택 UI 없이 subtype 비교 결과 반환)
    # ==========================================================================
    resolution_state = coverage_resolution.status if coverage_resolution else "RESOLVED"
    resolved_coverage_code = coverage_resolution.resolved_coverage_code if coverage_resolution else None

    # STEP 4.1: SUBTYPE_MULTI 상태 - subtype 비교 결과 포함하여 반환
    if resolution_state == "SUBTYPE_MULTI":
        merged_debug["resolution_gate"] = "subtype_multi_allowed"
        merged_debug["resolution_gate_reason"] = "multi_subtype_comparison"

        # 멀티 Subtype 비교용 요약 문구 생성
        display_names = get_display_names()
        insurer_display = display_names.get("insurer_names", {})
        insurer_names = [insurer_display.get(ic, ic) for ic in final_insurers]
        insurer_str = ", ".join(insurer_names)

        # subtype_comparison에서 subtype 이름 추출
        subtype_names = []
        if subtype_comparison and subtype_comparison.subtypes:
            for code in subtype_comparison.subtypes:
                defn = get_subtype_definition(code)
                if defn:
                    subtype_names.append(defn.name)

        subtype_str = " 및 ".join(subtype_names) if subtype_names else "경계성 종양 및 제자리암"

        multi_subtype_summary = (
            f"{insurer_str}의 {subtype_str} 보장 기준을 비교했습니다.\n"
            f"두 subtype은 동일 담보가 아니며, 보장 정의와 지급 조건이 다를 수 있습니다."
        )

        return CompareResponseModel(
            resolution_state=resolution_state,
            resolved_coverage_code=None,  # STEP 4.1: 단일 coverage_code 확정 금지
            compare_axis=None,  # 멀티 subtype에서는 compare_axis 불필요
            policy_axis=None,
            coverage_compare_result=None,
            diff_summary=None,
            slots=None,
            subtype_comparison=subtype_comparison,  # STEP 4.1: subtype 비교 결과 제공!
            resolved_coverage_codes=None,
            primary_coverage_code=None,
            primary_coverage_name=None,
            related_coverage_codes=[],
            user_summary=multi_subtype_summary,  # 멀티 subtype 요약 문구
            anchor=None,  # STEP 4.1: anchor 생성 금지 (Resolution Lock 금지)
            recovery_message=recovery_message,
            coverage_resolution=coverage_resolution,
            debug=merged_debug,
        )

    # STEP 3.7-δ-β: RESOLVED가 아니면 (UNRESOLVED, INVALID) 결과 데이터 null 반환
    if resolution_state != "RESOLVED":
        merged_debug["resolution_gate"] = "blocked"
        merged_debug["resolution_gate_reason"] = f"resolution_state={resolution_state}"

        return CompareResponseModel(
            resolution_state=resolution_state,
            resolved_coverage_code=resolved_coverage_code,
            compare_axis=None,
            policy_axis=None,
            coverage_compare_result=None,
            diff_summary=None,
            slots=None,
            subtype_comparison=None,
            resolved_coverage_codes=result.resolved_coverage_codes,
            primary_coverage_code=None,
            primary_coverage_name=None,
            related_coverage_codes=[],
            user_summary=None,
            anchor=None,
            recovery_message=recovery_message,
            coverage_resolution=coverage_resolution,
            debug=merged_debug,
        )

    # ==========================================================================
    # RESOLVED 상태: 전체 데이터 반환
    # ==========================================================================
    anchor_blocked_by_resolution = False  # RESOLVED이므로 anchor 생성 허용

    if should_preserve_anchor and input_anchor:
        # 기존 anchor 유지 (intent도 유지)
        new_anchor = input_anchor
    elif primary_code:
        # 새 anchor 생성 (STEP 3.6: intent 포함)
        coverage_domains = get_coverage_domains()
        new_anchor = QueryAnchor(
            coverage_code=primary_code,
            coverage_name=primary_name,
            domain=coverage_domains.get(primary_code),
            original_query=query,
            intent=resolved_intent,  # STEP 3.6: intent 포함
        )

    return CompareResponseModel(
        resolution_state=resolution_state,
        resolved_coverage_code=resolved_coverage_code,
        compare_axis=[
            CompareAxisItemResponse(
                insurer_code=item.insurer_code,
                coverage_code=item.coverage_code,
                coverage_name=item.coverage_name,
                doc_type_counts=item.doc_type_counts,
                evidence=[_convert_evidence(e) for e in item.evidence],
            )
            for item in result.compare_axis
        ],
        policy_axis=[
            PolicyAxisItemResponse(
                insurer_code=item.insurer_code,
                keyword=item.keyword,
                evidence=[_convert_evidence(e) for e in item.evidence],
            )
            for item in result.policy_axis
        ],
        coverage_compare_result=[
            CoverageCompareRowResponse(
                coverage_code=row.coverage_code,
                coverage_name=row.coverage_name,
                insurers=[
                    InsurerCompareCellResponse(
                        insurer_code=cell.insurer_code,
                        doc_type_counts=cell.doc_type_counts,
                        best_evidence=[_convert_evidence(e) for e in cell.best_evidence],
                    )
                    for cell in row.insurers
                ],
            )
            for row in result.coverage_compare_result
        ],
        diff_summary=[
            DiffSummaryItemResponse(
                coverage_code=item.coverage_code,
                coverage_name=item.coverage_name,
                bullets=[
                    DiffBulletResponse(
                        text=bullet.text,
                        evidence_refs=[
                            EvidenceRefResponse(
                                insurer_code=ref.insurer_code,
                                document_id=ref.document_id,
                                page_start=ref.page_start,
                            )
                            for ref in bullet.evidence_refs
                        ],
                    )
                    for bullet in item.bullets
                ],
            )
            for item in result.diff_summary
        ],
        # U-4.8: Comparison Slots
        slots=converted_slots,
        # STEP 4.1: Subtype Comparison
        subtype_comparison=subtype_comparison,
        # resolved_coverage_codes: top-level 승격
        resolved_coverage_codes=result.resolved_coverage_codes,
        # STEP 2.5: 대표 담보 / 연관 담보 / 사용자 요약
        primary_coverage_code=primary_code,
        primary_coverage_name=primary_name,
        related_coverage_codes=related_codes,
        user_summary=user_summary,
        # STEP 2.9: Query Anchor
        anchor=new_anchor,
        # STEP 3.5: Insurer Auto-Recovery 메시지
        recovery_message=recovery_message,
        # STEP 3.7: Coverage Resolution
        coverage_resolution=coverage_resolution,
        debug=merged_debug,
    )


@router.post("/compare", response_model=CompareResponseModel)
async def compare_insurers(request: CompareRequest) -> CompareResponseModel:
    """
    2-Phase Retrieval 비교 검색

    - **compare_axis**: 가입설계서/상품요약서/사업방법서에서 coverage_code 기반 근거 수집
    - **policy_axis**: 약관에서 키워드 기반 조문 근거 수집 (A2 정책)

    STEP 2.9: Query Anchor
    - anchor가 있는 경우, insurer-only 후속 질의인지 판별
    - insurer-only면 anchor.coverage_code 사용
    - 아니면 신규 질의로 처리

    STEP 3.6: Intent Locking
    - intent(lookup/compare)는 명시적 신호가 있을 때만 변경
    - UI 이벤트로 인한 intent 변경 금지
    - coverage/insurer 변경은 intent 변경 사유가 아님
    """
    try:
        # STEP 2.6: Insurer Scope 결정 (룰 기반, LLM 미사용)
        # STEP 3.5: Auto-Recovery 적용 - 빈 insurers도 처리됨
        final_insurers, insurer_scope_debug = _resolve_insurer_scope(
            request_insurers=request.insurers,
            query=request.query,
        )

        # Query에서 추출된 insurers (intent 판단용)
        query_insurers = insurer_scope_debug.get("query_extracted_insurers", [])

        # STEP 3.6: Intent Locking - 최종 intent 결정
        resolved_intent, intent_debug = _resolve_intent(
            query=request.query,
            anchor=request.anchor,
            ui_event_type=request.ui_event_type,
            query_insurers=query_insurers,
        )

        # STEP 3.5: Recovery 메시지 생성
        recovery_message: str | None = None
        if insurer_scope_debug.get("recovery_applied"):
            recovery_messages = get_recovery_messages()
            # 질의에서 보험사 추출된 경우
            if insurer_scope_debug.get("query_extracted_insurers"):
                display_names = get_display_names()
                insurer_display = display_names.get("insurer_names", {})
                insurer_names = [
                    insurer_display.get(ic, ic)
                    for ic in insurer_scope_debug["query_extracted_insurers"]
                ]
                recovery_message = recovery_messages.get(
                    "no_insurer_extracted", ""
                ).format(insurers=", ".join(insurer_names))
            else:
                # 기본 정책 적용
                recovery_message = recovery_messages.get("no_insurer_default", "")

        # STEP 2.9: Query Anchor 기반 후속 질의 판별
        query_type, anchor_debug = _detect_follow_up_query_type(
            query=request.query,
            anchor=request.anchor,
        )
        anchor_debug["query_type"] = query_type

        # STEP 3.9 + 4.5: locked_coverage_code(s) 우선 적용
        # locked_coverage_codes 또는 locked_coverage_code가 있으면 coverage resolver를 완전히 스킵
        coverage_codes_to_use = request.coverage_codes
        is_coverage_locked = False

        # STEP 4.5: locked_coverage_codes (복수) 우선, 없으면 locked_coverage_code (단일) 사용
        effective_locked_codes: list[str] | None = None
        if request.locked_coverage_codes and len(request.locked_coverage_codes) > 0:
            effective_locked_codes = request.locked_coverage_codes
        elif request.locked_coverage_code:
            effective_locked_codes = [request.locked_coverage_code]

        if effective_locked_codes:
            # STEP 4.5: 담보 고정 - resolver 스킵
            coverage_codes_to_use = effective_locked_codes
            anchor_debug["locked_coverage_codes"] = effective_locked_codes
            anchor_debug["coverage_locked"] = True
            is_coverage_locked = True
        elif query_type == "insurer_only" and request.anchor:
            # insurer-only 후속 질의인 경우, anchor의 coverage_code 사용
            coverage_codes_to_use = [request.anchor.coverage_code]
            anchor_debug["restored_from_anchor"] = True
            anchor_debug["anchor_coverage_code"] = request.anchor.coverage_code

        result = compare(
            insurers=final_insurers,  # STEP 2.6: resolved insurers 사용
            query=request.query,
            coverage_codes=coverage_codes_to_use,  # STEP 2.9: anchor에서 복원된 코드 사용
            top_k_per_insurer=request.top_k_per_insurer,
            compare_doc_types=request.compare_doc_types,
            policy_doc_types=request.policy_doc_types,
            policy_keywords=request.policy_keywords,
            age=request.age,
            gender=request.gender,
            # STEP 4.7: locked_coverage_codes 전달 (fallback 시 coverage_code 정체성 유지)
            locked_coverage_codes=effective_locked_codes,
        )

        # =======================================================================
        # STEP 4.1: 멀티 Subtype 감지 (Resolution 평가보다 먼저!)
        # =======================================================================
        is_multi_subtype = is_multi_subtype_query(request.query)
        extracted_subtypes = extract_subtypes_from_query(request.query) if is_multi_subtype else []

        # STEP 3.7: Coverage Resolution 평가
        # STEP 3.9: locked_coverage_code, insurer-only 후속 질의, explicit coverage_codes가 제공된 경우 평가 스킵
        # STEP 4.1: 멀티 Subtype인 경우 SUBTYPE_MULTI 상태 강제 (Resolution Lock 금지)
        coverage_resolution: CoverageResolutionResponse | None = None
        resolution_debug: dict[str, Any] | None = None

        if is_multi_subtype:
            # STEP 4.1: 멀티 Subtype 입력 - Resolution Lock 금지
            # similarity gap 기반 RESOLVED, perfect_match 기반 RESOLVED 모두 금지
            coverage_resolution = CoverageResolutionResponse(
                status="SUBTYPE_MULTI",
                resolved_coverage_code=None,  # 단일 coverage_code 확정 금지
                message=None,
                suggested_coverages=[],
                detected_domain="CANCER",  # 경계성종양/제자리암은 암 계열
            )
            resolution_debug = {
                "status": "SUBTYPE_MULTI",
                "reason": "multi_subtype_detected",
                "subtypes": [s.code for s in extracted_subtypes],
                "subtype_names": [s.name for s in extracted_subtypes],
                "resolution_lock_blocked": True,
            }
        elif is_coverage_locked:
            # STEP 3.9: 담보가 고정된 경우 resolution 평가 완전 스킵
            resolution_debug = {"skipped": True, "reason": "coverage_locked"}
        elif query_type != "insurer_only" and not request.coverage_codes:
            # 자동 추론된 경우에만 resolution 평가
            coverage_recommendations = result.debug.get("recommended_coverage_details", [])

            coverage_resolution, resolution_debug = _evaluate_coverage_resolution(
                query=request.query,
                resolved_coverage_codes=result.resolved_coverage_codes,
                coverage_recommendations=coverage_recommendations,
            )

        # STEP 4.1: Subtype Comparison 추출 (다중 subtype 질의인 경우)
        subtype_comparison_resp: SubtypeComparisonResponse | None = None
        if is_multi_subtype:
            # Evidence를 보험사별로 그룹화
            evidence_by_insurer: dict[str, list] = {ic: [] for ic in final_insurers}
            for item in result.compare_axis:
                if item.insurer_code in evidence_by_insurer:
                    evidence_by_insurer[item.insurer_code].extend(item.evidence)
            for item in result.policy_axis:
                if item.insurer_code in evidence_by_insurer:
                    evidence_by_insurer[item.insurer_code].extend(item.evidence)

            # Subtype 비교 추출
            subtype_result = extract_subtype_comparison(
                query=request.query,
                evidence_by_insurer=evidence_by_insurer,
                insurers=final_insurers,
            )

            # 결과를 API 응답 모델로 변환
            subtype_comparison_resp = SubtypeComparisonResponse(
                subtypes=subtype_result.subtypes,
                comparison_items=[
                    SubtypeComparisonItemResponse(
                        subtype_code=item.subtype_code,
                        subtype_name=item.subtype_name,
                        info_type=item.info_type,
                        info_label=item.info_label,
                        insurer_code=item.insurer_code,
                        value=item.value,
                        confidence=item.confidence,
                        evidence_ref=item.evidence_ref,
                    )
                    for item in subtype_result.comparison_items
                ],
                is_multi_subtype=subtype_result.is_multi_subtype,
            )

        return _convert_response(
            result,
            final_insurers,
            request.query,
            insurer_scope_debug,
            anchor_debug=anchor_debug,
            input_anchor=request.anchor,
            recovery_message=recovery_message,
            # STEP 3.6: Intent 전달
            resolved_intent=resolved_intent,
            intent_debug=intent_debug,
            # STEP 3.7: Coverage Resolution
            coverage_resolution=coverage_resolution,
            resolution_debug=resolution_debug,
            # STEP 4.1: Subtype Comparison
            subtype_comparison=subtype_comparison_resp,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
