"""
Step I: Plan 자동 선택 모듈

age/gender 정보를 바탕으로 product_plan에서 최적의 plan을 선택
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass
class SelectedPlan:
    """선택된 plan 정보"""
    insurer_code: str
    product_id: int
    plan_id: int | None
    plan_name: str | None
    reason: str


def select_plan_for_insurer(
    conn,
    insurer_code: str,
    age: int | None,
    gender: Literal["M", "F"] | None,
) -> SelectedPlan:
    """
    보험사별 최적 plan 선택

    우선순위:
    1. gender 정확 일치 (M/F) > U
    2. age 범위가 더 좁은 plan 우선
    3. plan_name 존재 (명시적) 우선

    Args:
        conn: DB connection
        insurer_code: 보험사 코드
        age: 나이 (None이면 무시)
        gender: 성별 (None이면 무시)

    Returns:
        SelectedPlan
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 먼저 해당 보험사의 product_id를 찾음
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
            return SelectedPlan(
                insurer_code=insurer_code,
                product_id=0,
                plan_id=None,
                plan_name=None,
                reason="no_product_found",
            )

        product_id = product_row["product_id"]

        # age/gender가 모두 없으면 plan 선택 없음 (공통 문서만)
        if age is None and gender is None:
            return SelectedPlan(
                insurer_code=insurer_code,
                product_id=product_id,
                plan_id=None,
                plan_name=None,
                reason="no_age_gender_provided",
            )

        # plan 후보 조회
        # gender: 요청과 일치 또는 U(공용)
        # age: 범위 내 또는 범위가 NULL (무제한)
        query = """
            SELECT
                pp.plan_id,
                pp.plan_name,
                pp.gender,
                pp.age_min,
                pp.age_max,
                CASE
                    WHEN pp.gender = %s THEN 2  -- 정확 일치
                    WHEN pp.gender = 'U' THEN 1  -- 공용
                    ELSE 0
                END as gender_score,
                COALESCE(pp.age_max, 999) - COALESCE(pp.age_min, 0) as age_range,
                CASE WHEN pp.plan_name IS NOT NULL THEN 1 ELSE 0 END as has_name
            FROM product_plan pp
            WHERE pp.product_id = %s
              AND (pp.gender = %s OR pp.gender = 'U')
              AND (pp.age_min IS NULL OR pp.age_min <= %s)
              AND (pp.age_max IS NULL OR pp.age_max >= %s)
            ORDER BY
                gender_score DESC,      -- gender 정확 일치 우선
                age_range ASC,          -- age 범위 좁은 것 우선
                has_name DESC,          -- plan_name 있는 것 우선
                pp.plan_id ASC
            LIMIT 1
        """

        effective_gender = gender or "U"
        effective_age = age if age is not None else 0

        cur.execute(query, (
            effective_gender,
            product_id,
            effective_gender,
            effective_age,
            effective_age,
        ))

        plan_row = cur.fetchone()

        if plan_row:
            reason_parts = []
            if plan_row["gender"] == gender:
                reason_parts.append(f"gender_match({gender})")
            elif plan_row["gender"] == "U":
                reason_parts.append("gender_universal")

            if plan_row["age_min"] is not None or plan_row["age_max"] is not None:
                age_range = f"{plan_row['age_min'] or '*'}-{plan_row['age_max'] or '*'}"
                reason_parts.append(f"age_range({age_range})")

            if plan_row["plan_name"]:
                reason_parts.append(f"plan_name({plan_row['plan_name']})")

            return SelectedPlan(
                insurer_code=insurer_code,
                product_id=product_id,
                plan_id=plan_row["plan_id"],
                plan_name=plan_row["plan_name"],
                reason=", ".join(reason_parts) if reason_parts else "default_match",
            )
        else:
            # 조건에 맞는 plan이 없으면 공통 문서만
            return SelectedPlan(
                insurer_code=insurer_code,
                product_id=product_id,
                plan_id=None,
                plan_name=None,
                reason="no_matching_plan",
            )


def select_plans_for_insurers(
    conn,
    insurers: list[str],
    age: int | None,
    gender: Literal["M", "F"] | None,
) -> dict[str, SelectedPlan]:
    """
    여러 보험사에 대해 plan 선택

    Args:
        conn: DB connection
        insurers: 보험사 코드 리스트
        age: 나이
        gender: 성별

    Returns:
        insurer_code -> SelectedPlan 매핑
    """
    result = {}
    for insurer_code in insurers:
        result[insurer_code] = select_plan_for_insurer(conn, insurer_code, age, gender)
    return result


def get_plan_ids_for_retrieval(
    selected_plans: dict[str, SelectedPlan],
) -> dict[str, int | None]:
    """
    retrieval에 사용할 plan_id 매핑 추출

    Args:
        selected_plans: insurer_code -> SelectedPlan

    Returns:
        insurer_code -> plan_id (None이면 공통 문서만)
    """
    return {
        insurer_code: plan.plan_id
        for insurer_code, plan in selected_plans.items()
    }
