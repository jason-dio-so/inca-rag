#!/usr/bin/env python3
"""
Step I: Product Plan 테스트 데이터 Seed

테스트용으로 최소 3개 보험사(SAMSUNG/LOTTE/DB)에 대해
M/F plan 2개 + U plan 1개 샘플 insert

Usage:
    python tools/seed_product_plans.py
"""

import os
import sys

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag"
    )


def seed_product_plans():
    """Product Plan 테스트 데이터 seed"""
    conn = psycopg.connect(get_db_url(), row_factory=dict_row)

    try:
        with conn.cursor() as cur:
            # 대상 보험사
            target_insurers = ["SAMSUNG", "LOTTE", "DB"]

            for insurer_code in target_insurers:
                # 1. insurer 확인
                cur.execute("""
                    SELECT insurer_id FROM insurer WHERE insurer_code = %s
                """, (insurer_code,))
                insurer_row = cur.fetchone()

                if not insurer_row:
                    print(f"[SKIP] {insurer_code}: insurer not found")
                    continue

                insurer_id = insurer_row["insurer_id"]

                # 2. product 확인 (없으면 생성)
                cur.execute("""
                    SELECT product_id FROM product WHERE insurer_id = %s LIMIT 1
                """, (insurer_id,))
                product_row = cur.fetchone()

                if product_row:
                    product_id = product_row["product_id"]
                    print(f"[OK] {insurer_code}: using existing product_id={product_id}")
                else:
                    # product 생성
                    cur.execute("""
                        INSERT INTO product (insurer_id, product_name, product_code, version)
                        VALUES (%s, %s, %s, %s)
                        RETURNING product_id
                    """, (insurer_id, f"{insurer_code} 테스트상품", f"TEST_{insurer_code}", "2511"))
                    product_id = cur.fetchone()["product_id"]
                    print(f"[NEW] {insurer_code}: created product_id={product_id}")

                # 3. 기존 plan 확인
                cur.execute("""
                    SELECT COUNT(*) as cnt FROM product_plan WHERE product_id = %s
                """, (product_id,))
                plan_count = cur.fetchone()["cnt"]

                if plan_count > 0:
                    print(f"  - {plan_count} plans already exist, skipping seed")
                    continue

                # 4. Plan seed (M/F/U)
                plans = [
                    # 남성 플랜 (40세 이하)
                    {
                        "plan_name": "남성-40세이하",
                        "gender": "M",
                        "age_min": 0,
                        "age_max": 40,
                    },
                    # 남성 플랜 (41세 이상)
                    {
                        "plan_name": "남성-41세이상",
                        "gender": "M",
                        "age_min": 41,
                        "age_max": 99,
                    },
                    # 여성 플랜 (40세 이하)
                    {
                        "plan_name": "여성-40세이하",
                        "gender": "F",
                        "age_min": 0,
                        "age_max": 40,
                    },
                    # 여성 플랜 (41세 이상)
                    {
                        "plan_name": "여성-41세이상",
                        "gender": "F",
                        "age_min": 41,
                        "age_max": 99,
                    },
                    # 공용 플랜 (연령 제한 없음)
                    {
                        "plan_name": "공용-전연령",
                        "gender": "U",
                        "age_min": None,
                        "age_max": None,
                    },
                ]

                for plan in plans:
                    cur.execute("""
                        INSERT INTO product_plan (product_id, plan_name, gender, age_min, age_max)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING plan_id
                    """, (
                        product_id,
                        plan["plan_name"],
                        plan["gender"],
                        plan["age_min"],
                        plan["age_max"],
                    ))
                    plan_id = cur.fetchone()["plan_id"]
                    print(f"  + Created plan: {plan['plan_name']} (id={plan_id})")

            conn.commit()
            print("\n[DONE] Product plans seeded successfully")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e}")
        sys.exit(1)
    finally:
        conn.close()


def verify_seed():
    """Seed 결과 검증"""
    conn = psycopg.connect(get_db_url(), row_factory=dict_row)

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    i.insurer_code,
                    p.product_id,
                    pp.plan_id,
                    pp.plan_name,
                    pp.gender,
                    pp.age_min,
                    pp.age_max
                FROM product_plan pp
                JOIN product p ON pp.product_id = p.product_id
                JOIN insurer i ON p.insurer_id = i.insurer_id
                WHERE i.insurer_code IN ('SAMSUNG', 'LOTTE', 'DB')
                ORDER BY i.insurer_code, pp.plan_id
            """)

            rows = cur.fetchall()
            print(f"\n=== Verification: {len(rows)} plans found ===")
            print(f"{'Insurer':<10} {'ProductID':<10} {'PlanID':<8} {'Name':<20} {'Gender':<8} {'Age'}")
            print("-" * 80)
            for row in rows:
                age_range = f"{row['age_min'] or '*'}-{row['age_max'] or '*'}"
                print(f"{row['insurer_code']:<10} {row['product_id']:<10} {row['plan_id']:<8} {row['plan_name']:<20} {row['gender']:<8} {age_range}")

    finally:
        conn.close()


if __name__ == "__main__":
    print("=== Seeding Product Plans ===\n")
    seed_product_plans()
    verify_seed()
