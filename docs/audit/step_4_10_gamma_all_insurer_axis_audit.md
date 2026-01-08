# STEP 4.10-γ: 전 보험사 Coverage Alias / Axis 생성 전수 검증

## 날짜
2025-12-21

## 목적

모든 보험사에 대해 특정 담보(coverage_code)가 주어졌을 때 alias_text_match 기반으로 compare_axis(증거 축)를 생성할 수 있는지 검증

---

## 검증 범위

### 대상 보험사
- DB, HANWHA, HEUNGKUK, HYUNDAI, KB, LOTTE, MERITZ, SAMSUNG (총 8개)

### 기준 담보
- A9630_1: 다빈치/로봇 암수술비

### 검증 시나리오
```bash
curl -s 'http://localhost:8000/compare' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "다빈치로봇암수술비",
    "insurers": ["<INSURER_CODE>"],
    "locked_coverage_codes": ["A9630_1"]
  }'
```

---

## 1차 검증 결과 (alias 보강 전)

| insurer_code | axis_strategy | alias_used | axis_len | result | 비고 |
|--------------|---------------|------------|----------|--------|------|
| DB | alias_text_match | true | 8 | ✅ GREEN | 연간1회한 |
| HANWHA | alias_text_match | true | 4 | ✅ GREEN | - |
| HEUNGKUK | alias_text_match | true | 0 | ❌ RED | alias suffix 불일치 |
| HYUNDAI | alias_text_match | true | 10 | ✅ GREEN | 다빈치/레보아이 |
| KB | alias_text_match | true | 0 | ❌ RED | alias suffix 불일치 |
| LOTTE | alias_text_match | true | 4 | ✅ GREEN | - |
| MERITZ | alias_text_match | true | 10 | ✅ GREEN | - |
| SAMSUNG | alias_text_match | true | 0 | ❌ RED | alias prefix/공백 불일치 |

---

## RED 케이스 분석

### HEUNGKUK
- **기존 alias**: `다빈치및레보아이로봇 암수술비(갑상선암 및 전립선암 제외)(최초1회한)(갱신형_10년)`
- **chunk 실제 표현**: `다빈치및레보아이로봇 암수술비(갑상선암 및 전립선암 제외)` (suffix 없음)
- **원인**: alias가 너무 구체적 (갱신형_10년 suffix 포함)

### KB
- **기존 alias**: `다빈치로봇 암수술비(갑상선암 및 전립선암 제외)(최초1회한)【갱신계약】`
- **chunk 실제 표현**: `다빈치로봇 암수술비(갑상선암 및 전립선암 제외)` (【갱신계약】 없음)
- **원인**: alias에 【갱신계약】 suffix 포함

### SAMSUNG
- **기존 alias**: `[갱신형]특정암 다빈치로봇 수술비(1년 감액)`
- **chunk 실제 표현**: `다빈치로봇 수술비(1년감액)` ([갱신형] prefix 없음, 공백 차이)
- **원인**: alias prefix 및 공백 불일치

---

## 보강 작업

### HEUNGKUK alias 추가 (5건)
```sql
INSERT INTO coverage_alias (insurer_id, coverage_code, raw_name, raw_name_norm, source_doc_type)
VALUES
    (7, 'A9630_1', '다빈치및레보아이로봇 암수술비(갑상선암 및 전립선암 제외)', ...),
    (7, 'A9630_1', '다빈치및레보아이로봇 암수술비(갑상선암 및 전립선암)', ...),
    (7, 'A9630_1', '다빈치및레보아이로봇 암수술비(최초1회한)', ...),
    (7, 'A9630_1', '다빈치및레보아이로봇 암수술비', ...),
    (7, 'A9630_1', '다빈치로봇 특정수술비', ...);
```

### KB alias 추가 (5건)
```sql
INSERT INTO coverage_alias (insurer_id, coverage_code, raw_name, raw_name_norm, source_doc_type)
VALUES
    (5, 'A9630_1', '다빈치로봇 암수술비(갑상선암 및 전립선암 제외)', ...),
    (5, 'A9630_1', '다빈치로봇 암수술비(갑상선암 및 전립선암 제외)(최초1회한)', ...),
    (5, 'A9630_1', '다빈치로봇 암수술비(최초1회한)', ...),
    (5, 'A9630_1', '다빈치로봇 암수술비', ...),
    (5, 'A9630_1', '다빈치로봇암수술비', ...);
```

### SAMSUNG alias 추가 (5건)
```sql
INSERT INTO coverage_alias (insurer_id, coverage_code, raw_name, raw_name_norm, source_doc_type)
VALUES
    (1, 'A9630_1', '다빈치로봇 수술비(1년감액)', ...),
    (1, 'A9630_1', '다빈치로봇 수술비(1년 감액)', ...),
    (1, 'A9630_1', '다빈치로봇 수술비', ...),
    (1, 'A9630_1', '암(특정암 제외) 다빈치로봇 수술비', ...),
    (1, 'A9630_1', '특정암 다빈치로봇 수술비', ...);
```

---

## 2차 검증 결과 (alias 보강 후)

| insurer_code | axis_strategy | alias_used | axis_len | result | doc_type_counts |
|--------------|---------------|------------|----------|--------|-----------------|
| DB | alias_text_match | true | 8 | ✅ GREEN | 가입설계서:4, 상품요약서:2, 사업방법서:2 |
| HANWHA | alias_text_match | true | 4 | ✅ GREEN | 사업방법서:3, 상품요약서:1 |
| HEUNGKUK | alias_text_match | true | 10 | ✅ GREEN | 가입설계서:6, 상품요약서:3, 사업방법서:1 |
| HYUNDAI | alias_text_match | true | 10 | ✅ GREEN | 가입설계서:4, 상품요약서:6 |
| KB | alias_text_match | true | 10 | ✅ GREEN | 가입설계서:6, 상품요약서:4 |
| LOTTE | alias_text_match | true | 4 | ✅ GREEN | 가입설계서:4 |
| MERITZ | alias_text_match | true | 10 | ✅ GREEN | 가입설계서:2, 상품요약서:3, 사업방법서:5 |
| SAMSUNG | alias_text_match | true | 10 | ✅ GREEN | 가입설계서:5, 상품요약서:5 |

---

## DoD 체크리스트

- [x] 모든 insurer_code에 대해 GREEN / YELLOW / RED 분류 완료
- [x] RED 케이스 3건(HEUNGKUK, KB, SAMSUNG) alias 보강
- [x] 보강 후 전체 GREEN 확인
- [x] audit 문서 생성
- [x] coverage_locked == true 확인
- [x] locked_coverage_codes == ["A9630_1"] 확인
- [x] len(compare_axis) >= 1 확인
- [x] __amount_fallback__ 노출 없음 확인

---

## 결론

### 최종 상태
- **8개 보험사 전체 GREEN**
- alias_text_match 전략으로 모든 보험사에서 axis 생성 성공

### 주요 발견
1. chunk.meta.entities.coverage_code 태깅은 0건 → ingestion 개선 필요 (STEP 5)
2. 현재는 coverage_alias.raw_name 기반 ILIKE 매칭으로 동작
3. alias 표현이 너무 구체적(suffix/prefix 포함)이면 매칭 실패
4. 간결한 alias 추가로 매칭률 향상

### 다음 단계
- STEP 5: Chunk coverage_code 태깅 (ingestion 개선)
- 추가 담보에 대한 alias 확장 검토

---

## 변경 사항

| 항목 | 내용 |
|------|------|
| DB coverage_alias | HEUNGKUK +5건, KB +5건, SAMSUNG +5건 |
| 총 A9630_1 alias | 34건 (기존 19건 + 추가 15건) |

---

## 커밋

```
feat: STEP 4.10-γ 전 보험사 Coverage Alias 전수 검증 및 보강
```
