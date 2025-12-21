
# STEP 4.7-γ: Single-Insurer Locked Coverage E2E Verification

**Date**: 2024-12-20
**Status**: PASS
**Commit**: 5c690b7 (STEP 4.7-β)

## 1. 검증 목적

- 단일 insurer + 특정 담보(`locked_coverage_codes`) 조회가 정상 동작하는지 검증
- DB에 coverage_code 태깅이 0건이어도 2-pass amount fallback이 발생할 때,
  결과 축(coverage_code)의 정체성이 locked code로 고정되는지 확인

## 2. 검증 시나리오

### 2.1 테스트 요청
```json
{
  "query": "암진단비",
  "insurers": ["SAMSUNG"],
  "locked_coverage_codes": ["A4200_1"]
}
```

### 2.2 사전 조건
- SAMSUNG에 `A4200_1` 태깅된 청크: **0건** (DB 확인 완료)
- 2-pass amount retrieval fallback 발생 예상

## 3. 검증 결과

### 3.1 E2E 테스트 출력
```
resolution_state: RESOLVED
debug.anchor: {
  'has_anchor': False,
  'has_coverage_keyword': True,
  'extracted_insurers': [],
  'reason': 'no_anchor',
  'query_type': 'new',
  'locked_coverage_codes': ['A4200_1'],
  'coverage_locked': True
}
coverage_compare_result_len: 1
coverage_compare_result.coverage_codes: ['A4200_1']
debug.retrieval: {
  'fallback_used': True,
  'fallback_reason': 'no_tagged_chunks_for_locked_code',
  'fallback_source': 'amount_pass_2',
  'effective_locked_code': 'A4200_1'
}
```

### 3.2 PASS 기준 검증

| 기준 | 결과 | 상태 |
|------|------|------|
| `debug.anchor.coverage_locked == true` | true | ✅ PASS |
| `debug.anchor.locked_coverage_codes` 포함 | ["A4200_1"] | ✅ PASS |
| `coverage_compare_result[*].coverage_code == "A4200_1"` | ["A4200_1"] | ✅ PASS |
| `coverage_code != "__amount_fallback__"` | A4200_1 | ✅ PASS |
| `debug.retrieval.fallback_used` 기록 | true | ✅ PASS |
| `debug.retrieval.fallback_reason` | no_tagged_chunks_for_locked_code | ✅ PASS |
| `debug.retrieval.effective_locked_code` | A4200_1 | ✅ PASS |

## 4. 코드 검증

### 4.1 compare_service.py 변경사항 확인
- `locked_coverage_codes` 인자 추가 (line 1720)
- `effective_locked_code` 결정 로직 (line 1908-1912)
- fallback 시 coverage_code 정체성 유지 (line 1969-1980)

### 4.2 api/compare.py 변경사항 확인
- `locked_coverage_codes` → `compare()` 함수 전달 (line 1598-1599)
- `anchor_debug.locked_coverage_codes`, `coverage_locked` 기록 (line 1579-1580)

## 5. 이슈 및 해결

### 5.1 초기 FAIL
- **원인**: Docker 컨테이너에 최신 코드가 반영되지 않음
- **증상**: `coverage_compare_result.coverage_codes: ['__amount_fallback__']`
- **해결**: `docker compose -f docker-compose.demo.yml build api --no-cache` 후 재테스트

### 5.2 해결 후 PASS
- rebuild 후 최신 코드 반영 확인
- 모든 검증 기준 통과

## 6. 결론

STEP 4.7-β 변경사항이 E2E 환경에서 정상 동작함을 확인.
- **축 정체성 유지**: `locked_coverage_codes` 제공 시 fallback이 발생해도 coverage_code가 locked code로 유지됨
- **debug 경로 준수**: `debug.anchor.coverage_locked`, `debug.retrieval.*` 필드가 규약대로 기록됨
