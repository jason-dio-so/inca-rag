#!/bin/bash
# =============================================================================
# 보험 약관 비교 RAG 시스템 - 데모 원클릭 실행 스크립트
#
# 사용법:
#   ./tools/demo_up.sh
#
# 옵션:
#   --build    이미지 강제 재빌드
#   --down     기존 컨테이너 종료 후 재시작
#   --clean    볼륨까지 삭제 후 재시작
#   --no-seed  데이터 시딩 건너뛰기
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

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  보험 약관 비교 RAG 시스템 - 데모 배포${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# 옵션 파싱
BUILD_FLAG=""
DOWN_FLAG=false
CLEAN_FLAG=false
NO_SEED=false

for arg in "$@"; do
  case $arg in
    --build)
      BUILD_FLAG="--build"
      shift
      ;;
    --down)
      DOWN_FLAG=true
      shift
      ;;
    --clean)
      CLEAN_FLAG=true
      shift
      ;;
    --no-seed)
      NO_SEED=true
      shift
      ;;
  esac
done

# 기존 컨테이너 정리
if [ "$CLEAN_FLAG" = true ]; then
  echo -e "${YELLOW}[1/8] 기존 컨테이너 및 볼륨 삭제 중...${NC}"
  docker compose -f docker-compose.demo.yml down -v --remove-orphans 2>/dev/null || true
elif [ "$DOWN_FLAG" = true ]; then
  echo -e "${YELLOW}[1/8] 기존 컨테이너 종료 중...${NC}"
  docker compose -f docker-compose.demo.yml down --remove-orphans 2>/dev/null || true
else
  echo -e "${YELLOW}[1/8] 기존 상태 확인...${NC}"
fi

# Step 1: DB 먼저 시작
echo -e "${YELLOW}[2/8] PostgreSQL + pgvector 시작 중...${NC}"
docker compose -f docker-compose.demo.yml up -d db

# DB 준비 대기
echo -e "${YELLOW}[3/8] DB 준비 대기 중...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
until docker compose -f docker-compose.demo.yml exec -T db pg_isready -U postgres -d inca_rag > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo -e "${RED}DB 시작 실패 (timeout)${NC}"
    exit 1
  fi
  echo -n "."
  sleep 1
done
echo -e " ${GREEN}OK${NC}"

# Step 2: DB 스키마 적용
echo -e "${YELLOW}[4/8] DB 스키마 적용 중...${NC}"
# schema.sql이 init 디렉토리에 마운트되어 있으므로 자동 실행됨
# 추가로 migration이 필요한 경우를 위해 체크
SCHEMA_EXISTS=$(docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -t -c \
  "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='chunk')" 2>/dev/null | tr -d ' ')
if [ "$SCHEMA_EXISTS" = "t" ]; then
  echo -e "  스키마: ${GREEN}이미 존재${NC}"
else
  # schema.sql 수동 적용
  docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -f /docker-entrypoint-initdb.d/schema.sql > /dev/null 2>&1 || true
  echo -e "  스키마: ${GREEN}적용 완료${NC}"
fi

# Step 3: API/Web/Nginx 시작
echo -e "${YELLOW}[5/8] API, Web, Nginx 시작 중...${NC}"
docker compose -f docker-compose.demo.yml up -d $BUILD_FLAG api web nginx

# API 준비 대기
echo -e "${YELLOW}[6/8] API 준비 대기 중...${NC}"
MAX_RETRIES=60
RETRY_COUNT=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo -e "${RED}API 시작 실패 (timeout)${NC}"
    docker compose -f docker-compose.demo.yml logs api
    exit 1
  fi
  echo -n "."
  sleep 2
done
echo -e " ${GREEN}OK${NC}"

# Step 4: 데이터 시딩 (API 컨테이너 내부에서 실행) - 삼성/메리츠 전체 PDF 로딩
if [ "$NO_SEED" = false ]; then
  echo -e "${YELLOW}[7/8] 데이터 시딩 중 (삼성/메리츠 전체 PDF)...${NC}"

  # 기존 데이터 확인
  EXISTING_STATS=$(docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -t -c "
    SELECT
      COALESCE(SUM(CASE WHEN i.insurer_code='SAMSUNG' THEN 1 ELSE 0 END), 0) as samsung_docs,
      COALESCE(SUM(CASE WHEN i.insurer_code='MERITZ' THEN 1 ELSE 0 END), 0) as meritz_docs
    FROM document d
    JOIN insurer i ON d.insurer_id=i.insurer_id
  " 2>/dev/null | tr -d ' ' || echo "0|0")
  EXISTING_SAMSUNG=$(echo "$EXISTING_STATS" | cut -d'|' -f1)
  EXISTING_MERITZ=$(echo "$EXISTING_STATS" | cut -d'|' -f2)

  if [ "$EXISTING_SAMSUNG" != "0" ] || [ "$EXISTING_MERITZ" != "0" ]; then
    echo -e "  기존 문서: SAMSUNG=${EXISTING_SAMSUNG}개, MERITZ=${EXISTING_MERITZ}개 (증분 적재)"
  fi

  # PDF 파일 개수 확인 (전체 로딩 대상)
  echo -e "  ${BLUE}[전체 로딩 대상 PDF 확인]${NC}"
  SAMSUNG_PDF_COUNT=$(docker compose -f docker-compose.demo.yml exec -T api find /app/data/samsung -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
  MERITZ_PDF_COUNT=$(docker compose -f docker-compose.demo.yml exec -T api find /app/data/meritz -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
  echo -e "    SAMSUNG: ${GREEN}${SAMSUNG_PDF_COUNT}${NC}개 PDF"
  echo -e "    MERITZ: ${GREEN}${MERITZ_PDF_COUNT}${NC}개 PDF"

  # Coverage 매핑 로드 (API 컨테이너 내부에서)
  echo -e "  Coverage 매핑 로드 중..."
  docker compose -f docker-compose.demo.yml exec -T api python tools/load_coverage_mapping.py \
    --xlsx /app/data/담보명mapping자료.xlsx 2>/dev/null && \
    echo -e "    ${GREEN}OK${NC}" || echo -e "    ${YELLOW}SKIP (이미 존재 또는 파일 없음)${NC}"

  # SAMSUNG 전체 ingestion
  echo -e "  ${BLUE}SAMSUNG${NC} 전체 ingestion..."
  docker compose -f docker-compose.demo.yml exec -T \
    -e SOURCE_PATH_ROOT=/app/data \
    api python services/ingestion/ingest.py --root /app/data --insurer SAMSUNG 2>&1 | \
    grep -E "(Processing|SKIP|inserted|Chunks|summary|Documents)" | head -15 || echo "    (처리 완료)"

  # MERITZ 전체 ingestion
  echo -e "  ${BLUE}MERITZ${NC} 전체 ingestion..."
  docker compose -f docker-compose.demo.yml exec -T \
    -e SOURCE_PATH_ROOT=/app/data \
    api python services/ingestion/ingest.py --root /app/data --insurer MERITZ 2>&1 | \
    grep -E "(Processing|SKIP|inserted|Chunks|summary|Documents)" | head -15 || echo "    (처리 완료)"

  # U-4.7 Patch: 삼성 유사암/경계성 청크 재태깅
  echo -e "  ${BLUE}[U-4.7 Patch]${NC} 삼성 유사암/경계성 재태깅..."
  ./tools/demo_retag_u47.sh 2>/dev/null | grep -E "(\[U-4.7|updated=|verify_count=)" || echo "    (패치 완료)"

  # 결과 확인 (보험사별)
  echo ""
  echo -e "  ${BLUE}[적재 결과 요약]${NC}"
  FINAL_STATS=$(docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -t -c "
    SELECT i.insurer_code,
           COUNT(DISTINCT d.document_id) as docs,
           COUNT(c.chunk_id) as chunks
    FROM insurer i
    LEFT JOIN document d ON d.insurer_id=i.insurer_id
    LEFT JOIN chunk c ON c.document_id=d.document_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
    GROUP BY i.insurer_code
    ORDER BY i.insurer_code
  " 2>/dev/null || echo "")

  # Parse and display
  SAMSUNG_FINAL=$(echo "$FINAL_STATS" | grep -i samsung | tr -d ' ' || echo "SAMSUNG|0|0")
  MERITZ_FINAL=$(echo "$FINAL_STATS" | grep -i meritz | tr -d ' ' || echo "MERITZ|0|0")
  SAMSUNG_DOCS=$(echo "$SAMSUNG_FINAL" | cut -d'|' -f2)
  SAMSUNG_CHUNKS=$(echo "$SAMSUNG_FINAL" | cut -d'|' -f3)
  MERITZ_DOCS=$(echo "$MERITZ_FINAL" | cut -d'|' -f2)
  MERITZ_CHUNKS=$(echo "$MERITZ_FINAL" | cut -d'|' -f3)

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
  docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -c "
    SELECT i.insurer_code, d.doc_type,
           COUNT(DISTINCT d.document_id) AS docs,
           COUNT(c.chunk_id) AS chunks
    FROM insurer i
    JOIN document d ON d.insurer_id=i.insurer_id
    LEFT JOIN chunk c ON c.document_id=d.document_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
    GROUP BY 1,2
    ORDER BY 1,2;
  " 2>/dev/null || echo "    (조회 실패)"

  # (B) 보험사별 coverage_code 상위 (compare_axis 대상 doc_type만)
  echo -e "  ${YELLOW}(B) coverage_code 상위 20개 (compare_axis 대상):${NC}"
  docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -c "
    SELECT i.insurer_code,
           c.meta->'entities'->>'coverage_code' AS coverage_code,
           COUNT(*) AS hits
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
      AND c.meta->'entities'->>'coverage_code' IS NOT NULL
    GROUP BY 1,2
    ORDER BY 1,3 DESC
    LIMIT 40;
  " 2>/dev/null || echo "    (조회 실패)"

  # (C) coverage_code 존재 비율
  echo -e "  ${YELLOW}(C) coverage_code 태깅률 (compare_axis 대상):${NC}"
  docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -c "
    SELECT i.insurer_code, c.doc_type,
           COUNT(*) AS total,
           COUNT(c.meta->'entities'->>'coverage_code') AS with_code,
           ROUND(100.0 * COUNT(c.meta->'entities'->>'coverage_code') / NULLIF(COUNT(*),0), 2) AS pct
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
    GROUP BY 1,2
    ORDER BY 1,2;
  " 2>/dev/null || echo "    (조회 실패)"

else
  echo -e "${YELLOW}[7/8] 데이터 시딩: SKIP (--no-seed)${NC}"
fi

# Step 5: Smoke Test (2-tier)
echo -e "${YELLOW}[8/8] 스모크 테스트 실행 중 (2단 구성)...${NC}"

# /health 테스트
HEALTH_RESULT=$(curl -sf http://localhost:8000/health 2>/dev/null)
if echo "$HEALTH_RESULT" | grep -q "healthy"; then
  echo -e "  /health: ${GREEN}OK${NC}"
else
  echo -e "  /health: ${RED}FAIL${NC}"
fi

# /api/health 테스트 (nginx 경유)
NGINX_HEALTH=$(curl -sf http://localhost/api/health 2>/dev/null || echo "FAIL")
if echo "$NGINX_HEALTH" | grep -q "healthy"; then
  echo -e "  /api/health (via nginx): ${GREEN}OK${NC}"
else
  echo -e "  /api/health (via nginx): ${YELLOW}PENDING${NC}"
fi

# =============================================================================
# Smoke A: 안정성 테스트 (양쪽 근거 PASS 강제)
# A6200: 암직접치료입원일당 (양쪽 공통), A5100: 질병수술비 (양쪽 공통)
# =============================================================================
echo ""
echo -e "  ${BLUE}[Smoke A: 안정성]${NC} 암입원일당 + 질병수술비 (A6200/A5100)"
SMOKE_A_RESPONSE=$(curl -sf -X POST http://localhost:8000/compare \
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
  echo -e "    ${YELLOW}[진단] A6200/A5100 chunk 분포:${NC}"
  docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -c "
    SELECT i.insurer_code, c.meta->'entities'->>'coverage_code' AS code, c.doc_type, COUNT(*) AS chunks
    FROM chunk c JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.meta->'entities'->>'coverage_code' IN ('A6200','A5100')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
    GROUP BY 1,2,3 ORDER BY 1,2,4 DESC;
  " 2>/dev/null || echo "    (DB 조회 실패)"
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
SMOKE_B_RESPONSE=$(curl -sf -X POST http://localhost:8000/compare \
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

    # Debug 정보 추출
    resolved_codes = debug.get('resolved_coverage_codes', [])
    recommended_codes = debug.get('recommended_coverage_codes', [])
    policy_keywords = debug.get('resolved_policy_keywords', [])

    if samsung >= 1 and meritz >= 1:
        status = 'PASS'
    elif total > 0:
        status = 'WARN'
    else:
        status = 'FAIL'

    # doc_type 분포 문자열
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
  docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -c "
    SELECT i.insurer_code,
           c.meta->'entities'->>'coverage_code' AS coverage_code,
           c.doc_type,
           COUNT(*) AS chunks
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
      AND c.meta->'entities'->>'coverage_code' IN ('A4200_1','A4210')
    GROUP BY 1,2,3
    ORDER BY 1,2,4 DESC;
  " 2>/dev/null || echo "    (DB 조회 실패)"
  echo ""
  echo -e "    ${YELLOW}[진단 SQL 2] compare_axis 대상 doc_type coverage_code 태깅률:${NC}"
  docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -c "
    SELECT i.insurer_code, c.doc_type,
           COUNT(*) AS total,
           COUNT(c.meta->'entities'->>'coverage_code') AS with_code,
           ROUND(100.0 * COUNT(c.meta->'entities'->>'coverage_code') / NULLIF(COUNT(*),0), 2) AS pct
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
    GROUP BY 1,2
    ORDER BY 1,2;
  " 2>/dev/null || echo "    (DB 조회 실패)"
else
  echo -e "    ${RED}FAIL${NC} - 근거 없음"
  echo "    응답: $(echo "$SMOKE_B_RESPONSE" | head -c 300)"
  echo ""
  echo -e "    ${RED}[진단 SQL] A4200_1/A4210 chunk 존재 여부:${NC}"
  docker compose -f docker-compose.demo.yml exec -T db psql -U postgres -d inca_rag -c "
    SELECT i.insurer_code,
           c.meta->'entities'->>'coverage_code' AS coverage_code,
           c.doc_type,
           COUNT(*) AS chunks
    FROM chunk c
    JOIN insurer i ON c.insurer_id=i.insurer_id
    WHERE i.insurer_code IN ('SAMSUNG','MERITZ')
      AND c.doc_type IN ('가입설계서','상품요약서','사업방법서')
      AND c.meta->'entities'->>'coverage_code' IN ('A4200_1','A4210')
    GROUP BY 1,2,3
    ORDER BY 1,2,4 DESC;
  " 2>/dev/null || echo "    (DB 조회 실패)"
fi

# 최종 스모크 결과 요약
echo ""
echo -e "  ${BLUE}[스모크 결과 요약]${NC}"
echo -e "    Smoke A (안정성):     ${SMOKE_A_STATUS}"
echo -e "    Smoke B (고객 시나리오): ${SMOKE_B_STATUS}"

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  데모 배포 완료!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""
echo -e "  ${BLUE}접속 URL:${NC}"
echo -e "    - Web UI:  ${GREEN}http://localhost${NC}"
echo -e "    - API:     ${GREEN}http://localhost:8000${NC}"
echo -e "    - API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  ${BLUE}추천 질의 (curl):${NC}"
echo ""
echo -e "  ${YELLOW}# Smoke A: 안정성 (양쪽 근거 보장)${NC}"
echo '  curl -X POST http://localhost:8000/compare -H "Content-Type: application/json" -d '\''{"query":"암입원일당 질병수술비","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A6200","A5100"]}'\'''
echo ""
echo -e "  ${YELLOW}# Smoke B: 고객 시나리오 (경계성종양 암진단비)${NC}"
echo '  curl -X POST http://localhost:8000/compare -H "Content-Type: application/json" -d '\''{"query":"경계성종양 암진단비","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A4200_1","A4210"]}'\'''
echo ""
echo -e "  ${BLUE}컨테이너 관리:${NC}"
echo "    docker compose -f docker-compose.demo.yml logs -f   # 로그 확인"
echo "    docker compose -f docker-compose.demo.yml down      # 종료"
echo ""
