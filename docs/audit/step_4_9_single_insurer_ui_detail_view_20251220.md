# STEP 4.9: Single-Insurer Locked Coverage Detail View

**Date**: 2025-12-20
**Status**: PASS

## 1. 목적

단일 보험사(single insurer) + 특정 담보 고정(locked_coverage_codes 제공) 시,
기존 "비교 테이블/멀티 비교 UI"를 그대로 쓰지 않고 **전용 상세 뷰**로 전환한다.

## 2. 전환 조건 (Contract)

다음 조건을 **모두** 만족하면 UI는 `SingleCoverageDetailView`로 전환:

```
selectedInsurers.length == 1
AND debug.anchor.coverage_locked == true
AND debug.anchor.locked_coverage_codes.length >= 1
```

**정답 경로**:
- Lock 판단: `debug.anchor.coverage_locked`, `debug.anchor.locked_coverage_codes`
- 후보 추천: `coverage_resolution.suggested_coverages`
- 결과 축: `coverage_compare_result[*].coverage_code`

## 3. UI Mode 결정 함수

```typescript
function determineUIMode(selectedInsurers, response): UIMode {
  // 조건 1: 단일 insurer + locked → SINGLE_DETAIL
  if (
    selectedInsurers.length === 1 &&
    response.debug.anchor.coverage_locked === true &&
    response.debug.anchor.locked_coverage_codes.length >= 1
  ) {
    return "SINGLE_DETAIL";
  }

  // 조건 2: UNRESOLVED + 후보 존재 → GUIDE
  if (
    response.resolution_state === "UNRESOLVED" &&
    response.coverage_resolution.suggested_coverages.length > 0
  ) {
    return "GUIDE";
  }

  // 기본: COMPARE
  return "COMPARE";
}
```

## 4. 검증 시나리오

### 4.1 시나리오 A: 단일 insurer, UNRESOLVED → 가이드 노출

**요청**:
```json
{"query":"암진단비","insurers":["SAMSUNG"]}
```

**결과**:
```
resolution_state: UNRESOLVED
suggested_coverages.length: 3
expected UI mode: GUIDE ✅
```

### 4.2 시나리오 B: 단일 insurer + locked → 상세 뷰 전환

**요청**:
```json
{"query":"암진단비","insurers":["SAMSUNG"],"locked_coverage_codes":["A4200_1"]}
```

**결과**:
```
resolution_state: RESOLVED
debug.anchor.coverage_locked: True
debug.anchor.locked_coverage_codes: ['A4200_1']
coverage_compare_result.coverage_codes: ['A4200_1']
debug.retrieval.fallback_used: True
  - fallback_reason: no_tagged_chunks_for_locked_code
  - fallback_source: amount_pass_2
  - effective_locked_code: A4200_1
expected UI mode: SINGLE_DETAIL ✅
```

### 4.3 시나리오 C: 2개 insurer + locked → COMPARE 뷰 유지

**요청**:
```json
{"query":"암진단비","insurers":["SAMSUNG","MERITZ"],"locked_coverage_codes":["A4200_1"]}
```

**결과**:
```
resolution_state: RESOLVED
debug.anchor.coverage_locked: True
insurers: 2개 → expected UI mode: COMPARE ✅
```

## 5. 구현 내용

### 5.1 새 컴포넌트

**파일**: `apps/web/src/components/SingleCoverageDetailView.tsx`

구성:
1. **헤더**: 보험사명, 담보명, coverage_code, "담보 변경(UNLOCK)" 버튼
2. **담보 정보 카드**: best_evidence 기반 금액 정보 (resolved_amount 생성 금지)
3. **Slots 테이블**: singleInsurer 모드로 단일 보험사만 표시
4. **근거(Evidence) 섹션**: EvidencePanel 재사용
5. **Debug 섹션**: 개발자/QA 전용 (Contract 경로 표시)

### 5.2 금액 표시 규칙 (STEP 4.9 원칙)

- `resolved_amount` 같은 필드 생성 금지
- best_evidence 기반으로만 표시:
  1. `best_evidence[].amount.amount_value` 우선
  2. `best_evidence[].amount.amount_text` 차선
  3. 둘 다 없으면 "금액 정보 없음" (중립 문구)

### 5.3 page.tsx 변경

- `determineUIMode()` 함수로 UI 모드 결정
- `uiMode === "SINGLE_DETAIL"` → `SingleCoverageDetailView` 렌더링
- 그 외 → `ResultsPanel` 렌더링

### 5.4 SlotsTable 변경

- `singleInsurer?: string` prop 추가
- 단일 보험사일 때:
  - 해당 insurer만 필터링
  - "차이 요약" 열 숨김

## 6. 파일 변경 목록

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/components/SingleCoverageDetailView.tsx` | 신규 - 단일 상세 뷰 컴포넌트 + determineUIMode 함수 |
| `apps/web/src/components/SlotsTable.tsx` | singleInsurer prop 추가, 필터링 로직 |
| `apps/web/src/app/page.tsx` | UI Mode 분기, SingleCoverageDetailView 연결 |

## 7. 금지 사항 준수

- ✅ `debug.locked_coverage_codes` 최상위 경로 참조 금지 → `debug.anchor.*` 사용
- ✅ 단일 insurer에서 비교 테이블 그대로 표시 금지 → 전용 상세 뷰 사용
- ✅ slot/evidence 없이 요약 문구 생성 금지 → "근거 문서에서 확인 필요"
- ✅ `resolved_amount` 생성 금지 → best_evidence 기반 표시
- ✅ `coverage_code="__amount_fallback__"` 노출 금지 → effective_locked_code 유지
