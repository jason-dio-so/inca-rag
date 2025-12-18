#!/bin/bash
# ============================================================================
# U-4.7 Demo Patch: 삼성 유사암/경계성 청크 재태깅
# ============================================================================
#
# 목적:
#   삼성의 compare doc_type에서 "유사암 진단비" 또는 "경계성종양" 관련 청크가
#   잘못된 coverage_code로 태깅된 경우, A4210(유사암진단비)으로 재태깅
#
# 특징:
#   - idempotent: 여러 번 실행해도 결과 동일
#   - chunk_id 하드코딩 없음 (조건 기반)
#   - demo 환경 전용 패치
#
# 사용:
#   ./tools/demo_retag_u47.sh
#   또는 demo_up.sh/demo_seed.sh에서 자동 호출
# ============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DB_CONTAINER="${DB_CONTAINER:-inca_demo_db}"
DB_NAME="${DB_NAME:-inca_rag}"
DB_USER="${DB_USER:-postgres}"

echo -e "${BLUE}[U-4.7 Patch]${NC} 삼성 유사암/경계성 청크 재태깅 시작..."

# ============================================================================
# 패치 SQL (idempotent)
# ============================================================================
PATCH_SQL=$(cat <<'EOSQL'
-- U-4.7 Patch: 삼성 유사암/경계성 청크를 A4210으로 재태깅
-- 조건:
--   1. insurer_code = 'SAMSUNG'
--   2. doc_type IN ('가입설계서', '상품요약서', '사업방법서') - compare 대상만
--   3. content에 '유사암 진단비(경계성종양)' 등 패턴 포함
--   4. 현재 coverage_code가 A4210이 아님 (idempotent)

WITH target_chunks AS (
    SELECT c.chunk_id
    FROM chunk c
    JOIN document d ON c.document_id = d.document_id
    JOIN insurer i ON d.insurer_id = i.insurer_id
    WHERE i.insurer_code = 'SAMSUNG'
      AND d.doc_type IN ('가입설계서', '상품요약서', '사업방법서')
      AND (
          c.content ILIKE '%유사암 진단비(경계성종양%'
          OR c.content ILIKE '%유사암 진단비(제자리암%'
          OR c.content ILIKE '%유사암 진단비(갑상선암%'
          OR c.content ILIKE '%유사암 진단비(기타피부암%'
          OR c.content ILIKE '%유사암 진단비(대장점막내암%'
      )
      AND (
          c.meta->'entities'->>'coverage_code' IS NULL
          OR c.meta->'entities'->>'coverage_code' != 'A4210'
      )
)
UPDATE chunk
SET meta = jsonb_set(
    jsonb_set(
        meta,
        '{entities,coverage_code}',
        '"A4210"',
        true
    ),
    '{entities,u47_patched}',
    'true',
    true
)
WHERE chunk_id IN (SELECT chunk_id FROM target_chunks);
EOSQL
)

# ============================================================================
# 패치 실행
# ============================================================================
RESULT=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "$PATCH_SQL" 2>&1)
UPDATED_COUNT=$(echo "$RESULT" | grep -oE 'UPDATE [0-9]+' | grep -oE '[0-9]+' || echo "0")

if [ "$UPDATED_COUNT" = "" ]; then
    UPDATED_COUNT=0
fi

echo -e "${GREEN}[U-4.7 Patch]${NC} 적용 완료: ${YELLOW}$UPDATED_COUNT${NC}건 재태깅"

# ============================================================================
# 검증: 삼성 + A4210 + compare doc_type 청크 존재 확인
# ============================================================================
VERIFY_SQL=$(cat <<'EOSQL'
SELECT COUNT(*) as cnt
FROM chunk c
JOIN document d ON c.document_id = d.document_id
JOIN insurer i ON d.insurer_id = i.insurer_id
WHERE i.insurer_code = 'SAMSUNG'
  AND d.doc_type IN ('가입설계서', '상품요약서', '사업방법서')
  AND c.meta->'entities'->>'coverage_code' = 'A4210';
EOSQL
)

VERIFY_COUNT=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "$VERIFY_SQL" 2>&1 | tr -d ' ')

if [ "$VERIFY_COUNT" -gt 0 ] 2>/dev/null; then
    echo -e "${GREEN}[U-4.7 Patch]${NC} 검증 PASS: 삼성 A4210 compare 청크 ${GREEN}$VERIFY_COUNT${NC}건 존재"
else
    echo -e "${RED}[U-4.7 Patch]${NC} 검증 WARN: 삼성 A4210 compare 청크 0건"
fi

# ============================================================================
# 패치 요약 로그
# ============================================================================
echo -e "${BLUE}[U-4.7 Patch]${NC} 요약:"
echo "  - updated=$UPDATED_COUNT rows"
echo "  - matched_by=\"유사암 진단비(경계성종양|제자리암|갑상선암|기타피부암|대장점막내암)\""
echo "  - target_code=A4210"
echo "  - verify_count=$VERIFY_COUNT"
