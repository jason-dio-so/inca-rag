#!/bin/bash
# =============================================================================
# LLM Trace Smoke Test (U-4.8.1)
#
# Tests LLM usage trace across the extraction pipeline
#
# Usage:
#   ./tools/run_llm_trace_smoke.sh              # Default: LLM OFF test only
#   ./tools/run_llm_trace_smoke.sh --all        # Run all tests
#   ./tools/run_llm_trace_smoke.sh --llm-on     # LLM_ON_smoke only
#   ./tools/run_llm_trace_smoke.sh --cost-guard # COST_GUARD_smoke only
#
# Environment Variables:
#   API_BASE           - API endpoint (default: http://localhost:8000)
#   DEMO_API_CONTAINER - Docker container name (default: inca_demo_api)
#
# Env var tests:
#   LLM_ENABLED=0 (default): llm_used=false, reason=flag_off
#   LLM_ENABLED=1: llm_used=true, method=llm|hybrid, model set
#   LLM_ENABLED=1 + LLM_COST_GUARD=1: llm_used=false, reason=cost_guard
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

API_BASE="${API_BASE:-http://localhost:8000}"
CONTAINER_NAME="${DEMO_API_CONTAINER:-inca_demo_api}"
RUN_MODE="${1:-default}"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Helper: get container env var
get_container_env() {
  local var_name="$1"
  local default_val="${2:-}"
  local val
  val=$(docker exec "$CONTAINER_NAME" printenv "$var_name" 2>/dev/null || echo "$default_val")
  echo "$val"
}

# Helper: wait for API
wait_for_api() {
  local max_attempts=10
  local attempt=1
  while [ $attempt -le $max_attempts ]; do
    if curl -sf "$API_BASE/health" > /dev/null 2>&1; then
      return 0
    fi
    sleep 1
    ((attempt++))
  done
  return 1
}

# Helper: make API call and get response
call_api() {
  curl -sf -X POST "$API_BASE/compare" \
    -H "Content-Type: application/json" \
    -d '{"query":"암진단비 비교","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A4200_1"]}' 2>/dev/null
}

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  LLM Trace Smoke Test (U-4.8.1)${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo -e "  API_BASE: $API_BASE"
echo -e "  Container: $CONTAINER_NAME"
echo ""

# API health check
echo -e "${YELLOW}[1] API Health Check${NC}"
if curl -sf "$API_BASE/health" > /dev/null 2>&1; then
  echo -e "  ${GREEN}OK${NC} - API is running"
else
  echo -e "  ${RED}FAIL${NC} - API is not responding"
  exit 1
fi

# Show current container env
echo ""
echo -e "${YELLOW}[Container Environment]${NC}"
LLM_ENABLED_VAL=$(get_container_env "LLM_ENABLED" "0")
LLM_COST_GUARD_VAL=$(get_container_env "LLM_COST_GUARD" "0")
LLM_MODEL_VAL=$(get_container_env "LLM_MODEL" "gpt-4o-mini")
echo -e "  LLM_ENABLED=$LLM_ENABLED_VAL"
echo -e "  LLM_COST_GUARD=$LLM_COST_GUARD_VAL"
echo -e "  LLM_MODEL=$LLM_MODEL_VAL"
echo ""

# =============================================================================
# Test 1: LLM_OFF_smoke (default)
# =============================================================================
if [ "$RUN_MODE" = "default" ] || [ "$RUN_MODE" = "--all" ]; then
  echo -e "${YELLOW}[2] LLM_OFF_smoke (LLM_ENABLED=0)${NC}"

  # Check if this test applies to current config
  if [ "$LLM_ENABLED_VAL" != "0" ]; then
    echo -e "  ${YELLOW}SKIP${NC} - LLM_ENABLED=$LLM_ENABLED_VAL (expected 0)"
    ((SKIP_COUNT++))
  else
    RESPONSE=$(call_api)

    if [ -z "$RESPONSE" ]; then
      echo -e "  ${RED}FAIL${NC} - No API response"
      ((FAIL_COUNT++))
    else
      TRACE_CHECK=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    slots = data.get('slots', [])
    if not slots:
        print('NO_SLOTS|0')
        sys.exit(0)

    llm_off_count = 0
    flag_off_count = 0
    not_needed_count = 0
    total_traces = 0

    for slot in slots:
        slot_key = slot.get('slot_key', '')
        for iv in slot.get('insurers', []):
            trace = iv.get('trace')
            if trace:
                total_traces += 1
                if not trace.get('llm_used', True):
                    llm_off_count += 1
                    reason = trace.get('llm_reason', '')
                    if reason == 'flag_off':
                        flag_off_count += 1
                    elif reason == 'not_needed':
                        not_needed_count += 1

    if llm_off_count == total_traces:
        print(f'PASS|total={total_traces},flag_off={flag_off_count},not_needed={not_needed_count}')
    else:
        print(f'FAIL|llm_used=true found in {total_traces - llm_off_count} traces')
except Exception as e:
    print(f'ERROR|{e}')
" 2>/dev/null || echo "ERROR|parse_failed")

      STATUS=$(echo "$TRACE_CHECK" | cut -d'|' -f1)
      DETAILS=$(echo "$TRACE_CHECK" | cut -d'|' -f2)

      if [ "$STATUS" = "PASS" ]; then
        echo -e "  ${GREEN}PASS${NC} - All traces llm_used=false (${DETAILS})"
        ((PASS_COUNT++))
      elif [ "$STATUS" = "NO_SLOTS" ]; then
        echo -e "  ${YELLOW}SKIP${NC} - No slots in response"
        ((SKIP_COUNT++))
      else
        echo -e "  ${RED}FAIL${NC} - ${DETAILS}"
        ((FAIL_COUNT++))
      fi
    fi
  fi
  echo ""
fi

# =============================================================================
# Test 2: A2 Policy Consistency (not_needed for policy-only slots)
# =============================================================================
if [ "$RUN_MODE" = "default" ] || [ "$RUN_MODE" = "--all" ]; then
  echo -e "${YELLOW}[3] A2 Policy Consistency (not_needed for policy-only slots)${NC}"

  RESPONSE=$(call_api)

  if [ -z "$RESPONSE" ]; then
    echo -e "  ${RED}FAIL${NC} - No API response"
    ((FAIL_COUNT++))
  else
    A2_CHECK=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    slots = data.get('slots', [])
    if not slots:
        print('NO_SLOTS')
        sys.exit(0)

    # Policy-only slots (A2: comparable=false)
    policy_slots = ['diagnosis_scope_definition', 'waiting_period']

    errors = []
    checked = 0

    for slot in slots:
        slot_key = slot.get('slot_key', '')
        if slot_key in policy_slots:
            for iv in slot.get('insurers', []):
                trace = iv.get('trace')
                if trace:
                    checked += 1
                    reason = trace.get('llm_reason', '')
                    if reason != 'not_needed':
                        errors.append(f'{slot_key}: reason={reason} (expected not_needed)')

    if checked == 0:
        print('NO_POLICY_SLOTS')
    elif errors:
        print(f'FAIL|{errors[0]}')
    else:
        print(f'PASS|{checked} policy slot traces verified')
except Exception as e:
    print(f'ERROR|{e}')
" 2>/dev/null || echo "ERROR|parse_failed")

    STATUS=$(echo "$A2_CHECK" | cut -d'|' -f1)
    DETAILS=$(echo "$A2_CHECK" | cut -d'|' -f2)

    if [ "$STATUS" = "PASS" ]; then
      echo -e "  ${GREEN}PASS${NC} - ${DETAILS}"
      ((PASS_COUNT++))
    elif [ "$STATUS" = "NO_SLOTS" ] || [ "$STATUS" = "NO_POLICY_SLOTS" ]; then
      echo -e "  ${YELLOW}SKIP${NC} - No policy slots found"
      ((SKIP_COUNT++))
    else
      echo -e "  ${RED}FAIL${NC} - ${DETAILS}"
      ((FAIL_COUNT++))
    fi
  fi
  echo ""
fi

# =============================================================================
# Test 3: LLM_ON_smoke (requires LLM_ENABLED=1, LLM_COST_GUARD=0)
# =============================================================================
if [ "$RUN_MODE" = "--llm-on" ] || [ "$RUN_MODE" = "--all" ]; then
  echo -e "${YELLOW}[4] LLM_ON_smoke (LLM_ENABLED=1, LLM_COST_GUARD=0)${NC}"

  # Check if this test applies to current config
  if [ "$LLM_ENABLED_VAL" != "1" ]; then
    echo -e "  ${YELLOW}SKIP${NC} - LLM_ENABLED=$LLM_ENABLED_VAL (expected 1)"
    echo -e "  Run: make llm-on && ./tools/run_llm_trace_smoke.sh --llm-on"
    ((SKIP_COUNT++))
  elif [ "$LLM_COST_GUARD_VAL" = "1" ]; then
    echo -e "  ${YELLOW}SKIP${NC} - LLM_COST_GUARD=1 (expected 0 for LLM_ON test)"
    echo -e "  Run: make llm-on && ./tools/run_llm_trace_smoke.sh --llm-on"
    ((SKIP_COUNT++))
  else
    RESPONSE=$(call_api)

    if [ -z "$RESPONSE" ]; then
      echo -e "  ${RED}FAIL${NC} - No API response"
      ((FAIL_COUNT++))
    else
      LLM_ON_CHECK=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    slots = data.get('slots', [])
    if not slots:
        print('NO_SLOTS')
        sys.exit(0)

    # Comparable slots should have llm_used=true when LLM_ENABLED=1
    comparable_slots = ['payout_amount', 'payout_condition_summary']

    llm_on_found = False
    model_found = None
    method_found = None

    for slot in slots:
        slot_key = slot.get('slot_key', '')
        if slot_key in comparable_slots:
            for iv in slot.get('insurers', []):
                trace = iv.get('trace')
                if trace and trace.get('llm_used'):
                    llm_on_found = True
                    model_found = trace.get('model', 'unknown')
                    method_found = trace.get('method', 'unknown')
                    if method_found in ('llm', 'hybrid') and model_found:
                        print(f'PASS|llm_used=true,method={method_found},model={model_found}')
                        sys.exit(0)

    if llm_on_found and model_found:
        print(f'PASS|llm_used=true,method={method_found},model={model_found}')
    else:
        print('FAIL|No llm_used=true found in comparable slots')
except Exception as e:
    print(f'ERROR|{e}')
" 2>/dev/null || echo "ERROR|parse_failed")

      STATUS=$(echo "$LLM_ON_CHECK" | cut -d'|' -f1)
      DETAILS=$(echo "$LLM_ON_CHECK" | cut -d'|' -f2)

      if [ "$STATUS" = "PASS" ]; then
        echo -e "  ${GREEN}PASS${NC} - LLM ON verified (${DETAILS})"
        ((PASS_COUNT++))
      elif [ "$STATUS" = "NO_SLOTS" ]; then
        echo -e "  ${YELLOW}SKIP${NC} - No slots in response"
        ((SKIP_COUNT++))
      else
        echo -e "  ${RED}FAIL${NC} - ${DETAILS}"
        ((FAIL_COUNT++))
      fi
    fi
  fi
  echo ""
fi

# =============================================================================
# Test 4: COST_GUARD_smoke (requires LLM_ENABLED=1 + LLM_COST_GUARD=1)
# =============================================================================
if [ "$RUN_MODE" = "--cost-guard" ] || [ "$RUN_MODE" = "--all" ]; then
  echo -e "${YELLOW}[5] COST_GUARD_smoke (LLM_ENABLED=1 + LLM_COST_GUARD=1)${NC}"

  # Check if this test applies to current config
  if [ "$LLM_ENABLED_VAL" != "1" ] || [ "$LLM_COST_GUARD_VAL" != "1" ]; then
    echo -e "  ${YELLOW}SKIP${NC} - LLM_ENABLED=$LLM_ENABLED_VAL, LLM_COST_GUARD=$LLM_COST_GUARD_VAL"
    echo -e "  Run: make cost-guard && ./tools/run_llm_trace_smoke.sh --cost-guard"
    ((SKIP_COUNT++))
  else
    RESPONSE=$(call_api)

    if [ -z "$RESPONSE" ]; then
      echo -e "  ${RED}FAIL${NC} - No API response"
      ((FAIL_COUNT++))
    else
      COST_GUARD_CHECK=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    slots = data.get('slots', [])
    if not slots:
        print('NO_SLOTS')
        sys.exit(0)

    # Comparable slots should have llm_used=false, reason=cost_guard
    comparable_slots = ['payout_amount', 'payout_condition_summary']

    cost_guard_found = False
    errors = []

    for slot in slots:
        slot_key = slot.get('slot_key', '')
        if slot_key in comparable_slots:
            for iv in slot.get('insurers', []):
                trace = iv.get('trace')
                if trace:
                    if trace.get('llm_used'):
                        errors.append(f'{slot_key}: llm_used=true (expected false)')
                    elif trace.get('llm_reason') == 'cost_guard':
                        cost_guard_found = True
                    elif trace.get('llm_reason') != 'cost_guard':
                        errors.append(f'{slot_key}: reason={trace.get(\"llm_reason\")} (expected cost_guard)')

    if errors:
        print(f'FAIL|{errors[0]}')
    elif cost_guard_found:
        print('PASS|llm_used=false,reason=cost_guard')
    else:
        print('FAIL|No cost_guard reason found')
except Exception as e:
    print(f'ERROR|{e}')
" 2>/dev/null || echo "ERROR|parse_failed")

      STATUS=$(echo "$COST_GUARD_CHECK" | cut -d'|' -f1)
      DETAILS=$(echo "$COST_GUARD_CHECK" | cut -d'|' -f2)

      if [ "$STATUS" = "PASS" ]; then
        echo -e "  ${GREEN}PASS${NC} - ${DETAILS}"
        ((PASS_COUNT++))
      elif [ "$STATUS" = "NO_SLOTS" ]; then
        echo -e "  ${YELLOW}SKIP${NC} - No slots in response"
        ((SKIP_COUNT++))
      else
        echo -e "  ${RED}FAIL${NC} - ${DETAILS}"
        ((FAIL_COUNT++))
      fi
    fi
  fi
  echo ""
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo -e "  ${GREEN}PASS: $PASS_COUNT${NC}"
echo -e "  ${RED}FAIL: $FAIL_COUNT${NC}"
echo -e "  ${YELLOW}SKIP: $SKIP_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -gt 0 ]; then
  echo -e "  ${RED}Some tests FAILED${NC}"
  exit 1
else
  echo -e "  ${GREEN}All executed tests PASSED${NC}"
fi

echo ""
echo -e "  ${BLUE}Quick Commands:${NC}"
echo -e "    make llm-on && ./tools/run_llm_trace_smoke.sh --llm-on"
echo -e "    make cost-guard && ./tools/run_llm_trace_smoke.sh --cost-guard"
echo -e "    make llm-off  # Reset to default"
echo ""
