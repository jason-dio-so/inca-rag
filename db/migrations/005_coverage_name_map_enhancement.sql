-- U-5.0-A: Coverage Name Mapping Table Enhancement
-- 목적: coverage_alias 및 coverage_standard 테이블을 Coverage Resolution의 Single Source of Truth로 승격
--
-- 핵심 원칙:
-- 1. Coverage Resolution은 테이블 우선 (LLM/rule은 보조)
-- 2. Subtype은 coverage_code에 절대 종속
-- 3. Rule의 기준 키는 coverage_code + semantic_scope

-- ============================================================================
-- 1. coverage_standard 테이블 확장: semantic_scope 추가
-- ============================================================================

ALTER TABLE coverage_standard
ADD COLUMN IF NOT EXISTS semantic_scope TEXT DEFAULT 'UNKNOWN';

COMMENT ON COLUMN coverage_standard.semantic_scope IS
'의미적 범위: DIAGNOSIS(진단비), SURGERY(수술비), HOSPITALIZATION(입원비), DEATH(사망), INJURY(상해), UNKNOWN';

-- ============================================================================
-- 2. coverage_alias 테이블 확장: is_primary, confidence 추가
-- ============================================================================

ALTER TABLE coverage_alias
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT false;

ALTER TABLE coverage_alias
ADD COLUMN IF NOT EXISTS confidence NUMERIC(3,2) DEFAULT 0.8;

COMMENT ON COLUMN coverage_alias.is_primary IS '해당 보험사의 대표 담보명 여부';
COMMENT ON COLUMN coverage_alias.confidence IS '매핑 신뢰도 (0.00 ~ 1.00). 신정원 기준=1.0, 수기=0.9, 추정=0.7';

-- ============================================================================
-- 3. coverage_standard.semantic_scope 데이터 초기화 (coverage_domain.yaml 기반)
-- ============================================================================

-- 암 계열 (CANCER)
UPDATE coverage_standard SET semantic_scope = 'CANCER' WHERE coverage_code IN (
    'A4209', 'A4200_1', 'A4299_1', 'A4210', 'A4302', 'A9630_1', 'A5200'
);

-- 뇌/심혈관 계열 (CARDIO)
UPDATE coverage_standard SET semantic_scope = 'CARDIO' WHERE coverage_code IN (
    'A4103', 'A4102', 'A4101', 'A4104_1', 'A4105', 'A5104_1', 'A5107_1'
);

-- 상해 계열 (INJURY)
UPDATE coverage_standard SET semantic_scope = 'INJURY' WHERE coverage_code IN (
    'A3300_1', 'A3100', 'A3200'
);

-- 수술비 계열 (SURGERY)
UPDATE coverage_standard SET semantic_scope = 'SURGERY' WHERE coverage_code IN (
    'A5100', 'A5300'
);

-- 사망 계열 (DEATH)
UPDATE coverage_standard SET semantic_scope = 'DEATH' WHERE coverage_code IN (
    'A1100', 'A1300'
);

-- ============================================================================
-- 4. coverage_alias.confidence 기본값 설정
-- ============================================================================

-- 가입설계서 기반 alias: 높은 신뢰도
UPDATE coverage_alias SET confidence = 1.0 WHERE source_doc_type = '가입설계서';

-- 상품요약서 기반 alias: 높은 신뢰도
UPDATE coverage_alias SET confidence = 0.95 WHERE source_doc_type = '상품요약서';

-- 사업방법서 기반 alias: 중간 신뢰도
UPDATE coverage_alias SET confidence = 0.85 WHERE source_doc_type = '사업방법서';

-- 약관 기반 alias: 참조용
UPDATE coverage_alias SET confidence = 0.7 WHERE source_doc_type = '약관';

-- ============================================================================
-- 5. 대표 담보 is_primary 설정 (보험사별 가장 먼저 등록된 alias)
-- ============================================================================

WITH primary_aliases AS (
    SELECT DISTINCT ON (insurer_id, coverage_code)
        alias_id
    FROM coverage_alias
    ORDER BY insurer_id, coverage_code,
        CASE source_doc_type
            WHEN '가입설계서' THEN 1
            WHEN '상품요약서' THEN 2
            WHEN '사업방법서' THEN 3
            ELSE 4
        END,
        created_at
)
UPDATE coverage_alias
SET is_primary = true
WHERE alias_id IN (SELECT alias_id FROM primary_aliases);

-- ============================================================================
-- 6. 인덱스 추가
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_coverage_standard_semantic_scope
ON coverage_standard(semantic_scope);

CREATE INDEX IF NOT EXISTS idx_coverage_alias_confidence
ON coverage_alias(confidence);

CREATE INDEX IF NOT EXISTS idx_coverage_alias_is_primary
ON coverage_alias(is_primary) WHERE is_primary = true;

-- ============================================================================
-- 7. coverage_name_map 뷰 생성 (지시서 스키마 준수)
-- ============================================================================

CREATE OR REPLACE VIEW coverage_name_map AS
SELECT
    i.insurer_code,
    ca.raw_name AS insurer_coverage_name,
    cs.coverage_name AS standard_coverage_name,
    ca.coverage_code,
    cs.semantic_scope,
    ca.is_primary,
    ca.confidence,
    ca.source_doc_type AS source
FROM coverage_alias ca
JOIN insurer i ON ca.insurer_id = i.insurer_id
JOIN coverage_standard cs ON ca.coverage_code = cs.coverage_code;

COMMENT ON VIEW coverage_name_map IS
'U-5.0-A: Coverage Resolution의 Single Source of Truth 뷰. 보험사별 담보명 → 표준 담보명 매핑';

-- ============================================================================
-- 검증 쿼리
-- ============================================================================

-- 도메인별 담보 분포 확인
-- SELECT semantic_scope, COUNT(*) FROM coverage_standard GROUP BY semantic_scope;

-- 신뢰도별 alias 분포 확인
-- SELECT confidence, COUNT(*) FROM coverage_alias GROUP BY confidence ORDER BY confidence DESC;

-- 대표 담보 확인
-- SELECT insurer_code, coverage_code, raw_name FROM coverage_name_map WHERE is_primary = true LIMIT 10;
