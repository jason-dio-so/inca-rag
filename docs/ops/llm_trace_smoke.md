# LLM Trace Smoke Test (U-4.8.1)

LLM 사용 추적 기능의 스모크 테스트 실행 방법

## 개요

U-4.8.1에서는 슬롯 추출 시 LLM 사용 여부를 추적합니다:
- `llm_used`: LLM 호출 여부
- `method`: `rule` | `llm` | `hybrid`
- `llm_reason`: `flag_off` | `cost_guard` | `not_needed`
- `model`: LLM 모델명 (llm_used=true일 때만)

## 테스트 모드

| 테스트 | 환경 설정 | 기대 결과 |
|--------|-----------|-----------|
| LLM_OFF_smoke | `LLM_ENABLED=0` (기본) | `llm_used=false`, `reason=flag_off` |
| LLM_ON_smoke | `LLM_ENABLED=1` | `llm_used=true`, `method=llm\|hybrid`, `model` 설정됨 |
| COST_GUARD_smoke | `LLM_ENABLED=1` + `LLM_COST_GUARD=1` | `llm_used=false`, `reason=cost_guard` |

## 실행 방법

### 1. LLM_OFF_smoke (기본)

```bash
# 기본 모드로 테스트 (데모 환경이 이미 실행 중이라면)
./tools/run_llm_trace_smoke.sh

# 또는 Makefile 사용
make llm-off
./tools/run_llm_trace_smoke.sh
```

**기대 결과:**
```
[2] LLM_OFF_smoke (LLM_ENABLED=0)
  PASS - All traces llm_used=false (total=10,flag_off=4,not_needed=6)
```

### 2. LLM_ON_smoke (PASS 찍는 방법)

```bash
# Step 1: LLM_ENABLED=1로 API 재시작
make llm-on

# Step 2: LLM_ON 테스트 실행
./tools/run_llm_trace_smoke.sh --llm-on
```

**기대 결과:**
```
[Container Environment]
  LLM_ENABLED=1
  LLM_COST_GUARD=0
  LLM_MODEL=gpt-4o-mini

[4] LLM_ON_smoke (LLM_ENABLED=1, LLM_COST_GUARD=0)
  PASS - LLM ON verified (llm_used=true,method=llm,model=gpt-4o-mini)
```

### 3. COST_GUARD_smoke (PASS 찍는 방법)

```bash
# Step 1: LLM_ENABLED=1 + LLM_COST_GUARD=1로 API 재시작
make cost-guard

# Step 2: COST_GUARD 테스트 실행
./tools/run_llm_trace_smoke.sh --cost-guard
```

**기대 결과:**
```
[Container Environment]
  LLM_ENABLED=1
  LLM_COST_GUARD=1
  LLM_MODEL=gpt-4o-mini

[5] COST_GUARD_smoke (LLM_ENABLED=1 + LLM_COST_GUARD=1)
  PASS - llm_used=false,reason=cost_guard
```

### 4. 모든 테스트 실행

```bash
# 현재 컨테이너 설정에 맞는 테스트만 실행됨
# 설정이 맞지 않으면 SKIP 처리
./tools/run_llm_trace_smoke.sh --all
```

## 기본 상태로 복원

```bash
make llm-off
./tools/run_llm_trace_smoke.sh
```

## Docker Compose Override 파일

| 파일 | 용도 |
|------|------|
| `ops/compose.override.llm-on.yml` | `LLM_ENABLED=1` |
| `ops/compose.override.cost-guard.yml` | `LLM_ENABLED=1` + `LLM_COST_GUARD=1` |

## 환경 변수

스모크 테스트 스크립트에서 사용하는 환경 변수:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `API_BASE` | `http://localhost:8000` | API 엔드포인트 |
| `DEMO_API_CONTAINER` | `inca_demo_api` | Docker 컨테이너 이름 |

## A2 정책 일관성

약관 기반 슬롯(policy-only)은 항상 `llm_reason=not_needed`로 설정됨:
- `diagnosis_scope_definition`
- `waiting_period`

이는 A2 정책에 따라 약관은 비교 계산에 사용하지 않기 때문입니다.

## 관련 파일

- `services/extraction/llm_trace.py` - LLMTrace 데이터클래스
- `services/extraction/llm_client.py` - LLM 플래그 함수
- `services/extraction/slot_extractor.py` - 슬롯 추출 + 트레이스
- `tools/run_llm_trace_smoke.sh` - 스모크 테스트 스크립트
