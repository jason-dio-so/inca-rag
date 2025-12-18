#!/bin/bash
# =============================================================================
# 사용자 테스트 스크립트
#
# 사용법:
#   ./tools/user_test.sh              # 기본 테스트
#   ./tools/user_test.sh "암진단비"    # 커스텀 질의
# =============================================================================

set -e

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

API_BASE="${API_BASE:-http://localhost:8000}"

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  보험 담보 비교 - 사용자 테스트${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# API 상태 확인
echo -e "${YELLOW}[1] API 상태 확인${NC}"
if curl -sf "$API_BASE/health" > /dev/null 2>&1; then
  echo -e "  ${GREEN}OK${NC} - API 정상 동작 중"
else
  echo -e "  API가 응답하지 않습니다. demo_up.sh를 먼저 실행하세요."
  exit 1
fi
echo ""

# 테스트 함수
run_compare() {
  local query="$1"
  local codes="$2"
  local name="$3"

  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${YELLOW}[$name]${NC} 질의: \"$query\""
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  RESPONSE=$(curl -sf -X POST "$API_BASE/compare" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"$query\",\"insurers\":[\"SAMSUNG\",\"MERITZ\"]$codes}" 2>/dev/null)

  if [ -z "$RESPONSE" ]; then
    echo "  API 호출 실패"
    return
  fi

  # 결과 파싱
  echo "$RESPONSE" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)

    # compare_axis 요약
    axis = data.get('compare_axis', [])
    print(f'\n  📊 compare_axis: {len(axis)}건')

    by_insurer = {}
    for item in axis:
        ic = item.get('insurer_code', 'UNKNOWN')
        by_insurer[ic] = by_insurer.get(ic, 0) + 1
    for ic, cnt in sorted(by_insurer.items()):
        print(f'     - {ic}: {cnt}건')

    # diff_summary 요약
    diff = data.get('diff_summary', [])
    if diff:
        print(f'\n  📋 diff_summary: {len(diff)}개 항목')
        for i, d in enumerate(diff[:3]):
            name = d.get('coverage_name') or d.get('coverage_code', '?')
            bullets = d.get('bullets', [])
            print(f'     {i+1}. [{name}] {len(bullets)}개 비교 포인트')
            for b in bullets[:2]:
                text = b.get('text', '')[:60]
                print(f'        • {text}...' if len(b.get('text',''))>60 else f'        • {text}')

    # coverage_compare 요약
    cc = data.get('coverage_compare', [])
    if cc:
        print(f'\n  📈 coverage_compare: {len(cc)}개 담보')
        for row in cc[:3]:
            code = row.get('coverage_code', '?')
            name = row.get('coverage_name', '')
            print(f'     - {code}: {name[:20]}')

    # policy_axis 요약
    policy = data.get('policy_axis', [])
    if policy:
        policy_count = sum(len(p.get('evidence', [])) for p in policy)
        print(f'\n  📜 policy_axis (약관): {policy_count}건')

    print()

except Exception as e:
    print(f'  파싱 오류: {e}')
"
}

# 커스텀 질의가 있으면 실행
if [ -n "$1" ]; then
  echo -e "${YELLOW}[2] 커스텀 질의 테스트${NC}"
  run_compare "$1" "" "커스텀"
  echo ""
  echo -e "${GREEN}테스트 완료!${NC}"
  echo ""
  exit 0
fi

# 기본 테스트 시나리오
echo -e "${YELLOW}[2] 테스트 시나리오 실행${NC}"
echo ""

# 시나리오 A: 안정성 테스트
run_compare "암입원일당 질병수술비" ",\"coverage_codes\":[\"A6200\",\"A5100\"]" "시나리오 A: 안정성"

# 시나리오 B: 경계성종양 (고객 시나리오)
run_compare "경계성종양 암진단비" ",\"coverage_codes\":[\"A4200_1\",\"A4210\"]" "시나리오 B: 경계성종양"

# 시나리오 C: 자유 질의 (coverage_code 없이)
run_compare "암 진단받으면 얼마 받아요?" "" "시나리오 C: 자유 질의"

# 시나리오 D: 수술비 비교
run_compare "질병수술비 비교해줘" ",\"coverage_codes\":[\"A5100\"]" "시나리오 D: 수술비"

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  테스트 완료!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""
echo -e "  ${BLUE}Web UI 테스트:${NC} ${GREEN}http://localhost${NC}"
echo ""
echo -e "  ${BLUE}추가 테스트:${NC}"
echo "    ./tools/user_test.sh \"원하는 질의\""
echo ""
