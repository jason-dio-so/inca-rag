-- ============================================================================
-- 보험 문서 RAG 시스템 DB 스키마
-- Postgres 15+ / pgvector
--
-- 핵심 규칙:
--   - 보험사 용어: insurer (carrier 사용 금지)
--   - ID 체계: BIGSERIAL/BIGINT 기반
--   - 공통 문서: plan_id IS NULL
--   - 쉬운요약서: doc_type='상품요약서', meta->>'subtype'='easy'
-- ============================================================================

-- ============================================================================
-- Extensions
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- 유사 문자열 검색용

-- ============================================================================
-- 1. CORE TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 보험사 (insurer)
-- 삼성화재, 롯데손보, DB손보 등 보험사 정보
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS insurer (
    insurer_id      BIGSERIAL PRIMARY KEY,
    insurer_code    TEXT UNIQUE NOT NULL,           -- SAMSUNG, LOTTE, DB 등
    insurer_name    TEXT NOT NULL,                  -- 삼성화재, 롯데손보 등
    ins_cd          TEXT,                           -- 신정원 코드 (N01, N02...)
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE insurer IS '보험사 정보';
COMMENT ON COLUMN insurer.insurer_code IS '보험사 영문 코드 (SAMSUNG, LOTTE 등)';
COMMENT ON COLUMN insurer.ins_cd IS '신정원 보험사 코드 (N01, N02 등)';

-- ----------------------------------------------------------------------------
-- 보험 상품 (product)
-- 보험사별 상품 정보, 동일 상품도 버전(예: 2511)으로 구분
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product (
    product_id      BIGSERIAL PRIMARY KEY,
    insurer_id      BIGINT NOT NULL REFERENCES insurer(insurer_id) ON DELETE CASCADE,
    product_name    TEXT NOT NULL,                  -- 상품명
    product_version TEXT,                           -- 버전 (예: 2511)
    product_code    TEXT,                           -- 상품 코드
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- product_version이 NULL일 때도 중복 방지하는 유니크 인덱스
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_unique_insurer_name_version
    ON product (insurer_id, product_name, COALESCE(product_version, ''));

COMMENT ON TABLE product IS '보험 상품 정보';
COMMENT ON COLUMN product.product_version IS '상품 버전 (예: 2511)';

-- ----------------------------------------------------------------------------
-- 상품 플랜 (product_plan)
-- 동일 상품 내 남/여, 연령대, 종/형 등 변형
-- plan_id IS NULL이면 "공통 문서"
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_plan (
    plan_id         BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES product(product_id) ON DELETE CASCADE,
    plan_name       TEXT,                           -- 플랜명 (1종, 2종, 남성형 등)
    gender          TEXT DEFAULT 'U' CHECK (gender IN ('U', 'M', 'F')),  -- U: 공용, M: 남, F: 여
    age_min         INT,                            -- 최소 나이
    age_max         INT,                            -- 최대 나이
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE product_plan IS '상품 플랜 (남/여, 연령대, 종/형 등)';
COMMENT ON COLUMN product_plan.gender IS 'U=공용, M=남성, F=여성';

-- ----------------------------------------------------------------------------
-- 문서 (document)
-- 약관, 사업방법서, 상품요약서, 가입설계서 등 PDF 문서
--
-- 쉬운요약서 처리:
--   doc_type = '상품요약서' (고정, 별도 doc_type 금지)
--   meta->>'subtype' = 'easy' 로만 구분
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document (
    document_id     BIGSERIAL PRIMARY KEY,
    sha256          TEXT UNIQUE NOT NULL,           -- 파일 해시 (중복 방지)
    insurer_id      BIGINT REFERENCES insurer(insurer_id) ON DELETE SET NULL,
    product_id      BIGINT REFERENCES product(product_id) ON DELETE SET NULL,
    plan_id         BIGINT REFERENCES product_plan(plan_id) ON DELETE SET NULL,  -- NULL이면 공통 문서
    doc_type        TEXT NOT NULL CHECK (doc_type IN ('약관', '사업방법서', '상품요약서', '가입설계서', '기타')),
    source_path     TEXT NOT NULL,                  -- 원본 파일 경로
    meta            JSONB DEFAULT '{}'::jsonb,      -- title, effective_date, subtype 등
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE document IS '보험 문서 (약관, 사업방법서, 상품요약서, 가입설계서)';
COMMENT ON COLUMN document.plan_id IS 'NULL이면 공통 문서 (모든 플랜에 적용)';
COMMENT ON COLUMN document.doc_type IS '문서 유형. 쉬운요약서는 상품요약서로 저장하고 meta.subtype=easy로 구분';
COMMENT ON COLUMN document.meta IS 'title, effective_date, subtype(easy/standard) 등';

-- ----------------------------------------------------------------------------
-- 청크 (chunk)
-- 문서를 잘라 만든 최소 검색 단위
-- meta.entities.coverage_code에 담보 표준코드 저장
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunk (
    chunk_id        BIGSERIAL PRIMARY KEY,
    document_id     BIGINT NOT NULL REFERENCES document(document_id) ON DELETE CASCADE,
    insurer_id      BIGINT REFERENCES insurer(insurer_id) ON DELETE SET NULL,
    product_id      BIGINT REFERENCES product(product_id) ON DELETE SET NULL,
    plan_id         BIGINT REFERENCES product_plan(plan_id) ON DELETE SET NULL,
    doc_type        TEXT NOT NULL CHECK (doc_type IN ('약관', '사업방법서', '상품요약서', '가입설계서', '기타')),
    content         TEXT NOT NULL,                  -- 청크 텍스트 내용
    embedding       vector(1536),                   -- pgvector 임베딩 (차원 변경 시 이 숫자 수정)
    page_start      INT,                            -- 시작 페이지 (1-based)
    page_end        INT,                            -- 끝 페이지 (1-based)
    chunk_index     INT,                            -- 문서 내 청크 순번 (0-based)
    meta            JSONB DEFAULT '{}'::jsonb,      -- entities.coverage_code, token_count 등
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE chunk IS '문서 청크 (검색 단위)';
COMMENT ON COLUMN chunk.embedding IS 'pgvector 임베딩. 현재 1536차원 (OpenAI ada-002). 다른 모델 사용 시 차원 변경';
COMMENT ON COLUMN chunk.meta IS 'entities: {coverage_code, coverage_name, ...}, token_count, char_count, section 등';

-- ============================================================================
-- 2. COVERAGE 표준화 TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 담보 표준 코드 (coverage_standard)
-- 신정원 기준 표준 담보 코드
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coverage_standard (
    coverage_code   TEXT PRIMARY KEY,               -- 신정원 코드 (예: A4200_1)
    coverage_name   TEXT NOT NULL,                  -- 표준 담보명 (예: 암진단비(유사암제외))
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE coverage_standard IS '신정원 기준 담보 표준 코드';
COMMENT ON COLUMN coverage_standard.coverage_code IS '신정원 담보 코드 (cre_cvr_cd)';

-- ----------------------------------------------------------------------------
-- 담보 별칭 (coverage_alias)
-- 보험사별 실제 담보명 → 표준코드 매핑
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coverage_alias (
    alias_id        BIGSERIAL PRIMARY KEY,
    insurer_id      BIGINT NOT NULL REFERENCES insurer(insurer_id) ON DELETE CASCADE,
    coverage_code   TEXT NOT NULL REFERENCES coverage_standard(coverage_code) ON DELETE CASCADE,
    raw_name        TEXT NOT NULL,                  -- 원본 담보명 (가입설계서 기준)
    raw_name_norm   TEXT NOT NULL,                  -- 정규화된 담보명 (검색용, 소문자/공백정리)
    source_doc_type TEXT NOT NULL DEFAULT '가입설계서',  -- 출처 문서 유형
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(insurer_id, raw_name_norm, source_doc_type)
);

COMMENT ON TABLE coverage_alias IS '보험사별 담보명 → 표준코드 매핑';
COMMENT ON COLUMN coverage_alias.raw_name_norm IS '정규화된 담보명 (검색 매칭용). 특수문자→공백, 소문자, 공백정리';

-- ============================================================================
-- 3. INDEXES
-- ============================================================================

-- Insurer
CREATE INDEX IF NOT EXISTS idx_insurer_code ON insurer(insurer_code);
CREATE INDEX IF NOT EXISTS idx_insurer_ins_cd ON insurer(ins_cd);

-- Product
CREATE INDEX IF NOT EXISTS idx_product_insurer ON product(insurer_id);
CREATE INDEX IF NOT EXISTS idx_product_name ON product(product_name);

-- Product Plan
CREATE INDEX IF NOT EXISTS idx_plan_product ON product_plan(product_id);
CREATE INDEX IF NOT EXISTS idx_plan_gender ON product_plan(gender);

-- Document
CREATE INDEX IF NOT EXISTS idx_document_insurer ON document(insurer_id);
CREATE INDEX IF NOT EXISTS idx_document_product ON document(product_id);
CREATE INDEX IF NOT EXISTS idx_document_plan ON document(plan_id);
CREATE INDEX IF NOT EXISTS idx_document_doc_type ON document(doc_type);
CREATE INDEX IF NOT EXISTS idx_document_sha256 ON document(sha256);

-- Document: subtype 필터용 (쉬운요약서 조회)
CREATE INDEX IF NOT EXISTS idx_document_meta_subtype ON document((meta->>'subtype'));

-- Chunk
CREATE INDEX IF NOT EXISTS idx_chunk_document ON chunk(document_id);
CREATE INDEX IF NOT EXISTS idx_chunk_insurer ON chunk(insurer_id);
CREATE INDEX IF NOT EXISTS idx_chunk_product ON chunk(product_id);
CREATE INDEX IF NOT EXISTS idx_chunk_plan ON chunk(plan_id);
CREATE INDEX IF NOT EXISTS idx_chunk_doc_type ON chunk(doc_type);

-- Chunk: coverage_code 필터용
CREATE INDEX IF NOT EXISTS idx_chunk_meta_coverage_code ON chunk((meta->'entities'->>'coverage_code'));

-- Chunk: 벡터 검색 인덱스
-- ============================================================================
-- 주의사항:
--   1. embedding이 NULL인 row가 있으면 인덱스 문제 발생 가능
--   2. 데이터 적재 후 인덱스 생성 권장 (초기 빈 테이블에서는 비효율)
--   3. HNSW는 pgvector 0.5+ 필요
--
-- 방식 비교:
--   HNSW: 검색 빠름, 인덱스 빌드 느림, 메모리 사용 많음
--   IVFFlat: 빌드 빠름, 검색 약간 느림, 데이터 1만건 이상 후 생성 권장
-- ============================================================================

-- HNSW 부분 인덱스 (embedding이 NULL이 아닌 row만)
-- pgvector 0.5+에서 WHERE 절 지원
CREATE INDEX IF NOT EXISTS idx_chunk_embedding_hnsw
    ON chunk USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

-- ============================================================================
-- [대안] IVFFlat 인덱스 (HNSW 실패 시 또는 pgvector < 0.5 환경)
-- 데이터 1만건 이상 적재 후 생성 권장
-- ============================================================================
-- DROP INDEX IF EXISTS idx_chunk_embedding_hnsw;
-- CREATE INDEX IF NOT EXISTS idx_chunk_embedding_ivfflat
--     ON chunk USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100)
--     WHERE embedding IS NOT NULL;
--
-- [참고] IVFFlat lists 값 가이드:
--   - 1만건 미만: lists = 100
--   - 10만건: lists = 300~500
--   - 100만건: lists = 1000

-- Coverage Alias
CREATE INDEX IF NOT EXISTS idx_coverage_alias_insurer ON coverage_alias(insurer_id);
CREATE INDEX IF NOT EXISTS idx_coverage_alias_code ON coverage_alias(coverage_code);
CREATE INDEX IF NOT EXISTS idx_coverage_alias_insurer_doctype ON coverage_alias(insurer_id, source_doc_type);
CREATE INDEX IF NOT EXISTS idx_coverage_alias_raw_name_norm ON coverage_alias(raw_name_norm);

-- Coverage Alias: pg_trgm 기반 유사 검색 (퍼지 매칭)
CREATE INDEX IF NOT EXISTS idx_coverage_alias_raw_name_trgm
    ON coverage_alias USING gin (raw_name_norm gin_trgm_ops);

-- ============================================================================
-- 4. TRIGGERS (updated_at 자동 갱신)
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Insurer
DROP TRIGGER IF EXISTS trg_insurer_updated_at ON insurer;
CREATE TRIGGER trg_insurer_updated_at
    BEFORE UPDATE ON insurer
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Product
DROP TRIGGER IF EXISTS trg_product_updated_at ON product;
CREATE TRIGGER trg_product_updated_at
    BEFORE UPDATE ON product
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Product Plan
DROP TRIGGER IF EXISTS trg_product_plan_updated_at ON product_plan;
CREATE TRIGGER trg_product_plan_updated_at
    BEFORE UPDATE ON product_plan
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Document
DROP TRIGGER IF EXISTS trg_document_updated_at ON document;
CREATE TRIGGER trg_document_updated_at
    BEFORE UPDATE ON document
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Coverage Standard
DROP TRIGGER IF EXISTS trg_coverage_standard_updated_at ON coverage_standard;
CREATE TRIGGER trg_coverage_standard_updated_at
    BEFORE UPDATE ON coverage_standard
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Coverage Alias
DROP TRIGGER IF EXISTS trg_coverage_alias_updated_at ON coverage_alias;
CREATE TRIGGER trg_coverage_alias_updated_at
    BEFORE UPDATE ON coverage_alias
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 5. INITIAL DATA
-- ============================================================================

-- 보험사 기초 데이터 (8개사)
INSERT INTO insurer (insurer_code, insurer_name, ins_cd) VALUES
    ('MERITZ',   '메리츠', 'N01'),
    ('HANWHA',   '한화',   'N02'),
    ('LOTTE',    '롯데',   'N03'),
    ('HEUNGKUK', '흥국',   'N05'),
    ('SAMSUNG',  '삼성',   'N08'),
    ('HYUNDAI',  '현대',   'N09'),
    ('KB',       'KB',     'N10'),
    ('DB',       'DB',     'N13')
ON CONFLICT (insurer_code) DO UPDATE SET
    insurer_name = EXCLUDED.insurer_name,
    ins_cd = EXCLUDED.ins_cd;

-- ============================================================================
-- 6. HELPER VIEWS (선택)
-- ============================================================================

-- 쉬운요약서 문서 조회용 뷰
CREATE OR REPLACE VIEW v_easy_summary AS
SELECT
    d.*,
    i.insurer_code,
    i.insurer_name,
    p.product_name,
    p.product_version
FROM document d
LEFT JOIN insurer i ON d.insurer_id = i.insurer_id
LEFT JOIN product p ON d.product_id = p.product_id
WHERE d.doc_type = '상품요약서'
  AND d.meta->>'subtype' = 'easy';

COMMENT ON VIEW v_easy_summary IS '쉬운요약서 문서 목록 (doc_type=상품요약서 AND meta.subtype=easy)';

-- 청크 + coverage_code 조회용 뷰
CREATE OR REPLACE VIEW v_chunk_with_coverage AS
SELECT
    c.*,
    c.meta->'entities'->>'coverage_code' AS coverage_code,
    c.meta->'entities'->>'coverage_name' AS coverage_name,
    i.insurer_code,
    d.doc_type AS document_doc_type
FROM chunk c
LEFT JOIN insurer i ON c.insurer_id = i.insurer_id
LEFT JOIN document d ON c.document_id = d.document_id;

COMMENT ON VIEW v_chunk_with_coverage IS '청크 + coverage_code 추출 뷰';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
