"""
Coverage Domain Configuration Loader

STEP 2.7-α: 설정 파일 기반 담보 계열 관리
STEP 2.8: 하드코딩 비즈니스 규칙 외부화
- 모든 의미 규칙을 YAML 설정 파일에서 로드
- 코드 수정 없이 설정 파일만으로 규칙 변경 가능
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


# 설정 파일 디렉토리 경로
CONFIG_DIR = Path(__file__).parent.parent / "config"


@lru_cache(maxsize=1)
def _load_yaml(filename: str) -> dict[str, Any]:
    """YAML 파일 로드 (캐싱)"""
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_coverage_domains() -> dict[str, str]:
    """
    coverage_code -> domain 매핑 반환

    Returns:
        {"A4209": "CANCER", "A3300_1": "INJURY", ...}
    """
    return _load_yaml("coverage_domain.yaml")


def get_domain_priority() -> dict[str, list[str]]:
    """
    domain -> 대표 담보 우선순위 리스트 반환

    Returns:
        {"CANCER": ["A4209", "A4200_1", ...], ...}
    """
    return _load_yaml("domain_priority.yaml")


def get_coverage_roles() -> dict[str, str]:
    """
    coverage_code -> 메인/파생 구분 반환

    Returns:
        {"A4209": "MAIN", "A4210": "DERIVED", ...}
    """
    return _load_yaml("coverage_role.yaml")


def get_domain_keywords() -> dict[str, list[str]]:
    """
    domain -> 질의 키워드 리스트 반환

    Returns:
        {"CANCER": ["암", "암진단", ...], ...}
    """
    return _load_yaml("domain_keywords.yaml")


def get_derived_keywords() -> dict[str, list[str]]:
    """
    coverage_code/그룹 -> 파생 담보 요청 키워드 반환

    Returns:
        {"A4210": ["유사암", ...], "subtype": ["제자리암", ...], ...}
    """
    return _load_yaml("derived_keywords.yaml")


def get_display_names() -> dict[str, dict[str, str]]:
    """
    표시용 이름 매핑 반환

    Returns:
        {
            "coverage_names": {"A4209": "암진단비", ...},
            "insurer_names": {"SAMSUNG": "삼성화재", ...}
        }
    """
    return _load_yaml("display_names.yaml")


def get_coverage_display_name(code: str) -> str | None:
    """coverage_code의 표시용 이름 반환"""
    names = get_display_names()
    return names.get("coverage_names", {}).get(code)


def get_insurer_display_name(code: str) -> str | None:
    """insurer_code의 표시용 이름 반환"""
    names = get_display_names()
    return names.get("insurer_names", {}).get(code)


def get_coverage_priority_score(code: str) -> int:
    """
    coverage_code의 우선순위 점수 반환 (낮을수록 높은 우선순위)
    domain_priority.yaml 기반
    """
    domain_priority = get_domain_priority()
    coverage_domains = get_coverage_domains()

    domain = coverage_domains.get(code)
    if not domain:
        return 99  # 미정의 코드는 낮은 우선순위

    priority_list = domain_priority.get(domain, [])
    try:
        return priority_list.index(code) + 1
    except ValueError:
        return 99  # 리스트에 없으면 낮은 우선순위


def clear_cache():
    """캐시 초기화 (테스트용)"""
    _load_yaml.cache_clear()


# =============================================================================
# STEP 2.8: P0 외부화 로더
# =============================================================================

def get_insurer_aliases() -> dict[str, str]:
    """
    보험사 alias 사전 반환 (한글명 -> insurer code)

    Returns:
        {"삼성화재": "SAMSUNG", "메리츠": "MERITZ", ...}
    """
    return _load_yaml("mappings/insurer_alias.yaml")


def get_compare_patterns() -> list[str]:
    """
    비교 의도 표현 패턴 리스트 반환

    Returns:
        [" vs ", "비교", "대비", ...]
    """
    data = _load_yaml("rules/compare_patterns.yaml")
    return data.get("patterns", [])


def get_policy_keyword_patterns() -> dict[str, str]:
    """
    질의 정규화 패턴 반환 (다양한 표현 -> 검색용 키워드)

    Returns:
        {"상피내암": "제자리암", "갑상선암": "유사암", ...}
    """
    data = _load_yaml("mappings/policy_keyword_patterns.yaml")
    # defaults 키 제외하고 반환
    return {k: v for k, v in data.items() if k != "defaults"}


def get_default_policy_keywords() -> list[str]:
    """
    기본 policy_keywords 반환 (아무것도 못 찾았을 때)

    Returns:
        ["경계성", "유사암", "제자리암"]
    """
    data = _load_yaml("mappings/policy_keyword_patterns.yaml")
    return data.get("defaults", ["경계성", "유사암", "제자리암"])


def get_doc_type_priority() -> dict[str, int]:
    """
    source_doc_type 우선순위 가중치 반환

    Returns:
        {"가입설계서": 3, "상품요약서": 2, "사업방법서": 1}
    """
    return _load_yaml("rules/doc_type_priority.yaml")


def get_slot_search_keywords() -> dict[str, list[str]]:
    """
    슬롯별 검색 키워드 레지스트리 반환

    Returns:
        {"diagnosis_lump_sum": [...], "cancer_diagnosis": [...], ...}
    """
    return _load_yaml("mappings/slot_search_keywords.yaml")


def get_coverage_code_groups() -> dict[str, list[str]]:
    """
    coverage_code 그룹 정의 반환

    Returns:
        {"cancer": ["A4200_1", ...], "cerebro_cardiovascular": [...], ...}
    """
    return _load_yaml("mappings/coverage_code_groups.yaml")


def get_coverage_code_to_type() -> dict[str, str]:
    """
    coverage_code -> coverage_type 매핑 반환

    Returns:
        {"A4200_1": "cancer_diagnosis", "A4103": "cerebro_cardiovascular_diagnosis", ...}
    """
    return _load_yaml("mappings/coverage_code_to_type.yaml")


# =============================================================================
# STEP 2.9: Query Anchor 설정 로더
# =============================================================================

def get_query_anchor_config() -> dict:
    """
    Query Anchor 설정 전체 반환

    Returns:
        {
            "coverage_keywords": [...],
            "insurer_only_patterns": [...],
            "intent_extension_keywords": {...}
        }
    """
    return _load_yaml("rules/query_anchor.yaml")


def get_coverage_keywords() -> list[str]:
    """anchor 재설정 트리거가 되는 coverage 키워드 리스트"""
    config = get_query_anchor_config()
    return config.get("coverage_keywords", [])


def get_insurer_only_patterns() -> list[str]:
    """insurer-only 후속 질의 판별 패턴 리스트"""
    config = get_query_anchor_config()
    return config.get("insurer_only_patterns", [])


def get_intent_extension_keywords() -> dict[str, list[str]]:
    """intent 확장 키워드 매핑"""
    config = get_query_anchor_config()
    return config.get("intent_extension_keywords", {})


# =============================================================================
# STEP 3.5: Insurer Guard / Auto-Recovery 설정 로더
# =============================================================================

def get_insurer_defaults_config() -> dict:
    """
    Insurer 기본 정책 설정 전체 반환

    Returns:
        {
            "default_insurers": [...],
            "default_policy_mode": "all",
            "representative_insurers": [...],
            "recovery_messages": {...}
        }
    """
    return _load_yaml("rules/insurer_defaults.yaml")


def get_default_insurers() -> list[str]:
    """기본 insurer 리스트 반환 (insurer 0개 상태 시 사용)"""
    config = get_insurer_defaults_config()
    mode = config.get("default_policy_mode", "all")

    if mode == "representative":
        return config.get("representative_insurers", ["SAMSUNG", "MERITZ"])
    else:
        return config.get("default_insurers", [])


def get_recovery_messages() -> dict[str, str]:
    """보정 메시지 템플릿 반환"""
    config = get_insurer_defaults_config()
    return config.get("recovery_messages", {})


# =============================================================================
# STEP 3.6: Intent Keywords 설정 로더
# =============================================================================

def get_intent_keywords_config() -> dict:
    """
    Intent 키워드 설정 전체 반환

    Returns:
        {
            "compare_trigger_keywords": [...],
            "lookup_force_keywords": [...],
            "ui_events_no_intent_change": [...],
            "compare_multi_insurer_patterns": [...]
        }
    """
    return _load_yaml("rules/intent_keywords.yaml")


def get_compare_trigger_keywords() -> list[str]:
    """비교 의도 트리거 키워드 리스트 반환"""
    config = get_intent_keywords_config()
    return config.get("compare_trigger_keywords", [])


def get_lookup_force_keywords() -> list[str]:
    """lookup 강제 유지 키워드 리스트 반환"""
    config = get_intent_keywords_config()
    return config.get("lookup_force_keywords", [])


def get_ui_events_no_intent_change() -> list[str]:
    """Intent 변경 불가 UI 이벤트 타입 리스트 반환"""
    config = get_intent_keywords_config()
    return config.get("ui_events_no_intent_change", [])


def get_compare_multi_insurer_patterns() -> list[str]:
    """복수 보험사 비교 패턴 리스트 반환"""
    config = get_intent_keywords_config()
    return config.get("compare_multi_insurer_patterns", [])
