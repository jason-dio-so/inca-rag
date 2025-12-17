# 보험 약관 비교 RAG 시스템 - 진행 현황

> 최종 업데이트: 2025-12-17

---

## 📋 전체 진행 요약

| 단계 | 작업 내용 | 유형 | 상태 |
|------|----------|------|------|
| Step A | DB 스키마 적용 및 데이터 적재 | 구현 | ✅ 완료 |
| Step B | Retrieval/Compare 검증 | 분석/검토 | ✅ 완료 |
| Step C-1 | Coverage 코드 표준화 (ontology → 신정원) | 구현 | ✅ 완료 |
| 분석 | doc_type별 coverage 매칭 품질 분석 | 분석/검토 | ✅ 완료 |
| Step A-1 | 약관 전용 coverage 태깅 분리 | 구현 | ✅ 완료 |
| 검증 | A-1 적용 후 비교 질의 품질 검증 | 분석/검토 | ✅ 완료 |
| **Step D** | **전체 보험사 Ingestion + 품질 검증** | **구현** | ✅ 완료 |

---

## 🕐 시간순 상세 내역

### 1. Step A: DB 스키마 적용 및 데이터 적재 [구현]

**작업 내용:**
- PostgreSQL + pgvector DB 스키마 적용 (`db/schema.sql`)
- Docker 컨테이너 실행 (`docker-compose.yml`)
- 담보명 매핑 Excel → `coverage_alias` 테이블 적재
- SAMSUNG 보험사 문서 ingestion (5개 문서, 1,279개 chunks)

**생성된 파일:**
- `db/schema.sql` - DB 스키마
- `docker-compose.yml` - Docker 설정
- `services/ingestion/` - Ingestion 파이프라인 전체
- `tools/load_coverage_mapping.py` - 담보 매핑 로드 스크립트

**결과:**
| 지표 | 값 |
|------|-----|
| 적재된 문서 수 | 5 |
| 적재된 chunk 수 | 1,279 |
| coverage 매칭률 | 66.85% |
| 표준코드 수 | 28개 |
| 보험사 수 | 8개 |

---

### 2. Step B: Retrieval/Compare 검증 [분석/검토]

**작업 내용:**
- doc_type 필터링 SQL 검증
- 쉬운요약서 우선순위 정렬 검증
- coverage_code 기반 검색 검증
- doc_type별 비교 분석

**검증 결과:**
- doc_type 필터링 정상 작동
- 가입설계서 coverage 매칭률: 77.78%
- plan_id NULL 비율: 100% (공통 문서)

---

### 3. Step C-1: Coverage 코드 표준화 [구현]

**문제:**
- chunk에 ontology 코드(THYROID_CANCER, STROKE 등)가 저장되어 있음
- 신정원 표준코드(A4210, A4103 등)가 아니라 JOIN 실패

**해결:**
1. `coverage_standard.meta.ontology_codes`에 매핑 seed
2. `coverage_extractor.py`에 fallback remap 로직 추가
3. 기존 chunk 백필 스크립트 실행

**생성된 파일:**
- `tools/seed_ontology_codes.py` - ontology → 신정원 매핑 seed
- `tools/backfill_chunk_coverage_code.py` - 기존 chunk 백필

**매핑 정의:**
```python
ONTOLOGY_TO_STANDARD = {
    "CANCER_DIAG": "A4200_1",      # 암진단비
    "THYROID_CANCER": "A4210",     # 유사암진단비
    "CIS_CARCINOMA": "A4210",      # 제자리암
    "STROKE": "A4103",             # 뇌졸중진단비
    "ACUTE_MI": "A4105",           # 허혈성심장질환진단비
    "SURGERY": "A5100",            # 질병수술비
    "HOSPITALIZATION": "A6100_1",  # 질병입원비
    "DEATH_BENEFIT": "A1100",      # 질병사망
    "DISABILITY": "A3300_1",       # 상해후유장해
    # ... 17개 매핑
}
```

**결과:**
| 지표 | Before | After |
|------|--------|-------|
| coverage_name 있는 chunk | 0 | 855 (100%) |
| coverage_standard JOIN 성공률 | 0% | 100% |

---

### 4. doc_type별 coverage 매칭 품질 분석 [분석/검토]

**분석 결과:**
| doc_type | mapping | fallback_remap | 문제 |
|----------|---------|----------------|------|
| 약관 | 7.57% | **92.43%** | ⚠️ 오탐 다수 |
| 상품요약서 | 50.59% | 49.41% | - |
| 사업방법서 | 53.97% | 46.03% | - |
| 가입설계서 | 71.43% | 28.57% | - |

**원인 분류 (약관):**
| 원인 | 비중 |
|------|------|
| 담보명이 문장 안에 묻힘 | ~92% |
| alias 부족 | ~5% |
| 표/레이아웃 깨짐 | ~3% |

**결론:** 약관에서 "갑상선암", "수술비" 등 일반 단어가 정의/설명문에 등장하여 오탐 발생

---

### 5. Step A-1: 약관 전용 coverage 태깅 분리 [구현]

**목표:** 약관에서 오탐 방지를 위해 헤더/조문 패턴에서만 coverage 추출

**구현 내용:**
1. `coverage_extractor.py` doc_type별 정책 분기 추가
   - 약관: `_extract_from_clause_header()` (헤더 패턴만)
   - 그 외: 기존 로직 유지

2. 헤더 패턴 정규식:
   ```python
   # 제X조(담보명)
   r"제\s*\d+\s*조(?:의\s*\d+)?\s*\(([^)]+)\)"
   # [담보명]
   r"(?:^|\s)\[([^\]]{2,50})\]"
   # X-Y. 담보명 특별약관
   r"(?:^|\n)\s*\d+(?:-\d+)*\.\s*([^\n]{2,50}?(?:특별약관|특약))"
   ```

3. 새로운 필드 추가:
   - `tag_source`: 'clause_header' (약관 전용)
   - `confidence`: 'high' | 'medium' | 'low'

**생성된 파일:**
- `tools/backfill_terms_for_policy.py` - 약관 재태깅 스크립트

**결과:**
| 지표 | Before | After |
|------|--------|-------|
| 약관 coverage 있는 chunk | 700 (62.6%) | 497 (44.5%) |
| 오탐 제거 | - | 203건 (31%) |
| 약관 match_source | fallback_remap 92% | clause_header 89% |
| 약관 confidence | low | **high** |

---

### 6. A-1 적용 후 비교 질의 품질 검증 [분석/검토]

**검증 1: 핵심 키워드 조문 누락 여부**

| 키워드 | clause_header | mapping | no_match | 합계 |
|--------|---------------|---------|----------|------|
| 경계성 | 78 | 4 | 1 | 83 |
| 유사암 | 27 | 16 | 16 | 59 |
| 제자리암 | 6 | 0 | 11 | 17 |

- no_match 28건 중 17건(61%)은 ±5페이지 내 clause_header 존재
- **판정: ✅ 성공** - 검색 근거 충분

**검증 2: 비교 질의 doc_type 우선순위**

| doc_type | 검색 결과 건수 |
|----------|---------------|
| 가입설계서 | 7 |
| 상품요약서 | 32 |
| 사업방법서 | 9 |
| 약관 | 93 |

- 상위 50건: 가입설계서 → 상품요약서 → 사업방법서 → 약관 순
- **판정: ✅ 성공** - 우선순위 정상 유지

---

### 7. Step D: 전체 보험사 Ingestion + 품질 검증 [구현]

**작업 내용:**
- 8개 보험사 전체 ingestion 실행
- A-1 정책(약관 clause_header) 적용 확인
- 보험사별 품질 편차 분석

**보험사별 Ingestion 결과:**

| insurer_code | doc_count | chunk_count | 상태 |
|--------------|-----------|-------------|------|
| LOTTE | 8 | 2,038 | ✅ |
| MERITZ | 4 | 1,937 | ✅ |
| HYUNDAI | 4 | 1,343 | ✅ |
| SAMSUNG | 5 | 1,279 | ✅ |
| DB | 5 | 1,259 | ✅ |
| HANWHA | 4 | 1,114 | ✅ |
| KB | 4 | 1,003 | ✅ |
| HEUNGKUK | 4 | 977 | ✅ |
| **합계** | **38** | **10,950** | - |

**보험사 × doc_type 매칭률:**

| insurer_code | 가입설계서 | 상품요약서 | 사업방법서 | 약관 |
|--------------|------------|------------|------------|------|
| DB | 89.47% | 98.72% | 90.77% | 1.82% |
| HANWHA | 60.00% ⚠️ | 84.72% | 75.96% | 25.18% |
| HEUNGKUK | 84.62% | 97.50% | 91.30% | 42.03% |
| HYUNDAI | 77.78% | 93.41% | 84.21% | 12.94% |
| KB | 100.00% | 98.53% | 92.31% | 10.78% |
| LOTTE | 77.78% | 91.67% | 87.78% | 33.98% |
| MERITZ | 76.92% | 88.30% | 80.31% | 13.01% |
| SAMSUNG | 77.78% | 96.59% | 98.44% | 44.45% |

**coverage_standard JOIN 성공률:** 전 보험사 **100%**

**보험사별 판정:**

| insurer_code | 판정 | 비고 |
|--------------|------|------|
| DB | PASS | - |
| HANWHA | **FAIL** | 가입설계서 60% (기준 70% 미달) |
| HEUNGKUK | PASS | - |
| HYUNDAI | PASS | - |
| KB | PASS | - |
| LOTTE | PASS | - |
| MERITZ | PASS | - |
| SAMSUNG | PASS | - |

**API 구현 리스크:**

| # | 리스크 | 우선순위 |
|---|--------|----------|
| 1 | HANWHA 가입설계서 매칭률 60% → 비교조회 시 담보 누락 | 🔴 High |
| 2 | 약관 clause_header 비율 편차 (1.8%~44.5%) → 검색 품질 불균형 | 🟡 Medium |
| 3 | 보험사별 chunk 수 편차 (977~2,038) → quota 병합 시 쏠림 | 🟡 Medium |

---

## 📁 생성된 파일 목록

### 구현 파일
| 파일 | 설명 |
|------|------|
| `db/schema.sql` | PostgreSQL + pgvector 스키마 |
| `docker-compose.yml` | Docker 설정 |
| `requirements.txt` | Python 의존성 |
| `services/ingestion/coverage_extractor.py` | Coverage 추출기 (doc_type 정책 분리 포함) |
| `services/ingestion/coverage_ontology.py` | Ontology 정의 |
| `services/ingestion/normalize.py` | 텍스트 정규화 |
| `services/ingestion/chunker.py` | PDF → Chunk 분할 |
| `services/ingestion/pdf_loader.py` | PDF 로더 |
| `services/ingestion/db_writer.py` | DB 저장 |
| `services/ingestion/embedding.py` | 임베딩 생성 |
| `services/ingestion/ingest.py` | Ingestion 메인 |
| `tools/load_coverage_mapping.py` | Excel → coverage_alias 로드 |
| `tools/seed_ontology_codes.py` | Ontology → 신정원 매핑 seed |
| `tools/backfill_chunk_coverage_code.py` | Chunk coverage 백필 |
| `tools/backfill_terms_for_policy.py` | 약관 재태깅 백필 |

---

## 📊 현재 DB 상태

**전체 통계:**
| 지표 | 값 |
|------|-----|
| 보험사 수 | 8 |
| 문서 수 | 38 |
| Chunk 수 | 10,950 |
| Coverage 매칭 chunk | 3,535 (32.3%) |
| coverage_standard JOIN 성공률 | 100% |

**보험사별 chunk 수:**
| insurer_code | chunks |
|--------------|--------|
| LOTTE | 2,038 |
| MERITZ | 1,937 |
| HYUNDAI | 1,343 |
| SAMSUNG | 1,279 |
| DB | 1,259 |
| HANWHA | 1,114 |
| KB | 1,003 |
| HEUNGKUK | 977 |

---

## 🔜 다음 단계 (예정)

1. Retrieval API 구현 (FastAPI)
2. 비교조회 API 구현 (quota 기반 병합)
3. plan_selector 연동 (성별/나이 기반 plan 자동 선택)
4. HANWHA 가입설계서 alias 보강 (매칭률 개선)
