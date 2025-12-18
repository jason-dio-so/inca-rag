# policy_axis 성능 벤치마크 결과

> 측정일: 2025-12-17
> 목적: pg_trgm 인덱스 추가 전/후 policy_axis 응답 시간 비교

---

## 테스트 환경

- DB: PostgreSQL + pgvector (Docker)
- 데이터: 8개 보험사, 10,950 chunks
- 측정 방법: 각 케이스 5회 호출 후 평균/최대값 측정

---

## 인덱스 추가 내용

```sql
-- 전체 content에 대한 trigram 인덱스
CREATE INDEX idx_chunk_content_trgm
  ON chunk USING gin (content gin_trgm_ops);

-- 약관(doc_type='약관')에 대한 부분 인덱스
CREATE INDEX idx_chunk_content_trgm_policy
  ON chunk USING gin (content gin_trgm_ops)
  WHERE doc_type = '약관';

-- 복합 조건 검색을 위한 btree 인덱스
CREATE INDEX idx_chunk_insurer_doctype
  ON chunk (insurer_id, doc_type);
```

---

## 벤치마크 결과

### Case 1: SAMSUNG vs MERITZ / 경계성 종양 암진단비

| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| policy_axis avg | 501.83ms | 290.61ms | **-42.1%** |
| policy_axis max | 524.02ms | 300.97ms | **-42.6%** |
| total avg | 518.56ms | 305.80ms | **-41.0%** |

### Case 4: 8개사 전체 / 암진단비 (쏠림 방지)

| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| policy_axis avg | 1598.13ms | 1112.07ms | **-30.4%** |
| policy_axis max | 1627.32ms | 1138.90ms | **-30.0%** |
| total avg | 1619.25ms | 1132.79ms | **-30.0%** |

---

## EXPLAIN ANALYZE 결과

인덱스 적용 후 쿼리 플랜:

```
Bitmap Index Scan on idx_chunk_content_trgm_policy
  Index Cond: (content ~~* '%경계성%'::text)
  Execution Time: 35.964 ms
```

- **Before**: Seq Scan (전체 테이블 스캔)
- **After**: Bitmap Index Scan (인덱스 사용)

---

## 요약

| Case | Before (ms) | After (ms) | 개선율 |
|------|-------------|------------|--------|
| case1 | 501.83 | 290.61 | -42.1% |
| case4 | 1598.13 | 1112.07 | -30.4% |

---

## pytest 검증

```
35 passed in 13.49s
```

- 모든 테스트 PASS
- A2 정책 준수 확인
- 정답성 변경 없음

---

## 추가 개선 가능성

1. **pg_trgm.similarity_threshold 조정**: 기본값 0.3에서 조정 가능
2. **키워드 전처리**: 불용어 제거 후 검색
3. **Full-text Search 전환**: ILIKE 대신 tsvector/tsquery 사용
4. **캐싱**: 자주 검색되는 키워드 결과 캐싱
