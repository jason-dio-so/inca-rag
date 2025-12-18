-- =============================================================================
-- U-4.8 Migration: Comparison Slots v0.1
-- =============================================================================
--
-- 이 마이그레이션은 슬롯 결과를 캐싱하기 위한 테이블을 추가합니다.
-- v0.1에서는 on-the-fly 계산이 주이며, 이 테이블은 선택적 캐싱용입니다.
--
-- 실행: psql -U postgres -d inca_rag -f db/migrations/20251218_add_comparison_slots.sql
-- =============================================================================

-- 슬롯 결과 캐시 테이블 (선택적)
CREATE TABLE IF NOT EXISTS comparison_slot_cache (
    cache_id SERIAL PRIMARY KEY,

    -- 대상 식별
    insurer_id INTEGER NOT NULL REFERENCES insurer(insurer_id),
    product_id INTEGER REFERENCES product(product_id),
    plan_id INTEGER REFERENCES product_plan(plan_id),
    coverage_code VARCHAR(50) NOT NULL,

    -- 슬롯 정보
    slot_key VARCHAR(50) NOT NULL,
    slot_value TEXT,
    slot_unit VARCHAR(20),
    normalized_value NUMERIC,
    confidence VARCHAR(20) DEFAULT 'medium',

    -- 근거 참조 (JSONB)
    evidence_refs JSONB DEFAULT '[]'::jsonb,

    -- 메타
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 유니크 제약
    CONSTRAINT uq_slot_cache UNIQUE (insurer_id, product_id, plan_id, coverage_code, slot_key)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_slot_cache_insurer_coverage
    ON comparison_slot_cache(insurer_id, coverage_code);

CREATE INDEX IF NOT EXISTS idx_slot_cache_slot_key
    ON comparison_slot_cache(slot_key);

-- 코멘트
COMMENT ON TABLE comparison_slot_cache IS 'U-4.8: 슬롯 결과 캐시 (선택적, on-the-fly 계산 우선)';
COMMENT ON COLUMN comparison_slot_cache.slot_key IS '슬롯 키 (payout_amount, existence_status 등)';
COMMENT ON COLUMN comparison_slot_cache.evidence_refs IS '근거 참조 [{document_id, page_start, chunk_id}]';
