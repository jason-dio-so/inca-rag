"""
Compare API Router

POST /compare - 2-Phase Retrieval 비교 검색
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.retrieval.compare_service import compare, CompareResponse
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
)

router = APIRouter(tags=["compare"])


# =============================================================================
# STEP 2.9: Query Anchor Model
# =============================================================================

class QueryAnchor(BaseModel):
    """
    Query Anchor - 대화형 질의에서 기준 담보와 의도를 유지

    세션 단위로 유지되며, 후속 질의에서 담보 컨텍스트 유지에 사용됨
    """
    coverage_code: str = Field(..., description="대표 담보 코드")
    coverage_name: str | None = Field(None, description="대표 담보 명칭")
    domain: str | None = Field(None, description="담보 도메인 (CANCER, CARDIO 등)")
    original_query: str = Field(..., description="anchor 생성 시점의 원본 질의")


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


class CompareResponseModel(BaseModel):
    """비교 검색 응답"""
    compare_axis: list[CompareAxisItemResponse]
    policy_axis: list[PolicyAxisItemResponse]
    coverage_compare_result: list[CoverageCompareRowResponse]
    diff_summary: list[DiffSummaryItemResponse]
    # U-4.8: Comparison Slots
    slots: list[ComparisonSlotResponse] = []
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

    # STEP 2.9: 새 anchor 생성
    # insurer_only 후속 질의인 경우 기존 anchor 유지, 아닌 경우 새 anchor 생성
    new_anchor: QueryAnchor | None = None
    if anchor_debug and anchor_debug.get("query_type") == "insurer_only" and input_anchor:
        # 기존 anchor 유지
        new_anchor = input_anchor
    elif primary_code:
        # 새 anchor 생성
        coverage_domains = get_coverage_domains()
        new_anchor = QueryAnchor(
            coverage_code=primary_code,
            coverage_name=primary_name,
            domain=coverage_domains.get(primary_code),
            original_query=query,
        )

    return CompareResponseModel(
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
    """
    try:
        # STEP 2.6: Insurer Scope 결정 (룰 기반, LLM 미사용)
        # STEP 3.5: Auto-Recovery 적용 - 빈 insurers도 처리됨
        final_insurers, insurer_scope_debug = _resolve_insurer_scope(
            request_insurers=request.insurers,
            query=request.query,
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

        # insurer-only 후속 질의인 경우, anchor의 coverage_code 사용
        coverage_codes_to_use = request.coverage_codes
        if query_type == "insurer_only" and request.anchor:
            # anchor에서 coverage_code 복원
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
        )
        return _convert_response(
            result,
            final_insurers,
            request.query,
            insurer_scope_debug,
            anchor_debug=anchor_debug,
            input_anchor=request.anchor,
            recovery_message=recovery_message,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
