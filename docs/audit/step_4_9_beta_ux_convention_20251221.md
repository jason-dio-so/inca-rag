# STEP 4.9-β: Diff / Compare / Evidence 공통 UX 규약 고정

## 날짜
2025-12-21

## 목적

엔진 언어 → 사용자 언어 번역 규약 고정

- 내부 식별자(coverage_code, __amount_fallback__, axis key)를 사용자에게 노출하지 않음
- 모든 탭에서 display name만 사용
- fallback 여부는 Debug/Audit 영역에서만 확인 가능

---

## 변경 사항

### 1. DiffSummary.tsx

**Before:**
```tsx
<Badge variant="outline">{item.coverage_code}</Badge>
<span className="font-medium">{displayName}</span>
...
<p className="text-sm text-muted-foreground ml-2">
  상세 차이점 정보 없음
</p>
```

**After:**
```tsx
<span className="font-medium text-base">{displayName}</span>
...
<p className="text-sm text-muted-foreground">
  보험사 간 차이가 없습니다
</p>
{isAmountFallback && (
  <p className="text-xs text-muted-foreground mt-1">
    ※ 금액 근거 기준으로 산출되었습니다.
  </p>
)}
```

**규칙:**
- coverage_code Badge 제거
- "상세 차이점 정보 없음" → "보험사 간 차이가 없습니다"
- fallback은 footnote로만 간접 표현

---

### 2. CompareTable.tsx

**Before:**
```tsx
<td className="p-3 font-medium">
  <div>{item.coverage_name || item.coverage_code}</div>
  {item.coverage_name && (
    <div className="text-xs text-muted-foreground">
      {item.coverage_code}
    </div>
  )}
</td>
```

**After:**
```tsx
<td className="p-3 font-medium">
  <div>{item.coverage_name || "담보"}</div>
</td>
```

**규칙:**
- coverage_code 보조 텍스트 제거
- fallback 시 기본값 "담보" 사용

---

### 3. ResultsPanel.tsx

**Before:**
```tsx
<Badge variant="default" className="text-sm">
  {response.primary_coverage_name}
</Badge>
<span className="text-xs text-muted-foreground">
  ({response.primary_coverage_code})
</span>
```

**After:**
```tsx
<Badge variant="default" className="text-sm">
  {response.primary_coverage_name}
</Badge>
```

**규칙:**
- 헤더에서 coverage_code 제거
- display name만 표시

---

## UX 규약 요약

| 영역 | 허용 | 금지 |
|------|------|------|
| Diff 탭 제목 | display name | coverage_code, __amount_fallback__ |
| Compare 탭 담보명 | display name | coverage_code 보조 텍스트 |
| Evidence 탭 그룹 | 보험사명 | axis key, internal id |
| 헤더 | display name | coverage_code |
| 차이 없음 | "보험사 간 차이가 없습니다" | "상세 차이점 정보 없음" |
| fallback 표현 | footnote (※ 금액 근거...) | "fallback", "__amount_fallback__" |

---

## 테스트 결과

### 시나리오 1: 복수 보험사 비교
- 쿼리: "삼성 메리츠 암진단비 비교"
- 결과: ✅ 모든 탭에서 coverage_code 미노출

### 시나리오 2: 단일 보험사 조회
- 쿼리: "삼성 암진단비"
- 결과: ✅ 내부 식별자 미노출

### 시나리오 3: 차이 없음 케이스
- 결과: ✅ "보험사 간 차이가 없습니다" 표시

---

## DoD 체크리스트

- [x] Diff 탭에서 `__amount_fallback__` 노출되지 않음
- [x] Compare 탭에서 coverage_code 노출되지 않음
- [x] Evidence 탭에서 fallback 레이블 노출되지 않음
- [x] 모든 탭에서 담보명이 display name으로 일관됨
- [x] fallback 발생 여부는 UI 판단에 영향을 주지 않음
- [x] Debug 섹션에서만 fallback 추적 가능
- [x] 단일/복수 insurer 시나리오 UX 일관성 유지

---

## 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `apps/web/src/components/DiffSummary.tsx` | coverage_code Badge 제거, 차이없음 문구 변경 |
| `apps/web/src/components/CompareTable.tsx` | coverage_code 보조 텍스트 제거 |
| `apps/web/src/components/ResultsPanel.tsx` | 헤더에서 coverage_code 제거 |

---

## 결론

STEP 4.9-β 완료. 모든 사용자 대면 UI에서 내부 식별자가 제거되고, display name만 표시됩니다.
