"""
Step I-1: Plan Detector 모듈

문서 경로/파일명/메타에서 성별(M/F)·나이구간을 감지하여
product_plan에서 매칭되는 plan_id를 반환
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal

import psycopg
from psycopg.rows import dict_row


@dataclass
class DetectedPlanInfo:
    """감지된 plan 정보"""
    gender: Literal["M", "F", "U"] | None = None
    age_min: int | None = None
    age_max: int | None = None
    detection_source: str | None = None  # 감지 소스 (파일명, 폴더명, 메타)


@dataclass
class PlanDetectorResult:
    """Plan detector 결과"""
    plan_id: int | None
    detected_info: DetectedPlanInfo
    reason: str


# =============================================================================
# 성별 감지 패턴
# =============================================================================

# 남성 패턴
MALE_PATTERNS = [
    r"남성",
    r"남자",
    r"\b남\b",
    r"\(남\)",
    r"_남_",
    r"-남-",
    r"남형",
    r"\bmale\b",
    r"\bM형\b",
    r"남성형",
]

# 여성 패턴
FEMALE_PATTERNS = [
    r"여성",
    r"여자",
    r"\b여\b",
    r"\(여\)",
    r"_여_",
    r"-여-",
    r"여형",
    r"\bfemale\b",
    r"\bF형\b",
    r"여성형",
]

# 컴파일된 패턴
MALE_REGEX = re.compile("|".join(MALE_PATTERNS), re.IGNORECASE)
FEMALE_REGEX = re.compile("|".join(FEMALE_PATTERNS), re.IGNORECASE)


# =============================================================================
# 나이 감지 패턴
# =============================================================================

# 나이 범위 패턴들
AGE_PATTERNS = [
    # "40세이하", "40세 이하"
    (r"(\d+)\s*세\s*이하", lambda m: (None, int(m.group(1)))),
    # "41세이상", "41세 이상"
    (r"(\d+)\s*세\s*이상", lambda m: (int(m.group(1)), None)),
    # "20-40세", "20~40세"
    (r"(\d+)\s*[-~]\s*(\d+)\s*세", lambda m: (int(m.group(1)), int(m.group(2)))),
    # "만40세", "만 40세"
    (r"만\s*(\d+)\s*세", lambda m: (int(m.group(1)), int(m.group(1)))),
    # "40대", "30대"
    (r"(\d)0\s*대", lambda m: (int(m.group(1)) * 10, int(m.group(1)) * 10 + 9)),
    # "40세미만"
    (r"(\d+)\s*세\s*미만", lambda m: (None, int(m.group(1)) - 1)),
    # "40세초과"
    (r"(\d+)\s*세\s*초과", lambda m: (int(m.group(1)) + 1, None)),
]


def detect_gender(text: str) -> Literal["M", "F"] | None:
    """
    텍스트에서 성별 감지

    Args:
        text: 검사할 텍스트

    Returns:
        "M", "F", or None
    """
    if not text:
        return None

    # 남성 먼저 체크
    if MALE_REGEX.search(text):
        return "M"

    # 여성 체크
    if FEMALE_REGEX.search(text):
        return "F"

    return None


def detect_age_range(text: str) -> tuple[int | None, int | None]:
    """
    텍스트에서 나이 범위 감지

    Args:
        text: 검사할 텍스트

    Returns:
        (age_min, age_max) - None이면 제한 없음
    """
    if not text:
        return None, None

    for pattern, extractor in AGE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return extractor(match)

    return None, None


def detect_from_path(source_path: str) -> DetectedPlanInfo:
    """
    파일 경로에서 plan 정보 감지

    Args:
        source_path: 파일 경로

    Returns:
        DetectedPlanInfo
    """
    if not source_path:
        return DetectedPlanInfo()

    # 파일명과 폴더명 분리
    filename = os.path.basename(source_path)
    dirname = os.path.dirname(source_path)

    # 파일명에서 먼저 감지
    gender = detect_gender(filename)
    age_min, age_max = detect_age_range(filename)
    detection_source = "filename"

    # 파일명에서 못 찾으면 폴더명에서 감지
    if gender is None and age_min is None and age_max is None:
        gender = detect_gender(dirname)
        age_min, age_max = detect_age_range(dirname)
        if gender is not None or age_min is not None or age_max is not None:
            detection_source = "dirname"
        else:
            detection_source = None

    return DetectedPlanInfo(
        gender=gender,
        age_min=age_min,
        age_max=age_max,
        detection_source=detection_source,
    )


def detect_from_meta(meta: dict | None) -> DetectedPlanInfo:
    """
    문서 메타데이터에서 plan 정보 감지

    Args:
        meta: 문서 메타데이터

    Returns:
        DetectedPlanInfo
    """
    if not meta:
        return DetectedPlanInfo()

    # meta에서 직접 gender/age 필드 확인
    gender = meta.get("gender")
    if gender in ("M", "F"):
        return DetectedPlanInfo(
            gender=gender,
            age_min=meta.get("age_min"),
            age_max=meta.get("age_max"),
            detection_source="meta_field",
        )

    # meta의 title 필드에서 감지
    title = meta.get("title", "")
    if title:
        gender = detect_gender(title)
        age_min, age_max = detect_age_range(title)
        if gender is not None or age_min is not None or age_max is not None:
            return DetectedPlanInfo(
                gender=gender,
                age_min=age_min,
                age_max=age_max,
                detection_source="meta_title",
            )

    return DetectedPlanInfo()


def detect_plan_info(
    source_path: str | None,
    doc_title: str | None,
    meta: dict | None,
) -> DetectedPlanInfo:
    """
    여러 소스에서 plan 정보 감지 (우선순위: meta > doc_title > path)

    Args:
        source_path: 파일 경로
        doc_title: 문서 제목
        meta: 메타데이터

    Returns:
        DetectedPlanInfo
    """
    # 1. meta에서 먼저 시도
    result = detect_from_meta(meta)
    if result.gender is not None or result.age_min is not None:
        return result

    # 2. doc_title에서 시도
    if doc_title:
        gender = detect_gender(doc_title)
        age_min, age_max = detect_age_range(doc_title)
        if gender is not None or age_min is not None or age_max is not None:
            return DetectedPlanInfo(
                gender=gender,
                age_min=age_min,
                age_max=age_max,
                detection_source="doc_title",
            )

    # 3. source_path에서 시도
    result = detect_from_path(source_path or "")
    return result


def find_matching_plan_id(
    conn,
    insurer_code: str,
    detected_info: DetectedPlanInfo,
) -> int | None:
    """
    감지된 정보로 product_plan에서 매칭되는 plan_id 조회

    Args:
        conn: DB connection (psycopg Connection)
        insurer_code: 보험사 코드
        detected_info: 감지된 plan 정보

    Returns:
        plan_id or None
    """
    if detected_info.gender is None and detected_info.age_min is None and detected_info.age_max is None:
        return None

    with conn.cursor(row_factory=dict_row) as cur:
        # product_id 조회
        cur.execute("""
            SELECT p.product_id
            FROM product p
            JOIN insurer i ON p.insurer_id = i.insurer_id
            WHERE i.insurer_code = %s
            ORDER BY p.product_id
            LIMIT 1
        """, (insurer_code,))

        product_row = cur.fetchone()
        if not product_row:
            return None

        product_id = product_row["product_id"]

        # plan 매칭 쿼리
        # gender 조건
        gender_condition = ""
        gender_params: list = []
        if detected_info.gender:
            gender_condition = "AND (pp.gender = %s OR pp.gender = 'U')"
            gender_params = [detected_info.gender]
        else:
            gender_condition = ""
            gender_params = []

        # age 조건
        age_conditions: list[str] = []
        age_params: list = []
        if detected_info.age_min is not None:
            # 감지된 age_min이 plan의 범위 내에 있어야 함
            age_conditions.append("(pp.age_min IS NULL OR pp.age_min <= %s)")
            age_params.append(detected_info.age_min)
        if detected_info.age_max is not None:
            # 감지된 age_max가 plan의 범위 내에 있어야 함
            age_conditions.append("(pp.age_max IS NULL OR pp.age_max >= %s)")
            age_params.append(detected_info.age_max)

        age_condition = " AND ".join(age_conditions) if age_conditions else "TRUE"

        query = f"""
            SELECT pp.plan_id, pp.plan_name, pp.gender, pp.age_min, pp.age_max,
                   CASE WHEN pp.gender = %s THEN 2 WHEN pp.gender = 'U' THEN 1 ELSE 0 END as gender_score,
                   COALESCE(pp.age_max, 999) - COALESCE(pp.age_min, 0) as age_range
            FROM product_plan pp
            WHERE pp.product_id = %s
              {gender_condition}
              AND {age_condition}
            ORDER BY gender_score DESC, age_range ASC
            LIMIT 1
        """

        params = tuple([detected_info.gender or "U", product_id] + gender_params + age_params)
        cur.execute(query, params)

        plan_row = cur.fetchone()
        if plan_row:
            return plan_row["plan_id"]

        return None


def detect_plan_id(
    conn,
    insurer_code: str,
    source_path: str | None,
    doc_title: str | None,
    meta: dict | None,
) -> PlanDetectorResult:
    """
    문서에서 plan_id 자동 감지

    Args:
        conn: DB connection
        insurer_code: 보험사 코드
        source_path: 파일 경로
        doc_title: 문서 제목
        meta: 메타데이터

    Returns:
        PlanDetectorResult
    """
    # 1. 정보 감지
    detected_info = detect_plan_info(source_path, doc_title, meta)

    # 2. 감지된 정보 없으면 None
    if detected_info.gender is None and detected_info.age_min is None and detected_info.age_max is None:
        return PlanDetectorResult(
            plan_id=None,
            detected_info=detected_info,
            reason="no_plan_info_detected",
        )

    # 3. plan_id 조회
    plan_id = find_matching_plan_id(conn, insurer_code, detected_info)

    if plan_id:
        reason_parts = []
        if detected_info.gender:
            reason_parts.append(f"gender={detected_info.gender}")
        if detected_info.age_min is not None or detected_info.age_max is not None:
            age_str = f"{detected_info.age_min or '*'}-{detected_info.age_max or '*'}"
            reason_parts.append(f"age={age_str}")
        if detected_info.detection_source:
            reason_parts.append(f"source={detected_info.detection_source}")

        return PlanDetectorResult(
            plan_id=plan_id,
            detected_info=detected_info,
            reason=", ".join(reason_parts),
        )
    else:
        return PlanDetectorResult(
            plan_id=None,
            detected_info=detected_info,
            reason=f"no_matching_plan (detected: gender={detected_info.gender}, age={detected_info.age_min}-{detected_info.age_max})",
        )
