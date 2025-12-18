#!/bin/bash
# =============================================================================
# 보험 약관 비교 RAG 시스템 - 데모 데이터 시딩 스크립트
#
# 사용법:
#   ./tools/demo_seed.sh           # DB가 localhost:5432에 있을 때
#   ./tools/demo_seed.sh --docker  # Docker 컨테이너 내부에서 실행
#
# 기능:
#   1. DB schema 적용 (필요시)
#   2. Coverage mapping 로드 (있으면)
#   3. SAMSUNG, MERITZ ingestion
#   4. 검증 SQL 실행
#   5. /compare 스모크 테스트
# =============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# 옵션 파싱
DOCKER_MODE=false
API_BASE="http://localhost:8000"

for arg in "$@"; do
  case $arg in
    --docker)
      DOCKER_MODE=true
      API_BASE="http://localhost/api"  # nginx 경유
      shift
      ;;
  esac
done

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  데모 데이터 시딩${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# DB 환경변수
if [ "$DOCKER_MODE" = true ]; then
  export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@db:5432/inca_rag}"
  export SOURCE_PATH_ROOT="/app/data"
  DATA_ROOT="/app/data"
else
  export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/inca_rag}"
  DATA_ROOT="$PROJECT_ROOT/data"
fi

echo -e "${YELLOW}[1/6] DB 연결 확인 중...${NC}"
# psql 또는 python으로 DB 연결 테스트
if command -v psql &> /dev/null; then
  if psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "  DB 연결: ${GREEN}OK${NC}"
  else
    echo -e "  DB 연결: ${RED}FAIL${NC}"
    echo "  DATABASE_URL: $DATABASE_URL"
    exit 1
  fi
else
  # psql이 없으면 python으로 테스트
  python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
conn.execute('SELECT 1')
conn.close()
print('  DB 연결: OK')
" 2>/dev/null || {
    echo -e "  DB 연결: ${RED}FAIL${NC}"
    exit 1
  }
fi

echo -e "${YELLOW}[2/6] DB 스키마 확인/적용 중...${NC}"
# chunk 테이블 존재 여부로 스키마 적용 필요성 판단
SCHEMA_EXISTS=$(python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.execute(\"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='chunk')\")
print(cur.fetchone()[0])
conn.close()
" 2>/dev/null || echo "False")

if [ "$SCHEMA_EXISTS" = "True" ]; then
  echo -e "  스키마: ${GREEN}이미 존재${NC}"
else
  echo -e "  스키마 적용 중..."
  if command -v psql &> /dev/null; then
    psql "$DATABASE_URL" -f db/schema.sql > /dev/null 2>&1
  else
    echo -e "  ${RED}psql이 없어 스키마 적용 불가${NC}"
    echo "  docker compose -f docker-compose.demo.yml exec db psql -U postgres -d inca_rag -f /docker-entrypoint-initdb.d/schema.sql"
    exit 1
  fi
  echo -e "  스키마: ${GREEN}적용 완료${NC}"
fi

echo -e "${YELLOW}[3/6] Coverage 매핑 로드 중...${NC}"
MAPPING_FILE="$DATA_ROOT/담보명mapping자료.xlsx"
if [ -f "$MAPPING_FILE" ]; then
  python3 tools/load_coverage_mapping.py --xlsx "$MAPPING_FILE" 2>/dev/null && \
    echo -e "  Coverage 매핑: ${GREEN}로드 완료${NC}" || \
    echo -e "  Coverage 매핑: ${YELLOW}SKIP (이미 존재 또는 오류)${NC}"
else
  echo -e "  Coverage 매핑: ${YELLOW}SKIP (파일 없음)${NC}"
fi

echo -e "${YELLOW}[4/6] 문서 Ingestion 중 (삼성/메리츠 전체 PDF)...${NC}"

# 이미 적재된 문서 수 확인 (보험사별)
EXISTING_STATS=$(python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.execute('''
    SELECT
      COALESCE(SUM(CASE WHEN i.insurer_code='SAMSUNG' THEN 1 ELSE 0 END), 0),
      COALESCE(SUM(CASE WHEN i.insurer_code='MERITZ' THEN 1 ELSE 0 END), 0)
    FROM document d
    JOIN insurer i ON d.insurer_id=i.insurer_id
''')
row = cur.fetchone()
print(f'{row[0]}|{row[1]}')
conn.close()
" 2>/dev/null || echo "0|0")
EXISTING_SAMSUNG=$(echo "$EXISTING_STATS" | cut -d'|' -f1)
EXISTING_MERITZ=$(echo "$EXISTING_STATS" | cut -d'|' -f2)

if [ "$EXISTING_SAMSUNG" != "0" ] || [ "$EXISTING_MERITZ" != "0" ]; then
  echo -e "  기존 문서: SAMSUNG=${EXISTING_SAMSUNG}개, MERITZ=${EXISTING_MERITZ}개 (증분 적재)"
fi

# PDF 파일 개수 확인 (전체 로딩 대상)
echo -e "  ${BLUE}[전체 로딩 대상 PDF 확인]${NC}"
SAMSUNG_PDF_COUNT=$(find "$DATA_ROOT/samsung" -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
MERITZ_PDF_COUNT=$(find "$DATA_ROOT/meritz" -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
echo -e "    SAMSUNG: ${GREEN}${SAMSUNG_PDF_COUNT}${NC}개 PDF"
echo -e "    MERITZ: ${GREEN}${MERITZ_PDF_COUNT}${NC}개 PDF"

# SAMSUNG 전체 ingestion
SAMSUNG_DIR="$DATA_ROOT/samsung"
if [ -d "$SAMSUNG_DIR" ]; then
  echo -e "  ${BLUE}SAMSUNG${NC} 전체 ingestion..."
  python3 services/ingestion/ingest.py --root "$DATA_ROOT" --insurer SAMSUNG 2>&1 | \
    grep -E "(Processing|SKIP|inserted|Chunks|summary)" | head -20
else
  echo -e "  SAMSUNG: ${YELLOW}SKIP (폴더 없음)${NC}"
fi

# MERITZ 전체 ingestion
MERITZ_DIR="$DATA_ROOT/meritz"
if [ -d "$MERITZ_DIR" ]; then
  echo -e "  ${BLUE}MERITZ${NC} 전체 ingestion..."
  python3 services/ingestion/ingest.py --root "$DATA_ROOT" --insurer MERITZ 2>&1 | \
    grep -E "(Processing|SKIP|inserted|Chunks|summary)" | head -20
else
  echo -e "  MERITZ: ${YELLOW}SKIP (폴더 없음)${NC}"
fi

# U-4.7 Patch: 삼성 유사암/경계성 청크 재태깅
echo -e "  ${BLUE}[U-4.7 Patch]${NC} 삼성 유사암/경계성 재태깅..."
U47_RESULT=$(python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.execute('''
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
        '\"A4210\"',
        true
    ),
    '{entities,u47_patched}',
    'true',
    true
)
WHERE chunk_id IN (SELECT chunk_id FROM target_chunks)
''')
updated = cur.rowcount
conn.commit()

# Verify
cur = conn.execute('''
SELECT COUNT(*) FROM chunk c
JOIN document d ON c.document_id = d.document_id
JOIN insurer i ON d.insurer_id = i.insurer_id
WHERE i.insurer_code = 'SAMSUNG'
  AND d.doc_type IN ('가입설계서', '상품요약서', '사업방법서')
  AND c.meta->'entities'->>'coverage_code' = 'A4210'
''')
verified = cur.fetchone()[0]
conn.close()
print(f'{updated}|{verified}')
" 2>/dev/null || echo "0|0")
U47_UPDATED=$(echo "$U47_RESULT" | cut -d'|' -f1)
U47_VERIFIED=$(echo "$U47_RESULT" | cut -d'|' -f2)
echo -e "    적용: ${GREEN}${U47_UPDATED}${NC}건, 검증: ${GREEN}${U47_VERIFIED}${NC}건 A4210 존재"

echo -e "${YELLOW}[5/6] 데이터 검증 중...${NC}"

# 문서/청크 카운트 (보험사별)
DOC_CHUNK_STATS=$(python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])

# 보험사별 문서/청크
cur = conn.execute('''
    SELECT i.insurer_code,
           COUNT(DISTINCT d.document_id) as docs,
           COUNT(c.chunk_id) as chunks
    FROM insurer i
    LEFT JOIN document d ON i.insurer_id = d.insurer_id
    LEFT JOIN chunk c ON c.document_id = d.document_id
    WHERE i.insurer_code IN ('SAMSUNG', 'MERITZ')
    GROUP BY i.insurer_code
    ORDER BY i.insurer_code
''')
results = cur.fetchall()
conn.close()

for row in results:
    print(f'{row[0]}|{row[1]}|{row[2]}')
" 2>/dev/null || echo "")

echo -e "  ${BLUE}[적재 결과 요약]${NC}"
SAMSUNG_LINE=$(echo "$DOC_CHUNK_STATS" | grep -i samsung || echo "SAMSUNG|0|0")
MERITZ_LINE=$(echo "$DOC_CHUNK_STATS" | grep -i meritz || echo "MERITZ|0|0")
SAMSUNG_DOCS=$(echo "$SAMSUNG_LINE" | cut -d'|' -f2)
SAMSUNG_CHUNKS=$(echo "$SAMSUNG_LINE" | cut -d'|' -f3)
MERITZ_DOCS=$(echo "$MERITZ_LINE" | cut -d'|' -f2)
MERITZ_CHUNKS=$(echo "$MERITZ_LINE" | cut -d'|' -f3)

echo -e "    SAMSUNG: 문서 ${GREEN}${SAMSUNG_DOCS}${NC}개, 청크 ${GREEN}${SAMSUNG_CHUNKS}${NC}개"
echo -e "    MERITZ:  문서 ${GREEN}${MERITZ_DOCS}${NC}개, 청크 ${GREEN}${MERITZ_CHUNKS}${NC}개"

# 증가량 표시
SAMSUNG_INC=$((SAMSUNG_DOCS - EXISTING_SAMSUNG))
MERITZ_INC=$((MERITZ_DOCS - EXISTING_MERITZ))
if [ "$SAMSUNG_INC" -gt 0 ] || [ "$MERITZ_INC" -gt 0 ]; then
  echo -e "    (증가: SAMSUNG +${SAMSUNG_INC}, MERITZ +${MERITZ_INC})"
fi

# 로딩 충분성 리포트
echo ""
echo -e "  ${BLUE}[로딩 충분성 리포트]${NC}"

# (A) 보험사 × doc_type 문서/청크 수
echo -e "  ${YELLOW}(A) 보험사 × doc_type 분포:${NC}"
python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.execute('''
    SELECT i.insurer_code, d.doc_type,
           COUNT(DISTINCT d.document_id) AS docs,
           COUNT(c.chunk_id) AS chunks
    FROM insurer i
    JOIN document d ON d.insurer_id=i.insurer_id
    LEFT JOIN chunk c ON c.document_id=d.document_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
    GROUP BY 1,2
    ORDER BY 1,2
''')
print('    insurer_code | doc_type | docs | chunks')
print('    -------------|----------|------|-------')
for row in cur.fetchall():
    print(f'    {row[0]:12} | {row[1]:8} | {row[2]:4} | {row[3]}')
conn.close()
" 2>/dev/null || echo "    (조회 실패)"

# (B) 보험사별 coverage_code 상위 (compare_axis 대상 doc_type만)
echo ""
echo -e "  ${YELLOW}(B) coverage_code 상위 20개 (compare_axis 대상):${NC}"
python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.execute('''
    SELECT i.insurer_code,
           c.meta->'\''entities'\''->>'coverage_code' AS coverage_code,
           COUNT(*) AS hits
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
      AND c.meta->'\''entities'\''->>'coverage_code' IS NOT NULL
    GROUP BY 1,2
    ORDER BY 1,3 DESC
    LIMIT 40
''')
print('    insurer_code | coverage_code | hits')
print('    -------------|---------------|-----')
for row in cur.fetchall():
    print(f'    {row[0]:12} | {row[1]:13} | {row[2]}')
conn.close()
" 2>/dev/null || echo "    (조회 실패)"

# (C) coverage_code 존재 비율
echo ""
echo -e "  ${YELLOW}(C) coverage_code 태깅률 (compare_axis 대상):${NC}"
python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.execute('''
    SELECT i.insurer_code, c.doc_type,
           COUNT(*) AS total,
           COUNT(c.meta->'\''entities'\''->>'coverage_code') AS with_code,
           ROUND(100.0 * COUNT(c.meta->'\''entities'\''->>'coverage_code') / NULLIF(COUNT(*),0), 2) AS pct
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
    GROUP BY 1,2
    ORDER BY 1,2
''')
print('    insurer_code | doc_type | total | with_code | pct')
print('    -------------|----------|-------|-----------|----')
for row in cur.fetchall():
    print(f'    {row[0]:12} | {row[1]:8} | {row[2]:5} | {row[3]:9} | {row[4]}%')
conn.close()
" 2>/dev/null || echo "    (조회 실패)"

echo ""
echo -e "${YELLOW}[6/6] /compare 스모크 테스트 (2단 구성)...${NC}"

# API 대기 (최대 30초)
echo -n "  API 대기 중"
for i in {1..30}; do
  if curl -sf "$API_BASE/health" > /dev/null 2>&1; then
    echo -e " ${GREEN}OK${NC}"
    break
  fi
  echo -n "."
  sleep 1
  if [ $i -eq 30 ]; then
    echo -e " ${RED}TIMEOUT${NC}"
    echo -e "  /compare 테스트: ${YELLOW}SKIP (API 미응답)${NC}"
    exit 0
  fi
done

# =============================================================================
# Smoke A: 안정성 테스트 (양쪽 근거 PASS 강제)
# A6200: 암직접치료입원일당 (양쪽 공통), A5100: 질병수술비 (양쪽 공통)
# =============================================================================
echo ""
echo -e "  ${BLUE}[Smoke A: 안정성]${NC} 암입원일당 + 질병수술비 (A6200/A5100)"
SMOKE_A_RESPONSE=$(curl -sf -X POST "$API_BASE/compare" \
  -H "Content-Type: application/json" \
  -d '{"query":"암입원일당 질병수술비","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A6200","A5100"],"top_k_per_insurer":10}' 2>/dev/null || echo '{"error": "failed"}')

SMOKE_A_RESULT=$(echo "$SMOKE_A_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    axis = data.get('compare_axis', [])
    counts = {}
    for item in axis:
        ic = item.get('insurer_code', '')
        counts[ic] = counts.get(ic, 0) + 1
    samsung = counts.get('SAMSUNG', 0)
    meritz = counts.get('MERITZ', 0)
    total = len(axis)
    if samsung >= 1 and meritz >= 1:
        print(f'PASS|{total}|{samsung}|{meritz}')
    elif total > 0:
        print(f'WARN|{total}|{samsung}|{meritz}')
    else:
        print(f'FAIL|0|0|0')
except Exception as e:
    print(f'ERROR|0|0|0|{e}')
" 2>/dev/null || echo "ERROR|0|0|0")

SMOKE_A_STATUS=$(echo "$SMOKE_A_RESULT" | cut -d'|' -f1)
SMOKE_A_TOTAL=$(echo "$SMOKE_A_RESULT" | cut -d'|' -f2)
SMOKE_A_SAMSUNG=$(echo "$SMOKE_A_RESULT" | cut -d'|' -f3)
SMOKE_A_MERITZ=$(echo "$SMOKE_A_RESULT" | cut -d'|' -f4)

if [ "$SMOKE_A_STATUS" = "PASS" ]; then
  echo -e "    ${GREEN}PASS${NC} (${SMOKE_A_TOTAL}개 근거) - SAMSUNG: ${SMOKE_A_SAMSUNG}, MERITZ: ${SMOKE_A_MERITZ}"
elif [ "$SMOKE_A_STATUS" = "WARN" ]; then
  echo -e "    ${YELLOW}WARN${NC} - SAMSUNG: ${SMOKE_A_SAMSUNG}, MERITZ: ${SMOKE_A_MERITZ}"
else
  echo -e "    ${RED}FAIL${NC}"
  echo "    응답: $(echo "$SMOKE_A_RESPONSE" | head -c 200)"
fi

# =============================================================================
# Smoke B: 고객 시나리오 테스트 (경계성종양/유사암/제자리암 + 암진단비)
# A4200_1: 암진단비, A4210: 유사암/제자리암 축
# WARN 허용 (데이터 부족 시), 단 진단 정보 출력 필수
# =============================================================================
echo ""
echo -e "  ${BLUE}[Smoke B: 고객 시나리오]${NC} 경계성종양 암진단비 (A4200_1/A4210)"
SMOKE_B_RESPONSE=$(curl -sf -X POST "$API_BASE/compare" \
  -H "Content-Type: application/json" \
  -d '{"query":"경계성종양 암진단비","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A4200_1","A4210"],"top_k_per_insurer":10}' 2>/dev/null || echo '{"error": "failed"}')

SMOKE_B_RESULT=$(echo "$SMOKE_B_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    axis = data.get('compare_axis', [])
    debug = data.get('debug', {})
    counts = {}
    doc_type_counts = {}
    for item in axis:
        ic = item.get('insurer_code', '')
        dt = item.get('doc_type', '')
        counts[ic] = counts.get(ic, 0) + 1
        key = f'{ic}:{dt}'
        doc_type_counts[key] = doc_type_counts.get(key, 0) + 1
    samsung = counts.get('SAMSUNG', 0)
    meritz = counts.get('MERITZ', 0)
    total = len(axis)

    resolved_codes = debug.get('resolved_coverage_codes', [])
    recommended_codes = debug.get('recommended_coverage_codes', [])
    policy_keywords = debug.get('resolved_policy_keywords', [])

    if samsung >= 1 and meritz >= 1:
        status = 'PASS'
    elif total > 0:
        status = 'WARN'
    else:
        status = 'FAIL'

    dt_str = ','.join([f'{k}={v}' for k,v in sorted(doc_type_counts.items())])
    debug_str = f'codes={resolved_codes};recommended={recommended_codes};keywords={policy_keywords}'
    print(f'{status}|{total}|{samsung}|{meritz}|{dt_str}|{debug_str}')
except Exception as e:
    print(f'ERROR|0|0|0||{e}')
" 2>/dev/null || echo "ERROR|0|0|0||")

SMOKE_B_STATUS=$(echo "$SMOKE_B_RESULT" | cut -d'|' -f1)
SMOKE_B_TOTAL=$(echo "$SMOKE_B_RESULT" | cut -d'|' -f2)
SMOKE_B_SAMSUNG=$(echo "$SMOKE_B_RESULT" | cut -d'|' -f3)
SMOKE_B_MERITZ=$(echo "$SMOKE_B_RESULT" | cut -d'|' -f4)
SMOKE_B_DOCTYPES=$(echo "$SMOKE_B_RESULT" | cut -d'|' -f5)
SMOKE_B_DEBUG=$(echo "$SMOKE_B_RESULT" | cut -d'|' -f6)

if [ "$SMOKE_B_STATUS" = "PASS" ]; then
  echo -e "    ${GREEN}PASS${NC} (${SMOKE_B_TOTAL}개 근거) - SAMSUNG: ${SMOKE_B_SAMSUNG}, MERITZ: ${SMOKE_B_MERITZ}"
  if [ -n "$SMOKE_B_DOCTYPES" ]; then
    echo -e "    doc_type 분포: ${SMOKE_B_DOCTYPES}"
  fi
elif [ "$SMOKE_B_STATUS" = "WARN" ]; then
  echo -e "    ${YELLOW}WARN${NC} - 한쪽 근거 부족 (데모 진행 가능)"
  echo -e "    SAMSUNG: ${SMOKE_B_SAMSUNG}개, MERITZ: ${SMOKE_B_MERITZ}개"
  if [ -n "$SMOKE_B_DOCTYPES" ]; then
    echo -e "    doc_type 분포: ${SMOKE_B_DOCTYPES}"
  fi
  echo ""
  echo -e "    ${YELLOW}[Debug 정보]${NC}"
  echo -e "    ${SMOKE_B_DEBUG}"
  echo ""
  echo -e "    ${YELLOW}[진단 SQL 1] A4200_1/A4210 coverage_code별 chunk 분포:${NC}"
  # demo_seed.sh는 로컬 python으로 실행하므로 직접 psql 또는 python 사용
  python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.execute('''
    SELECT i.insurer_code,
           c.meta->'\''entities'\''->>'coverage_code' AS coverage_code,
           c.doc_type,
           COUNT(*) AS chunks
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
      AND c.meta->'\''entities'\''->>'coverage_code' IN ('A4200_1','A4210')
    GROUP BY 1,2,3
    ORDER BY 1,2,4 DESC
''')
print('    insurer | coverage_code | doc_type | chunks')
print('    --------|---------------|----------|-------')
for row in cur.fetchall():
    print(f'    {row[0]:7} | {row[1]:13} | {row[2]:8} | {row[3]}')
conn.close()
" 2>/dev/null || echo "    (조회 실패)"
  echo ""
  echo -e "    ${YELLOW}[진단 SQL 2] coverage_code 태깅률:${NC}"
  python3 -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.execute('''
    SELECT i.insurer_code, c.doc_type,
           COUNT(*) AS total,
           COUNT(c.meta->'\''entities'\''->>'coverage_code') AS with_code,
           ROUND(100.0 * COUNT(c.meta->'\''entities'\''->>'coverage_code') / NULLIF(COUNT(*),0), 2) AS pct
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
    GROUP BY 1,2
    ORDER BY 1,2
''')
print('    insurer | doc_type | total | with_code | pct')
print('    --------|----------|-------|-----------|----')
for row in cur.fetchall():
    print(f'    {row[0]:7} | {row[1]:8} | {row[2]:5} | {row[3]:9} | {row[4]}%')
conn.close()
" 2>/dev/null || echo "    (조회 실패)"
else
  echo -e "    ${RED}FAIL${NC} - 근거 없음"
  echo "    응답: $(echo "$SMOKE_B_RESPONSE" | head -c 300)"
fi

# 최종 스모크 결과 요약
echo ""
echo -e "  ${BLUE}[스모크 결과 요약]${NC}"
echo -e "    Smoke A (안정성):     ${SMOKE_A_STATUS}"
echo -e "    Smoke B (고객 시나리오): ${SMOKE_B_STATUS}"

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  데모 데이터 시딩 완료!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""
echo -e "  ${BLUE}추천 질의 (curl):${NC}"
echo ""
echo -e "  ${YELLOW}# Smoke A: 안정성 (양쪽 근거 보장)${NC}"
echo '  curl -X POST http://localhost:8000/compare -H "Content-Type: application/json" -d '\''{"query":"암입원일당 질병수술비","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A6200","A5100"]}'\'''
echo ""
echo -e "  ${YELLOW}# Smoke B: 고객 시나리오 (경계성종양 암진단비)${NC}"
echo '  curl -X POST http://localhost:8000/compare -H "Content-Type: application/json" -d '\''{"query":"경계성종양 암진단비","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A4200_1","A4210"]}'\'''
echo ""
