"""
Compare Service - 2-Phase Retrieval for Insurance Document Comparison

compare_axis: 가입설계서/상품요약서/사업방법서에서 coverage_code 기반 검색
policy_axis: 약관에서 키워드 기반 검색 (A2 정책: 약관은 비교축에 섞지 않음)
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import psycopg
import yaml
from psycopg.rows import dict_row

from services.extraction.amount_extractor import extract_amount, AmountExtract
from services.extraction.condition_extractor import extract_condition_snippet, ConditionExtract
from services.extraction.llm_client import (
    LLMClient,
    DisabledLLMClient,
    is_llm_enabled,
    get_llm_max_calls_per_request,
    validate_span_in_text,
)
from services.extraction.llm_prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    has_amount_intent,
)
from services.extraction.llm_schemas import LLMExtractResult
from services.extraction.slot_extractor import extract_slots
from services.retrieval.plan_selector import (
    select_plans_for_insurers,
    get_plan_ids_for_retrieval,
    SelectedPlan,
)
from api.config_loader import (
    get_policy_keyword_patterns,
    get_default_policy_keywords,
    get_doc_type_priority,
    get_slot_search_keywords,
    get_coverage_code_groups,
)


# =============================================================================
# STEP 2.8: P0 하드코딩 외부화
# 아래 상수들은 config 파일로 이전됨:
# - POLICY_KEYWORD_PATTERNS → config/mappings/policy_keyword_patterns.yaml
# - DOC_TYPE_PRIORITY → config/rules/doc_type_priority.yaml
# - SLOT_SEARCH_KEYWORDS → config/mappings/slot_search_keywords.yaml
# - CANCER/CEREBRO/SURGERY_COVERAGE_CODES → config/mappings/coverage_code_groups.yaml
# =============================================================================

# LEGACY: policy_keywords 자동 추출을 위한 키워드 매핑 (하위 호환성)
# 정규화: 다양한 표현 → 검색용 키워드
POLICY_KEYWORD_PATTERNS: dict[str, str] = {
    # 암진단비 관련
    "경계성종양": "경계성",
    "경계성": "경계성",
    "유사암": "유사암",
    "제자리암": "제자리암",
    "상피내암": "제자리암",  # 상피내암 → 제자리암으로 정규화
    "갑상선암": "유사암",    # 갑상선암 → 유사암으로 정규화
    "암진단비": "암진단",
    "암 진단비": "암진단",
    # U-4.13: 뇌/심혈관 진단비 관련
    "뇌졸중": "뇌졸중",
    "뇌졸중진단비": "뇌졸중",
    "급성심근경색": "급성심근경색",
    "급성심근경색진단비": "급성심근경색",
    "뇌혈관질환": "뇌혈관",
    "뇌혈관": "뇌혈관",
    "허혈성심장질환": "허혈성심장",
    "허혈성심장": "허혈성심장",
    "뇌출혈": "뇌출혈",
    # U-4.13: 수술비 관련
    "수술비": "수술비",
    "수술급여": "수술비",
    "수술보험금": "수술비",
    "1~5종수술": "종수술",
    "종수술": "종수술",
}

# 기본 policy_keywords (아무것도 못 찾았을 때)
DEFAULT_POLICY_KEYWORDS = ["경계성", "유사암", "제자리암"]

# U-4.13: Coverage type별 기본 키워드
CEREBRO_CARDIOVASCULAR_KEYWORDS = ["뇌졸중", "급성심근경색", "뇌혈관", "허혈성심장"]
SURGERY_BENEFIT_KEYWORDS = ["수술비", "종수술", "수술"]

# source_doc_type 우선순위 가중치 (높을수록 우선)
DOC_TYPE_PRIORITY = {
    "가입설계서": 3,
    "상품요약서": 2,
    "사업방법서": 1,
}

# =============================================================================
# Step K: Hybrid Search 옵션
# =============================================================================

def is_hybrid_enabled() -> bool:
    """COMPARE_AXIS_HYBRID 환경변수 확인"""
    return os.environ.get("COMPARE_AXIS_HYBRID", "0") == "1"


def get_hybrid_ef_search() -> int:
    """HNSW ef_search 파라미터 (기본: 40)"""
    return int(os.environ.get("COMPARE_AXIS_EF_SEARCH", "40"))


def get_hybrid_vector_top_k() -> int:
    """벡터 검색 top_k (기본: 20)"""
    return int(os.environ.get("COMPARE_AXIS_VECTOR_TOP_K", "20"))


_logger = logging.getLogger(__name__)

# ============================================================================
# Query Normalization (헌법 준수: 설정 파일에서만 규칙 로드)
# ============================================================================

_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _load_insurer_aliases() -> list[str]:
    """
    insurer_alias.yaml에서 모든 보험사 alias 로드 (긴 것부터 정렬)

    헌법 준수: 하드코딩 fallback 금지. 설정 파일이 SSOT.
    로드 실패 시 빈 리스트 반환 + 경고 로그.
    """
    config_path = _CONFIG_DIR / "mappings" / "insurer_alias.yaml"
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            # 모든 key (alias)를 가져와서 긴 것부터 정렬 (greedy match)
            aliases = list(data.keys())
            aliases.sort(key=lambda x: len(x), reverse=True)
            return aliases
    except FileNotFoundError:
        _logger.error(f"[CRITICAL] insurer_alias.yaml not found: {config_path}")
        return []
    except Exception as e:
        _logger.error(f"[CRITICAL] Failed to load insurer_alias.yaml: {e}")
        return []


def _load_normalization_rules() -> dict:
    """
    query_normalization.yaml에서 정규화 규칙 로드

    헌법 준수: 하드코딩 금지. 설정 파일이 SSOT.
    """
    config_path = _CONFIG_DIR / "rules" / "query_normalization.yaml"
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        _logger.error(f"[CRITICAL] query_normalization.yaml not found: {config_path}")
        return {}
    except Exception as e:
        _logger.error(f"[CRITICAL] Failed to load query_normalization.yaml: {e}")
        return {}


# 모듈 로드 시 한 번만 로드 (캐시)
_INSURER_ALIASES: list[str] | None = None
_NORMALIZATION_RULES: dict | None = None


def _get_insurer_aliases() -> list[str]:
    """캐시된 보험사 alias 리스트 반환"""
    global _INSURER_ALIASES
    if _INSURER_ALIASES is None:
        _INSURER_ALIASES = _load_insurer_aliases()
    return _INSURER_ALIASES


def _get_normalization_rules() -> dict:
    """캐시된 정규화 규칙 반환"""
    global _NORMALIZATION_RULES
    if _NORMALIZATION_RULES is None:
        _NORMALIZATION_RULES = _load_normalization_rules()
    return _NORMALIZATION_RULES


def normalize_query_for_coverage(query: str) -> str:
    """
    coverage 추천을 위한 query 정규화

    헌법 준수: 모든 규칙은 config/rules/query_normalization.yaml에서 로드
    - 보험사명 제거 (config/mappings/insurer_alias.yaml)
    - 질의 의도 표현 제거
    - 공백 제거
    - 특수문자 제거
    """
    rules = _get_normalization_rules()
    normalized = query

    # 1. 보험사명/alias 제거 (긴 것부터 제거하여 부분 매칭 방지)
    for alias in _get_insurer_aliases():
        normalized = normalized.replace(alias, "")

    # 2. 중간 조사 제거 (보험사명 제거 후 남은 조사)
    intermediate = rules.get("intermediate_particles", {})
    if boundary_pattern := intermediate.get("boundary_pattern"):
        normalized = re.sub(boundary_pattern, "", normalized)
    if conjunction_pattern := intermediate.get("conjunction_pattern"):
        normalized = re.sub(conjunction_pattern, "", normalized)

    # 3. 공백 제거
    if rules.get("options", {}).get("strip_whitespace", True):
        normalized = normalized.replace(" ", "")

    # 4. 질의 의도 표현 제거 (긴 것부터)
    intent_suffixes = rules.get("intent_suffixes", [])
    for suffix in intent_suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            break

    # 5. 끝에 남은 조사 제거
    if trailing_pattern := rules.get("trailing_particles_pattern"):
        normalized = re.sub(trailing_pattern, "", normalized)

    # 6. 특수문자 제거
    if punctuation_pattern := rules.get("punctuation_pattern"):
        normalized = re.sub(punctuation_pattern, "", normalized)

    return normalized


@dataclass
class CoverageRecommendation:
    """coverage_code 추천 결과 (U-5.0-A: confidence 추가)"""
    insurer_code: str
    coverage_code: str
    coverage_name: str | None
    raw_name: str
    source_doc_type: str
    similarity: float
    # U-5.0-A: 매핑 신뢰도 (테이블 기반)
    confidence: float = 0.8
    semantic_scope: str = "UNKNOWN"
    # U-5.0-A: Combined score (similarity * confidence)
    combined_score: float = 0.0


def recommend_coverage_codes(
    conn: psycopg.Connection,
    insurers: list[str],
    query: str,
    top_n_per_insurer: int = 3,
    min_similarity: float = 0.1,
) -> tuple[list[str], list[CoverageRecommendation]]:
    """
    query 기반 coverage_codes 자동 추천

    Args:
        conn: DB 연결
        insurers: 보험사 코드 리스트
        query: 사용자 질의
        top_n_per_insurer: 보험사별 추천 개수
        min_similarity: 최소 유사도 임계값

    Returns:
        (추천 coverage_codes 리스트, 상세 추천 결과)
    """
    q_norm = normalize_query_for_coverage(query)

    if not q_norm:
        return [], []

    recommendations: list[CoverageRecommendation] = []

    with conn.cursor() as cur:
        # 보험사별로 추천 (쏠림 방지)
        for insurer_code in insurers:
            # U-5.0-A: pg_trgm similarity * confidence 기반 검색
            # source_doc_type 우선순위 적용 (가입설계서 > 상품요약서 > 사업방법서)
            query_sql = """
                WITH ranked AS (
                    SELECT
                        i.insurer_code,
                        ca.coverage_code,
                        cs.coverage_name,
                        ca.raw_name,
                        ca.source_doc_type,
                        similarity(ca.raw_name_norm, %s) AS sim,
                        -- U-5.0-A: confidence 및 semantic_scope 추가
                        COALESCE(ca.confidence, 0.8) AS confidence,
                        COALESCE(cs.semantic_scope, 'UNKNOWN') AS semantic_scope,
                        -- U-5.0-A: combined score = similarity * confidence
                        similarity(ca.raw_name_norm, %s) * COALESCE(ca.confidence, 0.8) AS combined_score,
                        CASE ca.source_doc_type
                            WHEN '가입설계서' THEN 3
                            WHEN '상품요약서' THEN 2
                            WHEN '사업방법서' THEN 1
                            ELSE 0
                        END AS doc_priority,
                        ROW_NUMBER() OVER (
                            PARTITION BY ca.coverage_code
                            ORDER BY
                                -- U-5.0-A: combined score 우선 정렬
                                similarity(ca.raw_name_norm, %s) * COALESCE(ca.confidence, 0.8) DESC,
                                CASE ca.source_doc_type
                                    WHEN '가입설계서' THEN 3
                                    WHEN '상품요약서' THEN 2
                                    WHEN '사업방법서' THEN 1
                                    ELSE 0
                                END DESC
                        ) AS rn
                    FROM coverage_alias ca
                    JOIN insurer i ON ca.insurer_id = i.insurer_id
                    LEFT JOIN coverage_standard cs ON cs.coverage_code = ca.coverage_code
                    WHERE i.insurer_code = %s
                      AND similarity(ca.raw_name_norm, %s) >= %s
                )
                SELECT insurer_code, coverage_code, coverage_name, raw_name, source_doc_type,
                       sim, confidence, semantic_scope, combined_score
                FROM ranked
                WHERE rn = 1
                ORDER BY combined_score DESC, doc_priority DESC
                LIMIT %s
            """
            cur.execute(
                query_sql,
                (q_norm, q_norm, q_norm, insurer_code, q_norm, min_similarity, top_n_per_insurer),
            )
            rows = cur.fetchall()

            for row in rows:
                recommendations.append(
                    CoverageRecommendation(
                        insurer_code=row["insurer_code"],
                        coverage_code=row["coverage_code"],
                        coverage_name=row["coverage_name"],
                        raw_name=row["raw_name"],
                        source_doc_type=row["source_doc_type"],
                        similarity=float(row["sim"]),
                        # U-5.0-A: 테이블 기반 필드
                        confidence=float(row["confidence"]),
                        semantic_scope=row["semantic_scope"],
                        combined_score=float(row["combined_score"]),
                    )
                )

    # 중복 제거하여 coverage_codes 목록 생성
    coverage_codes = list(dict.fromkeys(r.coverage_code for r in recommendations))

    return coverage_codes, recommendations


def extract_policy_keywords(query: str, coverage_type: str | None = None) -> list[str]:
    """
    query에서 policy_keywords를 자동 추출 (U-4.13: coverage_type 지원)

    규칙:
    - 매칭된 토큰을 정규화하여 반환
    - 하나도 못 찾으면 coverage_type에 맞는 기본값 반환

    Args:
        query: 사용자 질의
        coverage_type: 담보 유형 (cancer_diagnosis, cerebro_cardiovascular_diagnosis, surgery_benefit)

    Returns:
        추출된 키워드 리스트 (중복 제거)
    """
    found_keywords: set[str] = set()

    # STEP 2.8: config에서 패턴 로드
    policy_keyword_patterns = get_policy_keyword_patterns()

    # 긴 패턴부터 매칭 (경계성종양 → 경계성)
    for pattern, normalized in sorted(
        policy_keyword_patterns.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        if pattern in query:
            found_keywords.add(normalized)

    if not found_keywords:
        # U-4.13: Coverage type별 기본 키워드 (STEP 2.8: config에서 로드)
        slot_keywords = get_slot_search_keywords()
        if coverage_type == "cerebro_cardiovascular_diagnosis":
            return list(slot_keywords.get("cerebro_cardiovascular_default", CEREBRO_CARDIOVASCULAR_KEYWORDS))
        elif coverage_type == "surgery_benefit":
            return list(slot_keywords.get("surgery_benefit_default", SURGERY_BENEFIT_KEYWORDS))
        return get_default_policy_keywords()

    return list(found_keywords)


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


@dataclass
class AmountInfo:
    """금액 정보 (API 응답용)"""
    amount_value: int | None
    amount_text: str | None
    unit: str | None
    confidence: str
    method: str


@dataclass
class ConditionInfo:
    """지급조건 정보 (API 응답용)"""
    snippet: str | None
    matched_terms: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    """검색 결과 근거"""
    document_id: int
    doc_type: str
    page_start: int | None
    preview: str
    score: float = 0.0
    amount: AmountInfo | None = None
    condition_snippet: ConditionInfo | None = None


@dataclass
class CompareAxisResult:
    """Compare Axis 결과 (담보 기준)"""
    insurer_code: str
    coverage_code: str
    coverage_name: str | None
    doc_type_counts: dict[str, int] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class PolicyAxisResult:
    """Policy Axis 결과 (약관 키워드 기준)"""
    insurer_code: str
    keyword: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ResolvedAmount:
    """대표 금액 (amount_source_priority 정책으로 선택된 금액)"""
    amount_value: int | None
    amount_text: str | None
    unit: str | None
    confidence: str
    source_doc_type: str | None  # 금액이 선택된 doc_type
    source_document_id: int | None = None


@dataclass
class InsurerCompareCell:
    """비교표 셀: 보험사별 결과"""
    insurer_code: str
    doc_type_counts: dict[str, int] = field(default_factory=dict)
    best_evidence: list[Evidence] = field(default_factory=list)
    resolved_amount: ResolvedAmount | None = None  # H-1.8: 대표 금액
    # U-4.17: 비교 가능 상태 ("COMPARABLE" | "NO_COMPARABLE_EVIDENCE")
    compare_status: str = "COMPARABLE"
    # U-4.18: Source Level ("COMPARABLE_DOC" | "POLICY_ONLY" | "UNKNOWN")
    # - COMPARABLE_DOC: 가입설계서/상품요약서/사업방법서 기반
    # - POLICY_ONLY: 약관 단독
    # - UNKNOWN: evidence 부족
    source_level: str = "UNKNOWN"


@dataclass
class CoverageCompareRow:
    """비교표 행: coverage_code 기준"""
    coverage_code: str
    coverage_name: str | None
    insurers: list[InsurerCompareCell] = field(default_factory=list)


@dataclass
class EvidenceRef:
    """근거 참조"""
    insurer_code: str
    document_id: int
    page_start: int | None


@dataclass
class DiffBullet:
    """차이점 문장"""
    text: str
    evidence_refs: list[EvidenceRef] = field(default_factory=list)


@dataclass
class DiffSummaryItem:
    """coverage_code별 차이점 요약"""
    coverage_code: str
    coverage_name: str | None
    bullets: list[DiffBullet] = field(default_factory=list)


@dataclass
class CompareResponse:
    """Compare API 응답"""
    compare_axis: list[CompareAxisResult] = field(default_factory=list)
    policy_axis: list[PolicyAxisResult] = field(default_factory=list)
    coverage_compare_result: list[CoverageCompareRow] = field(default_factory=list)
    diff_summary: list[DiffSummaryItem] = field(default_factory=list)
    # U-4.8: Comparison Slots
    slots: list = field(default_factory=list)
    # resolved_coverage_codes: 질의에서 자동 추론된 coverage_code 목록 (top-level 승격)
    resolved_coverage_codes: list[str] | None = None
    debug: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Step K: Hybrid Vector Search
# =============================================================================

def get_compare_axis_vector(
    conn: psycopg.Connection,
    insurers: list[str],
    compare_doc_types: list[str],
    query_embedding: list[float],
    top_k_per_insurer: int = 10,
    plan_ids: dict[str, int | None] | None = None,
    ef_search: int = 40,
) -> tuple[list[CompareAxisResult], dict[str, int]]:
    """
    Step K: 벡터 검색 기반 Compare Axis 검색 (Hybrid fallback용)

    Args:
        conn: DB 연결
        insurers: 보험사 코드 리스트
        compare_doc_types: 검색 대상 doc_type 리스트
        query_embedding: 질의 임베딩 벡터
        top_k_per_insurer: 보험사별 최대 결과 수
        plan_ids: 보험사별 plan_id 매핑
        ef_search: HNSW ef_search 파라미터

    Returns:
        (결과 리스트, 보험사별 건수)
    """
    results: dict[str, CompareAxisResult] = {}
    insurer_counts: dict[str, int] = {}

    with conn.cursor() as cur:
        # HNSW ef_search 설정
        cur.execute(f"SET LOCAL hnsw.ef_search = {ef_search}")

        for insurer_code in insurers:
            # plan_id 조건 생성
            plan_id = plan_ids.get(insurer_code) if plan_ids else None
            if plan_id is not None:
                plan_condition = "(c.plan_id = %s OR c.plan_id IS NULL)"
                plan_params = (plan_id,)
            else:
                plan_condition = "c.plan_id IS NULL"
                plan_params = ()

            # 벡터 검색 쿼리
            query = f"""
                SELECT
                    c.chunk_id,
                    c.document_id,
                    c.doc_type,
                    c.page_start,
                    LEFT(c.content, 150) AS preview,
                    c.content,
                    c.meta->'entities'->>'coverage_code' AS coverage_code,
                    c.meta->'entities'->>'coverage_name' AS coverage_name,
                    i.insurer_code,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunk c
                JOIN insurer i ON c.insurer_id = i.insurer_id
                WHERE i.insurer_code = %s
                  AND c.doc_type = ANY(%s::text[])
                  AND c.embedding IS NOT NULL
                  AND {plan_condition}
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """

            params = (
                query_embedding,
                insurer_code,
                compare_doc_types,
            ) + plan_params + (query_embedding, top_k_per_insurer)

            cur.execute(query, params)
            rows = cur.fetchall()

            count = 0
            for row in rows:
                evidence = CompareEvidence(
                    chunk_id=row[0],
                    document_id=row[1],
                    doc_type=row[2],
                    page_start=row[3],
                    preview=row[4],
                    content=row[5],
                    coverage_code=row[6],
                    coverage_name=row[7],
                    similarity=row[9],
                )

                key = insurer_code
                if key not in results:
                    results[key] = CompareAxisResult(
                        insurer_code=insurer_code,
                        evidence=[],
                    )

                results[key].evidence.append(evidence)
                count += 1

            insurer_counts[insurer_code] = count

    return list(results.values()), insurer_counts


# =============================================================================
# 2-Pass Retrieval Configuration (범용화)
# =============================================================================

# 2-pass retrieval 설정 상수
RETRIEVAL_CONFIG = {
    "preview_len": int(os.environ.get("RETRIEVAL_PREVIEW_LEN", "1000")),
    "top_k_pass1": int(os.environ.get("RETRIEVAL_TOP_K_PASS1", "10")),
    "top_k_pass2": int(os.environ.get("RETRIEVAL_TOP_K_PASS2", "5")),
}

# Slot별 검색 키워드 레지스트리 (범용화)
SLOT_SEARCH_KEYWORDS = {
    # 진단비 일시금 (암진단비, 뇌졸중 등에 공통 사용 가능)
    "diagnosis_lump_sum": [
        "진단비",
        "진단보험금",
        "진단 확정",
        "진단확정",
        "가입금액 지급",
        "가입금액지급",
        "최초 1회",
        "최초1회",
        "보험가입금액",
    ],
    # 암 진단비 전용 (상위 호환)
    "cancer_diagnosis": [
        "암 진단비",
        "암진단비",
        "유사암",
        "악성신생물",
    ],
    # 뇌/심혈관 진단비 전용 (U-4.15 수정: 복합 키워드만 사용하여 정밀도 향상)
    # "뇌졸중" 단독 사용 시 "뇌졸중통원일당" 등과 매칭되므로 "진단비" 포함 복합어만 사용
    "cerebro_cardiovascular": [
        "뇌졸중진단비",
        "뇌출혈진단비",
        "뇌혈관질환진단비",
        "급성심근경색증진단비",
        "급성심근경색진단비",
        "허혈성심장질환진단비",
        "심장질환진단비",
        "중대뇌혈관질환진단비",
        "중대심장질환진단비",
    ],
    # 수술비 (향후 확장용)
    "surgery_benefit": [
        "수술비",
        "수술급여",
        "수술 시",
    ],
    # 입원일당 (향후 확장용)
    "hospitalization_daily": [
        "입원일당",
        "입원 1일당",
        "일당",
    ],
    # U-4.16: 다빈치/로봇 수술 키워드
    "surgery_method": [
        "다빈치",
        "da vinci",
        "로봇수술",
        "로봇 수술",
        "robot",
        "복강경",
    ],
    # U-4.16: 암 subtype (경계성종양/제자리암) 키워드
    "cancer_subtype": [
        "제자리암",
        "상피내암",
        "경계성종양",
        "경계성 종양",
        "유사암",
        "기타피부암",
        "갑상선암",
        "대장점막내암",
    ],
}

# 하위 호환성을 위한 alias
LUMP_SUM_SEARCH_KEYWORDS = (
    SLOT_SEARCH_KEYWORDS["diagnosis_lump_sum"] +
    SLOT_SEARCH_KEYWORDS["cancer_diagnosis"]
)

# U-4.15: coverage_codes → slot_type 매핑 (2-pass retrieval용)
# STEP 2.8: config로 외부화됨 → config/mappings/coverage_code_groups.yaml
# 하위 호환성을 위해 legacy 상수 유지
CANCER_COVERAGE_CODES = {"A4200_1", "A4210", "A4209", "A4299_1"}
CEREBRO_CARDIOVASCULAR_CODES = {"A4101", "A4102", "A4103", "A4104_1", "A4105"}
SURGERY_COVERAGE_CODES = {"A5100", "A5104_1", "A5107_1", "A5200", "A5298_001", "A5300", "A9630_1"}


def determine_slot_type_from_codes(coverage_codes: list[str] | None) -> str:
    """
    coverage_codes에서 2-pass retrieval용 slot_type 결정 (U-4.15)

    Returns:
        slot_type: "cancer_diagnosis", "cerebro_cardiovascular", "surgery_benefit", or "diagnosis_lump_sum"
    """
    if not coverage_codes:
        return "diagnosis_lump_sum"

    code_set = set(coverage_codes)

    # STEP 2.8: config에서 coverage code 그룹 로드
    code_groups = get_coverage_code_groups()
    cerebro_codes = set(code_groups.get("cerebro_cardiovascular", []))
    cancer_codes = set(code_groups.get("cancer", []))
    surgery_codes = set(code_groups.get("surgery", []))

    # 우선순위: cancer > cerebro > surgery (cancer가 가장 빈번한 쿼리)
    if code_set & cancer_codes:
        return "cancer_diagnosis"
    if code_set & cerebro_codes:
        return "cerebro_cardiovascular"
    if code_set & surgery_codes:
        return "surgery_benefit"

    return "diagnosis_lump_sum"


def get_amount_bearing_evidence(
    conn: psycopg.Connection,
    insurer_code: str,
    compare_doc_types: list[str],
    plan_id: int | None = None,
    top_k: int | None = None,
    slot_type: str = "diagnosis_lump_sum",  # 범용화: slot_type 인자 추가
    target_keyword: str | None = None,  # U-4.15: 우선 검색 키워드 (예: "뇌졸중진단비")
) -> list[Evidence]:
    """
    2-Pass Retrieval: 금액을 포함한 chunk를 검색 (범용화)

    일반 coverage_code 기반 검색으로 금액을 찾지 못한 경우 fallback으로 사용.
    slot_type에 따라 적절한 키워드 세트를 사용.

    Args:
        conn: DB 연결
        insurer_code: 보험사 코드
        compare_doc_types: 검색 대상 doc_type 리스트
        plan_id: plan_id (있으면 plan_id 또는 NULL, 없으면 NULL만)
        top_k: 최대 결과 수 (None이면 RETRIEVAL_CONFIG 사용)
        slot_type: 검색할 슬롯 타입 (diagnosis_lump_sum, cancer_diagnosis 등)
        target_keyword: 우선 검색 키워드 (있으면 해당 키워드 포함 청크 우선 반환)

    Returns:
        Evidence 리스트
    """
    results: list[Evidence] = []

    # 설정에서 top_k 가져오기
    if top_k is None:
        top_k = RETRIEVAL_CONFIG["top_k_pass2"]

    preview_len = RETRIEVAL_CONFIG["preview_len"]

    # STEP 2.8: slot_type에 따른 키워드 선택 (config에서 로드)
    slot_search_keywords = get_slot_search_keywords()
    search_keywords = slot_search_keywords.get(slot_type, [])
    lump_sum_keywords = slot_search_keywords.get("diagnosis_lump_sum", [])

    # U-4.15: cerebro_cardiovascular는 복합 키워드만 사용 (이미 "진단비" 포함)
    # "뇌졸중진단비", "급성심근경색증진단비" 등 구체적 키워드로 정밀 검색
    if slot_type == "cerebro_cardiovascular":
        # 복합 키워드만 사용 (diagnosis_lump_sum 추가 불필요)
        primary_keywords = search_keywords
    elif slot_type == "cancer_diagnosis":
        # 암은 기존대로 OR 결합
        primary_keywords = search_keywords + lump_sum_keywords
    else:
        # 기타 slot_type
        if not search_keywords:
            search_keywords = LUMP_SUM_SEARCH_KEYWORDS
        primary_keywords = search_keywords

    # Plan condition
    if plan_id is not None:
        plan_condition = "(c.plan_id = %s OR c.plan_id IS NULL)"
        plan_params = (plan_id,)
    else:
        plan_condition = "c.plan_id IS NULL"
        plan_params = ()

    # Build keyword conditions (OR 조건)
    keyword_conditions = " OR ".join("c.content ILIKE %s" for _ in primary_keywords)
    keyword_params = tuple(f"%{kw}%" for kw in primary_keywords)

    # Amount pattern: matches "X,XXX만원" or "X만원" or "X천만원"
    # PostgreSQL regex: digit(s) with optional commas, followed by 만원/천만원
    amount_pattern = r'[0-9][0-9,]*\s*만\s*원'

    # U-4.15: target_keyword가 있으면 해당 키워드+금액 패턴이 가까이 있는 청크 우선
    # 예: "뇌졸중진단비" 뒤에 "1천만원"이 50자 내에 있으면 우선
    if target_keyword:
        # target_keyword + 금액 패턴이 50자 내에 있으면 priority 0 (최우선)
        # target_keyword만 있으면 priority 1
        # 없으면 priority 2
        target_with_amount_pattern = f"{target_keyword}.{{0,50}}[0-9][0-9,]*\\s*[천백]?\\s*만\\s*원"
        target_priority = f"""
            CASE
                WHEN LEFT(c.content, {preview_len}) ~ %s THEN 0
                WHEN LEFT(c.content, {preview_len}) ILIKE %s THEN 1
                ELSE 2
            END
        """
        target_param = (target_with_amount_pattern, f"%{target_keyword}%")
    else:
        target_priority = "(SELECT 0)"  # 모든 청크 동일 우선순위 (상수 서브쿼리로 ORDER BY 무효화)
        target_param = ()

    with conn.cursor() as cur:
        query = f"""
            SELECT
                c.chunk_id,
                c.document_id,
                c.doc_type,
                c.page_start,
                LEFT(c.content, %s) AS preview,
                c.meta->'entities'->>'coverage_code' AS coverage_code
            FROM chunk c
            JOIN insurer i ON c.insurer_id = i.insurer_id
            WHERE i.insurer_code = %s
              AND c.doc_type = ANY(%s::text[])
              AND ({keyword_conditions})
              AND c.content ~ %s
              AND {plan_condition}
            ORDER BY
                {target_priority},
                CASE c.doc_type
                    WHEN '상품요약서' THEN 1
                    WHEN '사업방법서' THEN 2
                    WHEN '가입설계서' THEN 3
                    ELSE 4
                END,
                c.page_start
            LIMIT %s
        """

        params = (
            preview_len,
            insurer_code,
            compare_doc_types,
        ) + keyword_params + (amount_pattern,) + plan_params + target_param + (top_k,)

        cur.execute(query, params)
        rows = cur.fetchall()

        for row in rows:
            preview = row["preview"].replace("\n", " ").strip()

            # U-4.15: target_keyword가 있으면 해당 키워드부터 시작하는 텍스트만 추출
            # 이렇게 하면 추출기가 target_keyword 앞의 관련 없는 금액(암진단비 등)을 선택하는 것을 방지
            if target_keyword and target_keyword in preview:
                idx = preview.find(target_keyword)
                # target_keyword부터 시작, 뒤 150자까지 (keyword + amount + context)
                start = idx
                end = min(len(preview), idx + len(target_keyword) + 150)
                preview = preview[start:end]

            results.append(
                Evidence(
                    document_id=row["document_id"],
                    doc_type=row["doc_type"],
                    page_start=row["page_start"],
                    preview=preview,
                    score=0.0,
                )
            )

    return results


def get_compare_axis(
    conn: psycopg.Connection,
    insurers: list[str],
    compare_doc_types: list[str],
    coverage_codes: list[str] | None = None,
    top_k_per_insurer: int = 10,
    plan_ids: dict[str, int | None] | None = None,
) -> tuple[list[CompareAxisResult], dict[str, int]]:
    """
    Compare Axis 검색: 담보(coverage_code) 기반 근거 수집

    STEP 4.10: coverage_alias 기반 텍스트 매칭으로 확장
    - 기존: chunk.meta->entities->coverage_code 태그 기반 검색
    - 확장: coverage_alias.raw_name을 사용한 content 텍스트 매칭

    Args:
        conn: DB 연결
        insurers: 보험사 코드 리스트
        compare_doc_types: 검색 대상 doc_type 리스트
        coverage_codes: 필터할 coverage_code 리스트 (None이면 전체)
        top_k_per_insurer: 보험사별 최대 결과 수
        plan_ids: 보험사별 plan_id 매핑 (Step I)
                  - plan_id가 있으면: (c.plan_id = plan_id OR c.plan_id IS NULL)
                  - plan_id가 None이면: c.plan_id IS NULL

    Returns:
        (결과 리스트, 보험사별 건수)
    """
    results: dict[tuple[str, str], CompareAxisResult] = {}
    insurer_counts: dict[str, int] = {}

    with conn.cursor() as cur:
        # 보험사별로 쿼리 실행 (쏠림 방지)
        for insurer_code in insurers:
            # Step I: plan_id 조건 생성
            plan_id = plan_ids.get(insurer_code) if plan_ids else None
            if plan_id is not None:
                plan_condition = "(c.plan_id = %(plan_id)s OR c.plan_id IS NULL)"
                plan_params = (plan_id,)
            else:
                plan_condition = "c.plan_id IS NULL"
                plan_params = ()

            if coverage_codes:
                # STEP 4.10: coverage_alias 기반 텍스트 매칭
                # 1. 먼저 해당 보험사의 alias raw_name 목록 조회
                # 2. chunk content에서 해당 raw_name 포함 여부로 검색
                # Note: CONCAT 사용으로 psycopg3 % 이스케이프 문제 해결
                query = f"""
                    WITH alias_patterns AS (
                        -- 해당 coverage_codes에 대한 alias raw_name 조회
                        SELECT DISTINCT
                            ca.coverage_code,
                            cs.coverage_name,
                            ca.raw_name,
                            ca.raw_name_norm  -- U-5.0-A: 공백 제거 정규화 이름
                        FROM coverage_alias ca
                        JOIN insurer i ON ca.insurer_id = i.insurer_id
                        LEFT JOIN coverage_standard cs ON cs.coverage_code = ca.coverage_code
                        WHERE i.insurer_code = %(insurer_code)s
                          AND ca.coverage_code = ANY(%(coverage_codes)s::text[])
                    ),
                    matched_chunks AS (
                        -- alias raw_name을 포함하는 chunk 검색
                        SELECT
                            c.chunk_id,
                            c.document_id,
                            c.doc_type,
                            c.page_start,
                            LEFT(c.content, 1000) AS preview,
                            ap.coverage_code,
                            ap.coverage_name,
                            i.insurer_code,
                            -- doc_type 우선순위
                            CASE c.doc_type
                                WHEN '가입설계서' THEN 3
                                WHEN '상품요약서' THEN 2
                                WHEN '사업방법서' THEN 1
                                ELSE 0
                            END AS doc_priority
                        FROM chunk c
                        JOIN insurer i ON c.insurer_id = i.insurer_id
                        CROSS JOIN alias_patterns ap
                        WHERE i.insurer_code = %(insurer_code)s
                          AND c.doc_type = ANY(%(doc_types)s::text[])
                          -- U-5.0-A: 공백 무시 매칭 (raw_name_norm 사용)
                          AND REGEXP_REPLACE(LOWER(c.content), '[[:space:]]', '', 'g')
                              LIKE CONCAT(chr(37), ap.raw_name_norm, chr(37))
                          AND {plan_condition}
                          -- V1.6.3-β: synthetic chunk 오염 방지 (비교축에서 제외)
                          AND COALESCE((c.meta->>'is_synthetic')::boolean, false) = false
                    ),
                    ranked AS (
                        SELECT *,
                            ROW_NUMBER() OVER (
                                PARTITION BY coverage_code
                                ORDER BY doc_priority DESC, chunk_id
                            ) AS rn
                        FROM matched_chunks
                    )
                    SELECT chunk_id, document_id, doc_type, page_start, preview,
                           coverage_code, coverage_name, insurer_code
                    FROM ranked
                    WHERE rn <= %(top_k)s
                    ORDER BY coverage_code, rn
                """
                # Named parameters for clarity and to avoid % escaping issues
                params_dict = {
                    "insurer_code": insurer_code,
                    "coverage_codes": coverage_codes,
                    "doc_types": compare_doc_types,
                    "top_k": top_k_per_insurer,
                }
                # Add plan_id if needed
                if plan_id is not None:
                    params_dict["plan_id"] = plan_id

                cur.execute(query, params_dict)
            else:
                # coverage_codes 없으면 기존 로직 유지 (전체 검색)
                query = f"""
                    WITH ranked AS (
                        SELECT
                            c.chunk_id,
                            c.document_id,
                            c.doc_type,
                            c.page_start,
                            LEFT(c.content, 1000) AS preview,
                            c.meta->'entities'->>'coverage_code' AS coverage_code,
                            c.meta->'entities'->>'coverage_name' AS coverage_name,
                            i.insurer_code,
                            ROW_NUMBER() OVER (
                                PARTITION BY c.meta->'entities'->>'coverage_code'
                                ORDER BY c.chunk_id
                            ) AS rn
                        FROM chunk c
                        JOIN insurer i ON c.insurer_id = i.insurer_id
                        WHERE i.insurer_code = %s
                          AND c.doc_type = ANY(%s::text[])
                          AND c.meta->'entities'->>'coverage_code' IS NOT NULL
                          AND {plan_condition}
                          -- V1.6.3-β: synthetic chunk 오염 방지 (비교축에서 제외)
                          AND COALESCE((c.meta->>'is_synthetic')::boolean, false) = false
                    )
                    SELECT *
                    FROM ranked
                    WHERE rn <= %s
                    ORDER BY coverage_code, rn
                """
                params = (insurer_code, compare_doc_types) + plan_params + (top_k_per_insurer,)
                cur.execute(query, params)

            rows = cur.fetchall()
            insurer_counts[insurer_code] = len(rows)

            for row in rows:
                key = (row["insurer_code"], row["coverage_code"])

                if key not in results:
                    results[key] = CompareAxisResult(
                        insurer_code=row["insurer_code"],
                        coverage_code=row["coverage_code"],
                        coverage_name=row["coverage_name"],
                        doc_type_counts={},
                        evidence=[],
                    )

                result = results[key]

                # doc_type 카운트
                doc_type = row["doc_type"]
                result.doc_type_counts[doc_type] = result.doc_type_counts.get(doc_type, 0) + 1

                # evidence 추가
                result.evidence.append(
                    Evidence(
                        document_id=row["document_id"],
                        doc_type=doc_type,
                        page_start=row["page_start"],
                        preview=row["preview"].replace("\n", " ").strip(),
                        score=0.0,
                    )
                )

    return list(results.values()), insurer_counts


def get_policy_axis(
    conn: psycopg.Connection,
    insurers: list[str],
    policy_doc_types: list[str],
    policy_keywords: list[str],
    top_k_per_insurer: int = 10,
) -> tuple[list[PolicyAxisResult], dict[str, int]]:
    """
    Policy Axis 검색: 약관 키워드 기반 근거 수집

    Args:
        conn: DB 연결
        insurers: 보험사 코드 리스트
        policy_doc_types: 검색 대상 doc_type 리스트 (보통 ["약관"])
        policy_keywords: 검색 키워드 리스트
        top_k_per_insurer: 보험사별 최대 결과 수

    Returns:
        (결과 리스트, 보험사별 건수)
    """
    results: dict[tuple[str, str], PolicyAxisResult] = {}
    insurer_counts: dict[str, int] = {}

    if not policy_keywords:
        return [], {}

    with conn.cursor() as cur:
        for insurer_code in insurers:
            for keyword in policy_keywords:
                query = """
                    SELECT
                        c.chunk_id,
                        c.document_id,
                        c.doc_type,
                        c.page_start,
                        LEFT(c.content, 150) AS preview,
                        i.insurer_code
                    FROM chunk c
                    JOIN insurer i ON c.insurer_id = i.insurer_id
                    WHERE i.insurer_code = %s
                      AND c.doc_type = ANY(%s::text[])
                      AND c.content ILIKE %s
                    ORDER BY c.page_start
                    LIMIT %s
                """

                cur.execute(
                    query,
                    (insurer_code, policy_doc_types, f"%{keyword}%", top_k_per_insurer),
                )
                rows = cur.fetchall()

                key = (insurer_code, keyword)
                if rows:
                    if key not in results:
                        results[key] = PolicyAxisResult(
                            insurer_code=insurer_code,
                            keyword=keyword,
                            evidence=[],
                        )

                    for row in rows:
                        results[key].evidence.append(
                            Evidence(
                                document_id=row["document_id"],
                                doc_type=row["doc_type"],
                                page_start=row["page_start"],
                                preview=row["preview"].replace("\n", " ").strip(),
                                score=0.0,
                            )
                        )

                    insurer_counts[f"{insurer_code}:{keyword}"] = len(rows)

    return list(results.values()), insurer_counts


# H-1.8: Amount source priority (상품요약서 > 사업방법서 > 가입설계서)
AMOUNT_SOURCE_PRIORITY = ["상품요약서", "사업방법서", "가입설계서"]


def _resolve_amount_from_evidence(
    best_evidence: list["Evidence"],
) -> ResolvedAmount | None:
    """
    H-1.8: best_evidence에서 대표 금액 1개를 선택

    정책:
    - amount_source_priority: 상품요약서 > 사업방법서 > 가입설계서
    - 가입설계서: confidence='low'이면 제외 (오탐 방지)
    - 각 doc_type에서 amount_value가 있는 첫 번째 것 선택

    Args:
        best_evidence: Evidence 리스트

    Returns:
        ResolvedAmount | None
    """
    # doc_type별로 Evidence 그룹화
    evidence_by_doc_type: dict[str, list["Evidence"]] = {}
    for ev in best_evidence:
        if ev.amount and ev.amount.amount_value is not None:
            if ev.doc_type not in evidence_by_doc_type:
                evidence_by_doc_type[ev.doc_type] = []
            evidence_by_doc_type[ev.doc_type].append(ev)

    # 우선순위 순서로 선택
    for doc_type in AMOUNT_SOURCE_PRIORITY:
        if doc_type not in evidence_by_doc_type:
            continue

        for ev in evidence_by_doc_type[doc_type]:
            amount = ev.amount
            if not amount or amount.amount_value is None:
                continue

            # 가입설계서: confidence='low'이면 제외
            if doc_type == "가입설계서" and amount.confidence == "low":
                continue

            return ResolvedAmount(
                amount_value=amount.amount_value,
                amount_text=amount.amount_text,
                unit=amount.unit,
                confidence=amount.confidence,
                source_doc_type=doc_type,
                source_document_id=ev.document_id,
            )

    # 선택된 금액 없음
    return None


def build_coverage_compare_result(
    compare_axis: list[CompareAxisResult],
    insurers: list[str],
) -> list[CoverageCompareRow]:
    """
    compare_axis를 표 형태로 집계

    Args:
        compare_axis: CompareAxisResult 리스트
        insurers: 요청된 보험사 순서

    Returns:
        coverage_code별로 집계된 비교표
    """
    # doc_type 우선순위 (best_evidence 선택용)
    doc_type_priority_order = ["가입설계서", "상품요약서", "사업방법서"]

    # coverage_code별로 그룹화
    coverage_groups: dict[str, dict[str, CompareAxisResult]] = {}
    coverage_names: dict[str, str | None] = {}

    for item in compare_axis:
        if item.coverage_code not in coverage_groups:
            coverage_groups[item.coverage_code] = {}
            coverage_names[item.coverage_code] = item.coverage_name

        coverage_groups[item.coverage_code][item.insurer_code] = item

    # 비교표 생성
    rows: list[CoverageCompareRow] = []

    for coverage_code, insurer_map in coverage_groups.items():
        cells: list[InsurerCompareCell] = []

        # insurers 순서 유지
        for insurer_code in insurers:
            if insurer_code in insurer_map:
                item = insurer_map[insurer_code]

                # best_evidence 선택: doc_type 우선순위로 최대 2개
                best_evidence: list[Evidence] = []
                evidence_by_doc_type: dict[str, list[Evidence]] = {}

                for ev in item.evidence:
                    if ev.doc_type not in evidence_by_doc_type:
                        evidence_by_doc_type[ev.doc_type] = []
                    evidence_by_doc_type[ev.doc_type].append(ev)

                # 우선순위 순서로 각 doc_type에서 1개씩 선택 (최대 2개)
                for doc_type in doc_type_priority_order:
                    if doc_type in evidence_by_doc_type and len(best_evidence) < 2:
                        # score가 가장 높은 1개 선택 (현재 score=0이면 첫 번째)
                        ev_list = evidence_by_doc_type[doc_type]
                        best_ev = max(ev_list, key=lambda x: x.score)

                        # 금액/조건 추출 (약관 제외 - A2 정책)
                        if best_ev.doc_type != "약관":
                            # 금액 추출 (doc_type 전달하여 가입설계서는 엄격 모드)
                            amount_result = extract_amount(best_ev.preview, doc_type=best_ev.doc_type)
                            amount_info = AmountInfo(
                                amount_value=amount_result.amount_value,
                                amount_text=amount_result.amount_text,
                                unit=amount_result.unit,
                                confidence=amount_result.confidence,
                                method=amount_result.method,
                            )

                            # 조건 추출
                            condition_result = extract_condition_snippet(best_ev.preview)
                            condition_info = ConditionInfo(
                                snippet=condition_result.snippet,
                                matched_terms=condition_result.matched_terms,
                            )

                            # Evidence에 추가
                            best_ev = Evidence(
                                document_id=best_ev.document_id,
                                doc_type=best_ev.doc_type,
                                page_start=best_ev.page_start,
                                preview=best_ev.preview,
                                score=best_ev.score,
                                amount=amount_info,
                                condition_snippet=condition_info,
                            )

                        best_evidence.append(best_ev)

                # H-1.8: resolved_amount 선택
                resolved_amount = _resolve_amount_from_evidence(best_evidence)

                # U-4.17: compare_status 결정
                # U-4.18: source_level 결정
                # - best_evidence가 비어있지만 약관에 데이터가 있으면 NO_COMPARABLE_EVIDENCE
                # - Compare는 가입설계서/상품요약서/사업방법서만 사용 (약관 제외)
                compare_status = "COMPARABLE"
                source_level = "UNKNOWN"
                has_policy_evidence = "약관" in evidence_by_doc_type

                if best_evidence:
                    # 비교 가능 문서(가입설계서/상품요약서/사업방법서) 기반
                    compare_status = "COMPARABLE"
                    source_level = "COMPARABLE_DOC"
                elif has_policy_evidence:
                    # 약관만 존재
                    compare_status = "NO_COMPARABLE_EVIDENCE"
                    source_level = "POLICY_ONLY"
                else:
                    # evidence 없음
                    compare_status = "NO_COMPARABLE_EVIDENCE"
                    source_level = "UNKNOWN"

                cells.append(
                    InsurerCompareCell(
                        insurer_code=insurer_code,
                        doc_type_counts=item.doc_type_counts.copy(),
                        best_evidence=best_evidence,
                        resolved_amount=resolved_amount,
                        compare_status=compare_status,
                        source_level=source_level,
                    )
                )
            else:
                # 해당 보험사에 데이터 없음
                cells.append(
                    InsurerCompareCell(
                        insurer_code=insurer_code,
                        doc_type_counts={},
                        best_evidence=[],
                        resolved_amount=None,
                        compare_status="NO_COMPARABLE_EVIDENCE",
                        source_level="UNKNOWN",
                    )
                )

        rows.append(
            CoverageCompareRow(
                coverage_code=coverage_code,
                coverage_name=coverage_names.get(coverage_code),
                insurers=cells,
            )
        )

    return rows


# =============================================================================
# Step H-2: LLM 정밀 추출 (선별 적용)
# =============================================================================


@dataclass
class LLMRefinementStats:
    """LLM refinement 통계 (debug용)"""
    total_calls: int = 0
    success_count: int = 0
    upgrade_count: int = 0
    skip_reasons: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # H-2.1: 상세 메트릭
    llm_calls_attempted: int = 0
    llm_calls_succeeded: int = 0
    llm_upgrades: int = 0
    llm_failures_by_reason: dict[str, int] = field(default_factory=dict)
    llm_total_latency_ms: float = 0.0

    def to_debug_dict(self) -> dict:
        """debug 출력용 dict 반환"""
        return {
            "total_calls": self.total_calls,
            "success_count": self.success_count,
            "upgrade_count": self.upgrade_count,
            "skip_reasons": self.skip_reasons,
            "errors": self.errors,
            "llm_calls_attempted": self.llm_calls_attempted,
            "llm_calls_succeeded": self.llm_calls_succeeded,
            "llm_upgrades": self.llm_upgrades,
            "llm_failures_by_reason": self.llm_failures_by_reason,
            "llm_total_latency_ms": round(self.llm_total_latency_ms, 2),
        }

    def record_failure(self, reason: str) -> None:
        """실패 이유 기록"""
        self.llm_failures_by_reason[reason] = (
            self.llm_failures_by_reason.get(reason, 0) + 1
        )


def _should_call_llm_for_cell(
    cell: InsurerCompareCell,
    query: str,
) -> tuple[bool, str, "Evidence | None"]:
    """
    셀에 대해 LLM 호출이 필요한지 판단

    선별 조건:
    1. resolved_amount.amount_value is None
    2. best_evidence 중 doc_type=='가입설계서' evidence 존재
    3. evidence.amount.confidence in ('low', 'medium') OR amount is None

    추가 조건 (옵션):
    - query가 금액 의도를 포함할 때만

    Returns:
        (호출 필요 여부, skip 이유, 대상 evidence)
    """
    # 조건 1: resolved_amount가 이미 있으면 skip
    if cell.resolved_amount is not None and cell.resolved_amount.amount_value is not None:
        return False, "resolved_amount already exists", None

    # 조건 2: 가입설계서 evidence 찾기
    enrollment_evidence = None
    for ev in cell.best_evidence:
        if ev.doc_type == "가입설계서":
            enrollment_evidence = ev
            break

    if enrollment_evidence is None:
        return False, "no 가입설계서 evidence", None

    # 조건 3: amount가 없거나 confidence가 낮은 경우
    if enrollment_evidence.amount is None:
        # amount 자체가 없으면 LLM 호출 대상
        pass
    elif enrollment_evidence.amount.confidence not in ("low", "medium"):
        # confidence가 high이면 이미 신뢰할 수 있음
        return False, "가입설계서 amount confidence is high", None

    # 추가 조건: query에 금액 의도가 있는지 (옵션)
    if query and not has_amount_intent(query):
        return False, "query has no amount intent", None

    return True, "", enrollment_evidence


async def refine_amount_with_llm_if_needed(
    cell: InsurerCompareCell,
    insurer_code: str,
    coverage_code: str,
    query: str,
    llm_client: LLMClient,
    chunk_text: str | None = None,
    chunk_id: int | None = None,
) -> tuple[InsurerCompareCell, dict]:
    """
    선별 조건 충족 시 가입설계서 evidence에 대해 LLM 호출

    정책:
    - LLM 결과가 benefit_amount + confidence>=medium + span 존재 시 업그레이드
    - premium_amount/unknown이면 resolved_amount 유지 (None)

    Args:
        cell: InsurerCompareCell
        insurer_code: 보험사 코드
        coverage_code: 담보 코드
        query: 검색 쿼리
        llm_client: LLM 클라이언트
        chunk_text: chunk 텍스트 (None이면 evidence.preview 사용)
        chunk_id: chunk ID (None이면 0)

    Returns:
        (updated cell, debug info)
    """
    debug_info = {
        "called": False,
        "success": False,
        "upgraded": False,
        "reason": "",
        "llm_result": None,
        "latency_ms": 0.0,
    }

    # 선별 조건 확인
    should_call, skip_reason, target_evidence = _should_call_llm_for_cell(cell, query)

    if not should_call:
        debug_info["reason"] = skip_reason
        return cell, debug_info

    if target_evidence is None:
        debug_info["reason"] = "no target evidence"
        return cell, debug_info

    # LLM 호출
    debug_info["called"] = True

    try:
        # chunk_text가 없으면 evidence.preview 사용
        text_to_analyze = chunk_text or target_evidence.preview
        actual_chunk_id = chunk_id or 0

        user_prompt = build_user_prompt(
            insurer_code=insurer_code,
            coverage_code=coverage_code,
            document_id=target_evidence.document_id,
            page_start=target_evidence.page_start,
            chunk_id=actual_chunk_id,
            chunk_text=text_to_analyze,
        )

        context = {
            "coverage_code": coverage_code,
            "insurer_code": insurer_code,
            "document_id": target_evidence.document_id,
            "page_start": target_evidence.page_start,
            "chunk_id": actual_chunk_id,
        }

        start_time = time.time()
        llm_result = await llm_client.extract(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            context=context,
        )
        debug_info["latency_ms"] = (time.time() - start_time) * 1000

        if llm_result is None:
            debug_info["reason"] = "LLM returned None"
            return cell, debug_info

        debug_info["success"] = True
        debug_info["llm_result"] = llm_result.model_dump() if hasattr(llm_result, "model_dump") else str(llm_result)

        # 결과 검증 및 업그레이드
        amount = llm_result.amount

        # 업그레이드 조건:
        # 1. label == "benefit_amount"
        # 2. confidence in ("high", "medium")
        # 3. span이 존재하고 chunk_text에 포함됨
        if amount.label != "benefit_amount":
            debug_info["reason"] = f"label is {amount.label}, not benefit_amount"
            return cell, debug_info

        if amount.confidence not in ("high", "medium"):
            debug_info["reason"] = f"confidence is {amount.confidence}, need high or medium"
            return cell, debug_info

        if amount.amount_value is None:
            debug_info["reason"] = "amount_value is None"
            return cell, debug_info

        # span 검증 (환각 방지)
        if amount.span is not None and amount.span.text:
            if not validate_span_in_text(amount.span.text, text_to_analyze):
                debug_info["reason"] = "span text not found in chunk (hallucination)"
                return cell, debug_info

        # 업그레이드!
        new_resolved_amount = ResolvedAmount(
            amount_value=amount.amount_value,
            amount_text=amount.amount_text,
            unit=amount.unit,
            confidence=amount.confidence,
            source_doc_type="가입설계서",
            source_document_id=target_evidence.document_id,
        )

        # cell 업데이트 (U-4.17/U-4.18: compare_status, source_level 유지)
        updated_cell = InsurerCompareCell(
            insurer_code=cell.insurer_code,
            doc_type_counts=cell.doc_type_counts,
            best_evidence=cell.best_evidence,
            resolved_amount=new_resolved_amount,
            compare_status=cell.compare_status,
            source_level=cell.source_level,
        )

        debug_info["upgraded"] = True
        debug_info["reason"] = "upgraded from LLM"
        return updated_cell, debug_info

    except RuntimeError as e:
        # LLM disabled
        debug_info["reason"] = f"LLM disabled: {str(e)}"
        return cell, debug_info
    except Exception as e:
        debug_info["reason"] = f"LLM error: {str(e)}"
        return cell, debug_info


async def refine_coverage_compare_result_with_llm(
    coverage_compare_result: list[CoverageCompareRow],
    query: str,
    llm_client: LLMClient | None = None,
) -> tuple[list[CoverageCompareRow], LLMRefinementStats]:
    """
    coverage_compare_result 전체에 대해 LLM refinement 적용

    Args:
        coverage_compare_result: 비교표 결과
        query: 검색 쿼리
        llm_client: LLM 클라이언트 (None이면 DisabledLLMClient)

    Returns:
        (refined result, stats)
    """
    if llm_client is None:
        llm_client = DisabledLLMClient()

    stats = LLMRefinementStats()
    max_calls = get_llm_max_calls_per_request()
    call_count = 0

    refined_rows: list[CoverageCompareRow] = []

    for row in coverage_compare_result:
        refined_cells: list[InsurerCompareCell] = []

        for cell in row.insurers:
            # 호출 제한 체크
            if call_count >= max_calls:
                stats.skip_reasons.append(f"max_calls reached ({max_calls})")
                refined_cells.append(cell)
                continue

            # LLM refinement 시도
            updated_cell, debug_info = await refine_amount_with_llm_if_needed(
                cell=cell,
                insurer_code=cell.insurer_code,
                coverage_code=row.coverage_code,
                query=query,
                llm_client=llm_client,
            )

            if debug_info.get("called"):
                call_count += 1
                stats.total_calls += 1
                stats.llm_calls_attempted += 1

                if debug_info.get("success"):
                    stats.success_count += 1
                    stats.llm_calls_succeeded += 1

                if debug_info.get("upgraded"):
                    stats.upgrade_count += 1
                    stats.llm_upgrades += 1

                # 레이턴시 기록 (debug_info에 있으면)
                if debug_info.get("latency_ms"):
                    stats.llm_total_latency_ms += debug_info["latency_ms"]

                if debug_info.get("reason") and not debug_info.get("upgraded"):
                    reason = debug_info.get("reason", "unknown")
                    if "error" in reason.lower():
                        stats.errors.append(reason)
                    stats.record_failure(reason)
            else:
                if debug_info.get("reason"):
                    stats.skip_reasons.append(debug_info["reason"])

            refined_cells.append(updated_cell)

        refined_rows.append(
            CoverageCompareRow(
                coverage_code=row.coverage_code,
                coverage_name=row.coverage_name,
                insurers=refined_cells,
            )
        )

    return refined_rows, stats


def build_diff_summary(
    coverage_compare_result: list[CoverageCompareRow],
) -> list[DiffSummaryItem]:
    """
    coverage_compare_result 기반 차이점 요약 생성 (규칙 기반)

    규칙:
    - doc_type별 존재 여부 비교
    - 보험사별 근거 유무 차이 텍스트 생성
    - evidence_refs로 best_evidence 참조

    Args:
        coverage_compare_result: 비교표 결과

    Returns:
        coverage_code별 차이점 요약
    """
    doc_type_priority_order = ["가입설계서", "상품요약서", "사업방법서"]
    results: list[DiffSummaryItem] = []

    for row in coverage_compare_result:
        bullets: list[DiffBullet] = []
        insurer_cells = {cell.insurer_code: cell for cell in row.insurers}
        insurer_codes = [cell.insurer_code for cell in row.insurers]

        if len(insurer_codes) < 2:
            # 보험사가 1개면 비교 불가, 기본 정보만 제공
            if insurer_codes:
                cell = insurer_cells[insurer_codes[0]]
                if cell.doc_type_counts:
                    doc_types = ", ".join(cell.doc_type_counts.keys())
                    refs = [
                        EvidenceRef(
                            insurer_code=cell.insurer_code,
                            document_id=e.document_id,
                            page_start=e.page_start,
                        )
                        for e in cell.best_evidence
                    ]
                    bullets.append(
                        DiffBullet(
                            text=f"{cell.insurer_code}에 {doc_types} 근거 존재.",
                            evidence_refs=refs,
                        )
                    )
        else:
            # doc_type별로 비교
            for doc_type in doc_type_priority_order:
                has_doc_type: dict[str, bool] = {}
                evidence_by_insurer: dict[str, list[Evidence]] = {}

                for insurer_code in insurer_codes:
                    cell = insurer_cells[insurer_code]
                    count = cell.doc_type_counts.get(doc_type, 0)
                    has_doc_type[insurer_code] = count > 0
                    # best_evidence 중 해당 doc_type만 필터
                    evidence_by_insurer[insurer_code] = [
                        e for e in cell.best_evidence if e.doc_type == doc_type
                    ]

                has_list = [ic for ic in insurer_codes if has_doc_type[ic]]
                not_has_list = [ic for ic in insurer_codes if not has_doc_type[ic]]

                if len(has_list) == len(insurer_codes):
                    # 모두 있음
                    refs = []
                    for ic in insurer_codes:
                        for e in evidence_by_insurer[ic]:
                            refs.append(
                                EvidenceRef(
                                    insurer_code=ic,
                                    document_id=e.document_id,
                                    page_start=e.page_start,
                                )
                            )
                    if refs:
                        bullets.append(
                            DiffBullet(
                                text=f"모든 보험사에 {doc_type} 근거 존재.",
                                evidence_refs=refs,
                            )
                        )
                elif len(has_list) == 0:
                    # 모두 없음 - 생략
                    pass
                else:
                    # 일부만 있음
                    has_str = ", ".join(has_list)
                    not_has_str = ", ".join(not_has_list)
                    refs = []
                    for ic in has_list:
                        for e in evidence_by_insurer[ic]:
                            refs.append(
                                EvidenceRef(
                                    insurer_code=ic,
                                    document_id=e.document_id,
                                    page_start=e.page_start,
                                )
                            )
                    bullets.append(
                        DiffBullet(
                            text=f"{has_str}은 {doc_type} 근거가 있고, {not_has_str}은 없음.",
                            evidence_refs=refs,
                        )
                    )

        results.append(
            DiffSummaryItem(
                coverage_code=row.coverage_code,
                coverage_name=row.coverage_name,
                bullets=bullets,
            )
        )

    return results


def compare(
    insurers: list[str],
    query: str,
    coverage_codes: list[str] | None = None,
    top_k_per_insurer: int = 10,
    compare_doc_types: list[str] | None = None,
    policy_doc_types: list[str] | None = None,
    policy_keywords: list[str] | None = None,
    coverage_top_n_per_insurer: int = 3,
    db_url: str | None = None,
    age: int | None = None,
    gender: Literal["M", "F"] | None = None,
    locked_coverage_codes: list[str] | None = None,  # STEP 4.7: 고정된 담보 코드
) -> CompareResponse:
    """
    2-Phase Retrieval 비교 검색

    Args:
        insurers: 비교할 보험사 코드 리스트
        query: 사용자 질의 (현재는 로깅용)
        coverage_codes: 필터할 coverage_code 리스트
        top_k_per_insurer: 보험사별 최대 결과 수
        compare_doc_types: Compare Axis 대상 doc_type
        policy_doc_types: Policy Axis 대상 doc_type
        policy_keywords: 약관 검색 키워드
        coverage_top_n_per_insurer: coverage_codes 자동추천 시 보험사별 추천 개수
        db_url: DB URL
        age: 피보험자 나이 (plan 자동 선택용)
        gender: 피보험자 성별 (M/F)

    Returns:
        CompareResponse
    """
    if compare_doc_types is None:
        compare_doc_types = ["가입설계서", "상품요약서", "사업방법서"]
    if policy_doc_types is None:
        policy_doc_types = ["약관"]

    # policy_keywords 자동 추출 (없거나 빈 배열이면)
    if not policy_keywords:
        resolved_policy_keywords = extract_policy_keywords(query)
    else:
        resolved_policy_keywords = policy_keywords

    debug: dict[str, Any] = {
        "query": query,
        "insurers": insurers,
        "resolved_policy_keywords": resolved_policy_keywords,
        "timing_ms": {},
        "insurer_counts": {},
        "age": age,
        "gender": gender,
    }

    conn = psycopg.connect(db_url or get_db_url(), row_factory=dict_row)

    try:
        # Step I: Plan 자동 선택
        selected_plans: dict[str, SelectedPlan] = {}
        plan_ids: dict[str, int | None] = {}

        if age is not None or gender is not None:
            # psycopg2 커넥션 필요 (plan_selector는 psycopg2 사용)
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn2 = psycopg2.connect(db_url or get_db_url())
            try:
                selected_plans = select_plans_for_insurers(conn2, insurers, age, gender)
                plan_ids = get_plan_ids_for_retrieval(selected_plans)
            finally:
                conn2.close()

        debug["selected_plan"] = [
            {
                "insurer_code": p.insurer_code,
                "product_id": p.product_id,
                "plan_id": p.plan_id,
                "plan_name": p.plan_name,
                "reason": p.reason,
            }
            for p in selected_plans.values()
        ] if selected_plans else []

        # coverage_codes 자동 추천 (없거나 빈 배열이면)
        recommended_coverage_codes: list[str] = []
        recommended_coverage_details: list[dict[str, Any]] = []

        if not coverage_codes:
            start = time.time()
            recommended_codes, recommendations = recommend_coverage_codes(
                conn,
                insurers,
                query,
                top_n_per_insurer=coverage_top_n_per_insurer,
            )
            debug["timing_ms"]["coverage_recommendation"] = round((time.time() - start) * 1000, 2)

            recommended_coverage_codes = recommended_codes
            recommended_coverage_details = [
                {
                    "insurer_code": r.insurer_code,
                    "coverage_code": r.coverage_code,
                    "coverage_name": r.coverage_name,
                    "raw_name": r.raw_name,
                    "source_doc_type": r.source_doc_type,
                    "similarity": round(r.similarity, 4),
                }
                for r in recommendations
            ]

            # 추천된 코드로 compare_axis 실행
            resolved_coverage_codes = recommended_codes if recommended_codes else None
        else:
            resolved_coverage_codes = coverage_codes

        # debug에 coverage 추천 정보 추가
        debug["recommended_coverage_codes"] = recommended_coverage_codes
        debug["recommended_coverage_details"] = recommended_coverage_details
        debug["resolved_coverage_codes"] = resolved_coverage_codes

        # Compare Axis (Step I: plan_ids 전달)
        start = time.time()
        compare_axis, compare_counts = get_compare_axis(
            conn,
            insurers,
            compare_doc_types,
            resolved_coverage_codes,
            top_k_per_insurer,
            plan_ids=plan_ids if plan_ids else None,
        )
        debug["timing_ms"]["compare_axis"] = round((time.time() - start) * 1000, 2)
        debug["insurer_counts"]["compare_axis"] = compare_counts

        # Step K: Hybrid fallback (벡터 검색)
        debug["hybrid_enabled"] = is_hybrid_enabled()
        debug["hybrid_used"] = False

        if is_hybrid_enabled():
            # coverage_codes 검색 결과가 부족하면 벡터 검색 fallback
            total_evidence = sum(compare_counts.values())
            min_evidence_threshold = len(insurers)  # 보험사당 최소 1개

            if total_evidence < min_evidence_threshold:
                from services.ingestion.embedding import DummyEmbeddingProvider

                # Query embedding 생성
                embedding_provider = DummyEmbeddingProvider()
                query_embedding = embedding_provider.embed_text(query)

                # 벡터 검색 실행
                start_vector = time.time()
                vector_results, vector_counts = get_compare_axis_vector(
                    conn,
                    insurers,
                    compare_doc_types,
                    query_embedding,
                    top_k_per_insurer,
                    plan_ids=plan_ids if plan_ids else None,
                    ef_search=get_hybrid_ef_search(),
                )
                debug["timing_ms"]["compare_axis_vector"] = round(
                    (time.time() - start_vector) * 1000, 2
                )
                debug["insurer_counts"]["compare_axis_vector"] = vector_counts
                debug["hybrid_used"] = True

                # 벡터 검색 결과 병합 (기존 결과에 없는 chunk만 추가)
                existing_chunk_ids = set()
                for result in compare_axis:
                    for ev in result.evidence:
                        existing_chunk_ids.add(ev.chunk_id)

                for vector_result in vector_results:
                    insurer_code = vector_result.insurer_code
                    # 기존 결과에서 해당 보험사 찾기
                    existing_result = next(
                        (r for r in compare_axis if r.insurer_code == insurer_code),
                        None
                    )
                    if existing_result is None:
                        # 새 보험사 결과 추가
                        compare_axis.append(vector_result)
                    else:
                        # 기존 보험사에 새 evidence 추가
                        for ev in vector_result.evidence:
                            if ev.chunk_id not in existing_chunk_ids:
                                existing_result.evidence.append(ev)
                                existing_chunk_ids.add(ev.chunk_id)

        # U-4.11: 2-pass amount retrieval for payout_amount slot
        # U-4.15: slot_type 기반 키워드 선택
        # Check each insurer's evidence for amounts, fetch additional if needed
        start = time.time()
        amount_pattern = re.compile(r'\d[\d,]*\s*만\s*원')
        amount_retrieval_used = {}

        # U-4.15: coverage_codes에서 slot_type 결정
        slot_type_for_retrieval = determine_slot_type_from_codes(resolved_coverage_codes)
        debug["slot_type_for_retrieval"] = slot_type_for_retrieval

        # STEP 4.7: locked_coverage_codes가 있으면 effective_locked_code 결정
        # fallback 시 coverage_code로 사용 (단일 insurer 기준)
        effective_locked_code: str | None = None
        if locked_coverage_codes and len(locked_coverage_codes) > 0:
            effective_locked_code = locked_coverage_codes[0]

        # STEP 4.7: retrieval fallback 추적용
        retrieval_debug: dict[str, Any] = {}

        for insurer_code in insurers:
            # Find insurer's compare_axis entries
            insurer_evidence = []
            for result in compare_axis:
                if result.insurer_code == insurer_code:
                    insurer_evidence.extend(result.evidence)

            # Check if any evidence has amount
            has_amount = any(
                amount_pattern.search(ev.preview) for ev in insurer_evidence
            )

            if not has_amount:
                # 2nd pass: fetch amount-bearing chunks (U-4.15: slot_type 전달)
                plan_id = plan_ids.get(insurer_code) if plan_ids else None

                # U-4.15: cerebro 쿼리 시 target_keyword 전달하여 정밀 검색
                # 예: "뇌졸중진단비" 쿼리 → "뇌졸중진단비" 키워드 포함 청크 우선
                target_kw = None
                if slot_type_for_retrieval == "cerebro_cardiovascular":
                    # STEP 2.8: query에서 진단비 패턴 추출 (config에서 로드)
                    cerebro_kws = get_slot_search_keywords().get("cerebro_cardiovascular", [])
                    for kw in cerebro_kws:
                        if kw in query:
                            target_kw = kw
                            break
                    # 없으면 query + "진단비" 조합 시도
                    if not target_kw and "진단비" not in query:
                        target_kw = query + "진단비" if query else None

                amount_evidence = get_amount_bearing_evidence(
                    conn,
                    insurer_code,
                    compare_doc_types,
                    plan_id=plan_id,
                    top_k=3,
                    slot_type=slot_type_for_retrieval,
                    target_keyword=target_kw,
                )

                if amount_evidence:
                    amount_retrieval_used[insurer_code] = len(amount_evidence)

                    # Add to compare_axis (create new entry if needed)
                    existing_result = next(
                        (r for r in compare_axis if r.insurer_code == insurer_code),
                        None
                    )
                    if existing_result is None:
                        # Create new CompareAxisResult for this insurer
                        # STEP 4.7: locked_coverage_codes가 있으면 해당 코드 사용
                        # "__amount_fallback__"은 locked 상태에서 절대 금지
                        fallback_coverage_code = (
                            effective_locked_code
                            if effective_locked_code
                            else "__amount_fallback__"
                        )

                        # STEP 4.7: fallback 사용 여부 debug에 기록
                        if effective_locked_code:
                            retrieval_debug["fallback_used"] = True
                            retrieval_debug["fallback_reason"] = "no_tagged_chunks_for_locked_code"
                            retrieval_debug["fallback_source"] = "amount_pass_2"
                            retrieval_debug["effective_locked_code"] = effective_locked_code

                        compare_axis.append(
                            CompareAxisResult(
                                insurer_code=insurer_code,
                                coverage_code=fallback_coverage_code,
                                coverage_name=None,
                                doc_type_counts={},
                                evidence=amount_evidence,
                            )
                        )
                    else:
                        # Add evidence to existing result (avoid duplicates)
                        existing_doc_ids = {ev.document_id for ev in existing_result.evidence}
                        for ev in amount_evidence:
                            if ev.document_id not in existing_doc_ids:
                                existing_result.evidence.append(ev)
                                existing_doc_ids.add(ev.document_id)
                                # Update doc_type counts
                                existing_result.doc_type_counts[ev.doc_type] = (
                                    existing_result.doc_type_counts.get(ev.doc_type, 0) + 1
                                )

        debug["timing_ms"]["amount_retrieval_2pass"] = round((time.time() - start) * 1000, 2)
        debug["amount_retrieval_used"] = amount_retrieval_used

        # STEP 4.7: retrieval fallback debug 정보 추가
        if retrieval_debug:
            debug["retrieval"] = retrieval_debug

        # Policy Axis (resolved_policy_keywords 사용)
        start = time.time()
        policy_axis, policy_counts = get_policy_axis(
            conn,
            insurers,
            policy_doc_types,
            resolved_policy_keywords,
            top_k_per_insurer,
        )
        debug["timing_ms"]["policy_axis"] = round((time.time() - start) * 1000, 2)
        debug["insurer_counts"]["policy_axis"] = policy_counts

        # Coverage Compare Result (비교표) 생성
        start = time.time()
        coverage_compare_result = build_coverage_compare_result(compare_axis, insurers)
        debug["timing_ms"]["coverage_compare_result"] = round((time.time() - start) * 1000, 2)

        # Diff Summary (차이점 요약) 생성
        start = time.time()
        diff_summary = build_diff_summary(coverage_compare_result)
        debug["timing_ms"]["diff_summary"] = round((time.time() - start) * 1000, 2)

        # U-4.8: Comparison Slots 추출 (U-4.16: query 전달하여 조건부 슬롯 지원)
        start = time.time()
        slots = extract_slots(
            insurers=insurers,
            compare_axis=compare_axis,
            policy_axis=policy_axis,
            coverage_codes=resolved_coverage_codes,
            query=query,  # U-4.16: 다빈치/경계성종양 쿼리 시 조건부 슬롯 추출
        )
        debug["timing_ms"]["slots"] = round((time.time() - start) * 1000, 2)
        debug["slots_count"] = len(slots)

    finally:
        conn.close()

    return CompareResponse(
        compare_axis=compare_axis,
        policy_axis=policy_axis,
        coverage_compare_result=coverage_compare_result,
        diff_summary=diff_summary,
        slots=slots,
        resolved_coverage_codes=resolved_coverage_codes,
        debug=debug,
    )
