# DB Gap Report - 2025-12-20

## 1. Migration Files 현황

| 파일 | 내용 |
|------|------|
| `db/migrations/20251217_add_trgm_indexes.sql` | pg_trgm 인덱스 3개 (chunk.content) |
| `db/migrations/20251218_add_comparison_slots.sql` | comparison_slot_cache 테이블 |

---

## 2. 현재 DB 적용 상태

### 2.1 pg_trgm Extension

```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';
```

| extname | extversion |
|---------|------------|
| pg_trgm | 1.6 |

**결과: 적용됨 (schema.sql에 이미 포함)**

---

### 2.2 trgm 인덱스 (chunk 테이블)

```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'chunk' AND indexname LIKE '%trgm%';
```

| indexname |
|-----------|
| (0 rows) |

**결과: 미적용 - migration 20251217 실행 안 됨**

---

### 2.3 insurer_doctype 복합 인덱스

```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'chunk' AND indexname LIKE '%insurer_doctype%';
```

| indexname |
|-----------|
| (0 rows) |

**결과: 미적용 - migration 20251217 실행 안 됨**

---

### 2.4 comparison_slot_cache 테이블

```sql
SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'comparison_slot_cache');
```

| table_exists |
|--------------|
| false |

**결과: 미적용 - migration 20251218 실행 안 됨**

---

## 3. GAP 요약

| 항목 | Migration 파일 | 현재 DB | GAP |
|------|---------------|---------|-----|
| pg_trgm extension | 20251217 | 적용됨 | - |
| idx_chunk_content_trgm | 20251217 | **미적용** | 누락 |
| idx_chunk_content_trgm_policy | 20251217 | **미적용** | 누락 |
| idx_chunk_insurer_doctype | 20251217 | **미적용** | 누락 |
| comparison_slot_cache 테이블 | 20251218 | **미적용** | 누락 |
| idx_slot_cache_insurer_coverage | 20251218 | **미적용** | 누락 |
| idx_slot_cache_slot_key | 20251218 | **미적용** | 누락 |

---

## 4. 조치 필요 사항

1. **schema.sql 현행화**: 위 누락 항목을 schema.sql에 squash
2. **Option A+ 스크립트**: coverage 재적재 + 검증 자동화
3. **재현성 검증**: DB 볼륨 재생성 시 자동 적용 확인

---

## 5. 검증 일시

- 검증 시각: 2025-12-20
- DB 컨테이너: inca_demo_db
- 검증자: Claude Code (STEP 4.2)
