"""
Coverage Ontology v0.1

담보 표준코드 및 alias 정의
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CoverageCode:
    """담보 코드 정의"""

    code: str
    name: str
    aliases: list[str]


# Coverage Ontology v0.1
COVERAGE_ONTOLOGY: list[CoverageCode] = [
    # 암 관련
    CoverageCode(
        code="CIS_CARCINOMA",
        name="제자리암",
        aliases=["제자리암", "상피내암", "CIS", "carcinoma in situ", "제자리 암"],
    ),
    CoverageCode(
        code="BORDERLINE_TUMOR",
        name="경계성종양",
        aliases=["경계성종양", "경계성 종양", "borderline tumor", "경계성암"],
    ),
    CoverageCode(
        code="CANCER_DIAG",
        name="암진단비",
        aliases=["암진단비", "암 진단비", "일반암", "암진단", "암 진단", "일반암진단"],
    ),
    CoverageCode(
        code="THYROID_CANCER",
        name="갑상선암",
        aliases=["갑상선암", "갑상선 암", "thyroid cancer", "갑상샘암"],
    ),
    CoverageCode(
        code="BREAST_CANCER",
        name="유방암",
        aliases=["유방암", "유방 암", "breast cancer"],
    ),
    CoverageCode(
        code="PROSTATE_CANCER",
        name="전립선암",
        aliases=["전립선암", "전립선 암", "prostate cancer"],
    ),
    CoverageCode(
        code="LUNG_CANCER",
        name="폐암",
        aliases=["폐암", "폐 암", "lung cancer"],
    ),
    CoverageCode(
        code="LIVER_CANCER",
        name="간암",
        aliases=["간암", "간 암", "liver cancer", "간세포암"],
    ),
    CoverageCode(
        code="STOMACH_CANCER",
        name="위암",
        aliases=["위암", "위 암", "stomach cancer", "gastric cancer"],
    ),
    CoverageCode(
        code="COLORECTAL_CANCER",
        name="대장암",
        aliases=["대장암", "대장 암", "직장암", "결장암", "colorectal cancer"],
    ),
    # 뇌/심장 관련
    CoverageCode(
        code="STROKE",
        name="뇌졸중",
        aliases=["뇌졸중", "뇌졸증", "stroke", "뇌출혈", "뇌경색"],
    ),
    CoverageCode(
        code="ACUTE_MI",
        name="급성심근경색",
        aliases=[
            "급성심근경색",
            "급성 심근경색",
            "심근경색",
            "acute myocardial infarction",
            "AMI",
        ],
    ),
    CoverageCode(
        code="CEREBRAL_HEMORRHAGE",
        name="뇌출혈",
        aliases=["뇌출혈", "뇌 출혈", "cerebral hemorrhage", "두개내출혈"],
    ),
    CoverageCode(
        code="CEREBRAL_INFARCTION",
        name="뇌경색",
        aliases=["뇌경색", "뇌 경색", "cerebral infarction"],
    ),
    # 수술/입원 관련
    CoverageCode(
        code="HOSPITALIZATION",
        name="입원일당",
        aliases=["입원일당", "입원 일당", "입원비", "입원급여금"],
    ),
    CoverageCode(
        code="SURGERY",
        name="수술비",
        aliases=["수술비", "수술 비", "수술급여금", "수술보험금"],
    ),
    CoverageCode(
        code="OUTPATIENT",
        name="통원치료비",
        aliases=["통원치료비", "통원 치료비", "통원비", "외래진료비"],
    ),
    # 사망/장해 관련
    CoverageCode(
        code="DEATH_BENEFIT",
        name="사망보험금",
        aliases=["사망보험금", "사망 보험금", "사망급여금", "일반사망"],
    ),
    CoverageCode(
        code="DISABILITY",
        name="장해급여금",
        aliases=["장해급여금", "장해 급여금", "후유장해", "장해보험금"],
    ),
    # 진단비 관련
    CoverageCode(
        code="DIAGNOSIS_BENEFIT",
        name="진단비",
        aliases=["진단비", "진단 비", "진단급여금", "진단보험금"],
    ),
    CoverageCode(
        code="CI_BENEFIT",
        name="중대한질병",
        aliases=["중대한질병", "중대한 질병", "CI", "critical illness"],
    ),
    # 실손 관련
    CoverageCode(
        code="ACTUAL_EXPENSE",
        name="실손의료비",
        aliases=["실손의료비", "실손 의료비", "실비", "실손보험", "의료실비"],
    ),
]


def get_coverage_by_code(code: str) -> CoverageCode | None:
    """코드로 Coverage 조회"""
    for cov in COVERAGE_ONTOLOGY:
        if cov.code == code:
            return cov
    return None


def get_all_coverage_codes() -> list[str]:
    """모든 coverage code 목록 반환"""
    return [cov.code for cov in COVERAGE_ONTOLOGY]


def get_alias_to_code_map() -> dict[str, CoverageCode]:
    """
    alias → CoverageCode 매핑 생성
    긴 alias 우선 (더 구체적인 매칭)
    """
    alias_map: dict[str, CoverageCode] = {}
    for cov in COVERAGE_ONTOLOGY:
        for alias in cov.aliases:
            alias_lower = alias.lower()
            # 기존 매핑이 없거나, 현재 alias가 더 길면 덮어쓰기
            if alias_lower not in alias_map:
                alias_map[alias_lower] = cov
    return alias_map
