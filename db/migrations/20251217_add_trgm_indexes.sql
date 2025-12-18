-- Step E-3: policy_axis 성능 개선을 위한 pg_trgm 인덱스 추가
--
-- 목적: ILIKE 키워드 검색 성능 개선
-- 적용 대상: chunk.content 컬럼
--
-- 실행 방법:
--   psql -h localhost -U postgres -d inca_rag -f db/migrations/20251217_add_trgm_indexes.sql

-- pg_trgm 확장 활성화 (이미 있으면 무시)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. 전체 chunk.content에 대한 trigram 인덱스
-- ILIKE 검색 시 sequential scan 대신 index scan 사용
CREATE INDEX IF NOT EXISTS idx_chunk_content_trgm
  ON chunk USING gin (content gin_trgm_ops);

-- 2. 약관(doc_type='약관')에 대한 부분 인덱스
-- policy_axis는 약관만 검색하므로, 부분 인덱스가 더 효율적
CREATE INDEX IF NOT EXISTS idx_chunk_content_trgm_policy
  ON chunk USING gin (content gin_trgm_ops)
  WHERE doc_type = '약관';

-- 3. 복합 조건 검색을 위한 btree 인덱스 (insurer_id + doc_type)
-- policy_axis 쿼리: WHERE insurer_id = ? AND doc_type = ANY(?)
CREATE INDEX IF NOT EXISTS idx_chunk_insurer_doctype
  ON chunk (insurer_id, doc_type);

-- 인덱스 통계 갱신
ANALYZE chunk;

-- 확인용 쿼리
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'chunk'
  AND indexname LIKE '%trgm%'
ORDER BY indexname;
