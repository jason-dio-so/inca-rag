#!/bin/bash
# =============================================================================
# STEP 4.2 — Option A+ DB Reset Script
# =============================================================================
#
# 목적: coverage 테이블 초기화 + 엑셀 기반 재적재 + 검증
#
# 사용법:
#   ./tools/reset_db_option_a_plus.sh
#   ./tools/reset_db_option_a_plus.sh --skip-backfill  # chunk 재태깅 생략
#
# 전제조건:
#   - Docker 컨테이너 (inca_demo_db) 실행 중
#   - data/담보명mapping자료.xlsx 존재
#   - Python 환경 + 필수 패키지 설치됨
#
# =============================================================================

set -e  # 에러 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 옵션 파싱
SKIP_BACKFILL=false
for arg in "$@"; do
    case $arg in
        --skip-backfill)
            SKIP_BACKFILL=true
            shift
            ;;
    esac
done

echo "=============================================="
echo "Option A+ DB Reset Script"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# 1. Docker 컨테이너 확인
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/6] Docker 컨테이너 확인...${NC}"

if ! docker ps --format '{{.Names}}' | grep -q 'inca_demo_db'; then
    echo -e "${RED}ERROR: inca_demo_db 컨테이너가 실행 중이 아닙니다.${NC}"
    echo "docker compose -f docker-compose.demo.yml up -d 로 먼저 시작하세요."
    exit 1
fi
echo -e "${GREEN}✓ inca_demo_db 컨테이너 확인됨${NC}"

# -----------------------------------------------------------------------------
# 2. Coverage 테이블 초기화 (TRUNCATE + CASCADE)
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[2/6] Coverage 테이블 초기화...${NC}"

docker exec -i inca_demo_db psql -U postgres -d inca_rag -c "
TRUNCATE coverage_alias CASCADE;
DELETE FROM coverage_standard;
"

echo -e "${GREEN}✓ coverage_alias, coverage_standard 초기화 완료${NC}"

# -----------------------------------------------------------------------------
# 3. 엑셀 기반 표준코드/alias 적재
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[3/6] 엑셀 기반 coverage 적재...${NC}"

XLSX_PATH="$PROJECT_ROOT/data/담보명mapping자료.xlsx"

if [ ! -f "$XLSX_PATH" ]; then
    echo -e "${RED}ERROR: 엑셀 파일이 없습니다: $XLSX_PATH${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"
python tools/load_coverage_mapping.py --xlsx "$XLSX_PATH"

echo -e "${GREEN}✓ coverage 적재 완료${NC}"

# -----------------------------------------------------------------------------
# 4. (선택) Chunk coverage_code 재태깅
# -----------------------------------------------------------------------------
echo ""
if [ "$SKIP_BACKFILL" = true ]; then
    echo -e "${YELLOW}[4/6] Chunk 재태깅 생략 (--skip-backfill)${NC}"
else
    echo -e "${YELLOW}[4/6] Chunk coverage_code 재태깅...${NC}"

    if [ -f "$PROJECT_ROOT/tools/backfill_chunk_coverage_code.py" ]; then
        python tools/backfill_chunk_coverage_code.py || {
            echo -e "${YELLOW}⚠ backfill 스크립트 실행 실패 (무시하고 계속)${NC}"
        }
        echo -e "${GREEN}✓ Chunk 재태깅 완료${NC}"
    else
        echo -e "${YELLOW}⚠ backfill 스크립트가 없습니다. 생략합니다.${NC}"
    fi
fi

# -----------------------------------------------------------------------------
# 5. 누락된 인덱스/테이블 생성 (현재 DB에 적용)
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[5/6] 누락된 인덱스/테이블 적용...${NC}"

docker exec -i inca_demo_db psql -U postgres -d inca_rag <<'EOSQL'
-- trgm 인덱스 (20251217 migration)
CREATE INDEX IF NOT EXISTS idx_chunk_content_trgm
    ON chunk USING gin (content gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_chunk_content_trgm_policy
    ON chunk USING gin (content gin_trgm_ops)
    WHERE doc_type = '약관';

CREATE INDEX IF NOT EXISTS idx_chunk_insurer_doctype
    ON chunk (insurer_id, doc_type);

-- comparison_slot_cache 테이블 (20251218 migration)
CREATE TABLE IF NOT EXISTS comparison_slot_cache (
    cache_id        BIGSERIAL PRIMARY KEY,
    insurer_id      BIGINT NOT NULL REFERENCES insurer(insurer_id) ON DELETE CASCADE,
    product_id      BIGINT REFERENCES product(product_id) ON DELETE SET NULL,
    plan_id         BIGINT REFERENCES product_plan(plan_id) ON DELETE SET NULL,
    coverage_code   TEXT NOT NULL,
    slot_key        TEXT NOT NULL,
    slot_value      TEXT,
    slot_unit       TEXT,
    normalized_value NUMERIC,
    confidence      TEXT DEFAULT 'medium',
    evidence_refs   JSONB DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_slot_cache UNIQUE (insurer_id, product_id, plan_id, coverage_code, slot_key)
);

CREATE INDEX IF NOT EXISTS idx_slot_cache_insurer_coverage
    ON comparison_slot_cache(insurer_id, coverage_code);

CREATE INDEX IF NOT EXISTS idx_slot_cache_slot_key
    ON comparison_slot_cache(slot_key);

ANALYZE chunk;
EOSQL

echo -e "${GREEN}✓ 인덱스/테이블 적용 완료${NC}"

# -----------------------------------------------------------------------------
# 6. 검증
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[6/6] 검증 수행...${NC}"

# 검증 결과 수집
VERIFICATION_FAILED=false

# 6.1 coverage_standard 개수
STANDARD_COUNT=$(docker exec -i inca_demo_db psql -U postgres -d inca_rag -t -c "SELECT count(*) FROM coverage_standard;" | tr -d ' ')
if [ "$STANDARD_COUNT" -eq 28 ]; then
    echo -e "${GREEN}✓ coverage_standard: $STANDARD_COUNT (expected: 28)${NC}"
else
    echo -e "${RED}✗ coverage_standard: $STANDARD_COUNT (expected: 28)${NC}"
    VERIFICATION_FAILED=true
fi

# 6.2 coverage_alias 개수
ALIAS_COUNT=$(docker exec -i inca_demo_db psql -U postgres -d inca_rag -t -c "SELECT count(*) FROM coverage_alias;" | tr -d ' ')
if [ "$ALIAS_COUNT" -ge 260 ]; then
    echo -e "${GREEN}✓ coverage_alias: $ALIAS_COUNT (expected: ~264)${NC}"
else
    echo -e "${RED}✗ coverage_alias: $ALIAS_COUNT (expected: ~264)${NC}"
    VERIFICATION_FAILED=true
fi

# 6.3 pg_trgm extension
TRGM_EXISTS=$(docker exec -i inca_demo_db psql -U postgres -d inca_rag -t -c "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='pg_trgm');" | tr -d ' ')
if [ "$TRGM_EXISTS" = "t" ]; then
    echo -e "${GREEN}✓ pg_trgm extension: 존재${NC}"
else
    echo -e "${RED}✗ pg_trgm extension: 없음${NC}"
    VERIFICATION_FAILED=true
fi

# 6.4 trgm 인덱스
TRGM_IDX_COUNT=$(docker exec -i inca_demo_db psql -U postgres -d inca_rag -t -c "SELECT count(*) FROM pg_indexes WHERE tablename='chunk' AND indexname LIKE '%trgm%';" | tr -d ' ')
if [ "$TRGM_IDX_COUNT" -ge 2 ]; then
    echo -e "${GREEN}✓ chunk trgm 인덱스: $TRGM_IDX_COUNT개${NC}"
else
    echo -e "${RED}✗ chunk trgm 인덱스: $TRGM_IDX_COUNT개 (expected: 2+)${NC}"
    VERIFICATION_FAILED=true
fi

# 6.5 comparison_slot_cache 테이블
SLOT_TABLE_EXISTS=$(docker exec -i inca_demo_db psql -U postgres -d inca_rag -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='comparison_slot_cache');" | tr -d ' ')
if [ "$SLOT_TABLE_EXISTS" = "t" ]; then
    echo -e "${GREEN}✓ comparison_slot_cache 테이블: 존재${NC}"
else
    echo -e "${RED}✗ comparison_slot_cache 테이블: 없음${NC}"
    VERIFICATION_FAILED=true
fi

# 최종 결과
echo ""
echo "=============================================="
if [ "$VERIFICATION_FAILED" = true ]; then
    echo -e "${RED}검증 실패 - 일부 항목이 기대값과 다릅니다${NC}"
    exit 1
else
    echo -e "${GREEN}모든 검증 통과!${NC}"
    echo ""
    echo "Summary:"
    echo "  - coverage_standard: $STANDARD_COUNT"
    echo "  - coverage_alias: $ALIAS_COUNT"
    echo "  - pg_trgm: enabled"
    echo "  - trgm indexes: $TRGM_IDX_COUNT"
    echo "  - comparison_slot_cache: created"
fi
echo "=============================================="
