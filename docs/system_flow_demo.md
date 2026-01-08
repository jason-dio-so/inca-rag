# 보험 약관 비교 RAG 시스템 - 질의 처리 흐름 문서

## 데모 시나리오
> **질의**: "삼성생명의 경계성종양 암진단시 담보가 얼마야"

---

## 1. 시스템 개요

### 1.1 기술 스택
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL + pgvector
- **검색 방식**: Vector Search + Metadata Filter 병행
- **LLM**: OpenAI (선택적 사용)

### 1.2 핵심 모듈 구성

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Layer                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  api/compare.py - POST /compare 엔드포인트                    │   │
│  │  • CompareRequest 파싱                                        │   │
│  │  • Insurer Scope Resolver                                     │   │
│  │  • Intent Detection (lookup/compare)                          │   │
│  │  • Coverage Resolution State 평가                             │   │
│  │  • Subtype Intent Detection                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Service Layer                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  services/retrieval/compare_service.py                        │   │
│  │  • Query Normalization                                        │   │
│  │  • Coverage Code Recommendation (pg_trgm)                     │   │
│  │  • 2-Phase Retrieval (Compare Axis + Policy Axis)             │   │
│  │  • Plan Selection                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  services/extraction/slot_extractor.py                        │   │
│  │  • Slot 추출 (금액, 존재여부, 조건 등)                         │   │
│  │  • Subtype 슬롯 (경계성종양/제자리암 보장여부)                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  services/extraction/amount_extractor.py                      │   │
│  │  • 진단비 일시금 추출                                         │   │
│  │  • 수술비 금액 추출                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Database Layer                                  │
│  ┌───────────────────┐  ┌───────────────────┐                       │
│  │  coverage_alias   │  │  coverage_standard│                       │
│  │  (담보명→코드)     │  │  (신정원 표준)     │                       │
│  └───────────────────┘  └───────────────────┘                       │
│  ┌───────────────────┐  ┌───────────────────┐                       │
│  │  chunk            │  │  document         │                       │
│  │  (검색 단위)       │  │  (문서 메타)       │                       │
│  └───────────────────┘  └───────────────────┘                       │
│  ┌───────────────────┐  ┌───────────────────┐                       │
│  │  insurer          │  │  product_plan     │                       │
│  │  (보험사)          │  │  (플랜)           │                       │
│  └───────────────────┘  └───────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 처리 흐름 상세

### 2.1 Phase 1: API 요청 처리 (`api/compare.py:1572-1821`)

#### 2.1.1 요청 수신
```python
POST /compare
{
    "query": "삼성생명의 경계성종양 암진단시 담보가 얼마야",
    "insurers": ["SAMSUNG"]  # 또는 빈 배열 (자동 추출)
}
```

#### 2.1.2 Insurer Scope Resolution (`api/compare.py:914-985`)
**함수**: `_resolve_insurer_scope()`

| 단계 | 처리 내용 | 관련 설정 파일 |
|------|----------|---------------|
| 1 | 질의에서 보험사명 추출 | `config/mappings/insurer_alias.yaml` |
| 2 | "삼성생명" → "SAMSUNG" 변환 | - |
| 3 | Request insurers와 병합 | - |
| 4 | 빈 경우 기본값 적용 | `config/rules/insurer_scope.yaml` |

**사용 테이블**: 없음 (설정 파일 기반)

**결과**:
```python
final_insurers = ["SAMSUNG"]
insurer_scope_debug = {
    "insurer_scope_method": "query_single_explicit",
    "query_extracted_insurers": ["SAMSUNG"]
}
```

#### 2.1.3 Intent Detection (`api/compare.py:847-912`)
**함수**: `_resolve_intent()`

| 단계 | 처리 내용 | 관련 설정 파일 |
|------|----------|---------------|
| 1 | 비교 키워드 탐지 ("비교", "vs") | `config/rules/intent_keywords.yaml` |
| 2 | lookup 강제 키워드 확인 | - |
| 3 | Anchor 기반 intent 유지 | - |

**결과**:
```python
resolved_intent = "lookup"  # 단일 보험사 조회
```

#### 2.1.4 Subtype Intent Detection (`api/compare.py:505-551`)
**함수**: `_detect_subtype_intent()`

| 단계 | 처리 내용 | 관련 설정 파일 |
|------|----------|---------------|
| 1 | "경계성종양" 키워드 탐지 | `config/rules/subtype_config.yaml` |
| 2 | subtype_targets 결정 | - |
| 3 | comparison_mode 결정 | - |

**결과**:
```python
is_subtype_intent = True
detected_subtype_targets = ["borderline"]
comparison_mode = "SUBTYPE"
```

---

### 2.2 Phase 2: Compare Service 호출 (`services/retrieval/compare_service.py:1805-2153`)

#### 2.2.1 Query Normalization (`compare_service.py:195-238`)
**함수**: `normalize_query_for_coverage()`

| 단계 | 원본 | 결과 |
|------|------|------|
| 1 | "삼성생명의 경계성종양 암진단시 담보가 얼마야" | - |
| 2 | 보험사명 제거 | "경계성종양 암진단시 담보가 얼마야" |
| 3 | 조사 제거 | "경계성종양암진단시담보얼마" |
| 4 | 의도 표현 제거 | "경계성종양암진단" |
| 5 | 공백 제거 | "경계성종양암진단" |

**사용 설정 파일**: `config/rules/query_normalization.yaml`

#### 2.2.2 Coverage Code Recommendation (`compare_service.py:257-359`)
**함수**: `recommend_coverage_codes()`

**사용 테이블**:
- `coverage_alias`: 보험사별 담보명 → 표준코드 매핑
- `coverage_standard`: 신정원 표준 담보 정보
- `insurer`: 보험사 정보

**SQL 쿼리 핵심**:
```sql
WITH ranked AS (
    SELECT
        ca.coverage_code,
        cs.coverage_name,
        ca.raw_name,
        similarity(ca.raw_name_norm, '경계성종양암진단') AS sim,
        ca.confidence,
        similarity(...) * COALESCE(ca.confidence, 0.8) AS combined_score
    FROM coverage_alias ca
    JOIN insurer i ON ca.insurer_id = i.insurer_id
    LEFT JOIN coverage_standard cs ON cs.coverage_code = ca.coverage_code
    WHERE i.insurer_code = 'SAMSUNG'
      AND similarity(ca.raw_name_norm, '경계성종양암진단') >= 0.1
)
SELECT ... ORDER BY combined_score DESC LIMIT 3
```

**핵심**: `pg_trgm` extension의 `similarity()` 함수 사용

**결과 예시**:
```python
recommended_coverage_codes = ["A4200_1", "A4210"]
recommendations = [
    {
        "coverage_code": "A4200_1",
        "coverage_name": "암진단비(유사암제외)",
        "raw_name": "암진단비(유사암제외)",
        "similarity": 0.45,
        "confidence": 0.9
    }
]
```

#### 2.2.3 Coverage Resolution State 평가 (`api/compare.py:664-845`)
**함수**: `_evaluate_coverage_resolution()`

| 조건 | 상태 | 설명 |
|------|------|------|
| candidates == 0 | INVALID | 매핑 불가, 재입력 필요 |
| candidates >= 1 && similarity >= 0.5 | RESOLVED | 확정됨 |
| candidates >= 1 && gap >= 0.15 | RESOLVED | 1위 압도적 |
| candidates >= 1 but not confident | UNRESOLVED | 선택 필요 |
| subtype-only 질의 | UNRESOLVED | 상위 담보 필요 |

**경계성종양 단독 질의의 경우**:
- "경계성종양"만으로는 coverage_code를 확정할 수 없음
- 상태: `UNRESOLVED`
- 메시지: "담보를 인식하지 못했습니다. 비교를 위해서는 상위 담보(예: 암진단비)를 함께 입력해 주세요."

**사용 설정 파일**: `config/rules/coverage_resolution.yaml`

---

### 2.3 Phase 3: 2-Phase Retrieval

#### 2.3.1 Compare Axis 검색 (`compare_service.py:908-1089`)
**함수**: `get_compare_axis()`

**목적**: 가입설계서/상품요약서/사업방법서에서 coverage_code 기반 근거 수집

**사용 테이블**:
- `chunk`: 문서 청크 (검색 단위)
- `coverage_alias`: 담보명 매칭용
- `insurer`: 보험사 필터

**SQL 쿼리 핵심**:
```sql
WITH alias_patterns AS (
    -- 해당 coverage_codes에 대한 alias raw_name 조회
    SELECT DISTINCT ca.coverage_code, cs.coverage_name, ca.raw_name, ca.raw_name_norm
    FROM coverage_alias ca
    JOIN insurer i ON ca.insurer_id = i.insurer_id
    LEFT JOIN coverage_standard cs ON cs.coverage_code = ca.coverage_code
    WHERE i.insurer_code = 'SAMSUNG'
      AND ca.coverage_code = ANY(['A4200_1', 'A4210'])
),
matched_chunks AS (
    -- alias raw_name을 포함하는 chunk 검색
    SELECT c.chunk_id, c.document_id, c.doc_type, c.page_start,
           LEFT(c.content, 1000) AS preview, ap.coverage_code
    FROM chunk c
    JOIN insurer i ON c.insurer_id = i.insurer_id
    CROSS JOIN alias_patterns ap
    WHERE i.insurer_code = 'SAMSUNG'
      AND c.doc_type = ANY(['가입설계서', '상품요약서', '사업방법서'])
      -- U-5.0-A: 공백 무시 매칭
      AND REGEXP_REPLACE(LOWER(c.content), '[[:space:]]', '', 'g')
          LIKE CONCAT('%', ap.raw_name_norm, '%')
)
SELECT ... ORDER BY doc_priority DESC, chunk_id LIMIT 10
```

**doc_type 우선순위**: 가입설계서(3) > 상품요약서(2) > 사업방법서(1)

#### 2.3.2 Policy Axis 검색 (`compare_service.py:1091-1166`)
**함수**: `get_policy_axis()`

**목적**: 약관에서 키워드 기반 조문 근거 수집 (A2 정책)

**사용 테이블**:
- `chunk`: 약관 청크
- `insurer`: 보험사 필터

**SQL 쿼리 핵심**:
```sql
SELECT c.chunk_id, c.document_id, c.doc_type, c.page_start,
       LEFT(c.content, 150) AS preview
FROM chunk c
JOIN insurer i ON c.insurer_id = i.insurer_id
WHERE i.insurer_code = 'SAMSUNG'
  AND c.doc_type = ANY(['약관'])
  AND c.content ILIKE '%경계성%'
ORDER BY c.page_start
LIMIT 10
```

**Policy Keywords 자동 추출** (`compare_service.py:362-400`):
```python
# "경계성종양" → "경계성" 으로 정규화
POLICY_KEYWORD_PATTERNS = {
    "경계성종양": "경계성",
    "경계성": "경계성",
    ...
}
```

#### 2.3.3 2-Pass Amount Retrieval (`compare_service.py:757-906`)
**함수**: `get_amount_bearing_evidence()`

**목적**: 1차 검색에서 금액을 못 찾은 경우 fallback

**SQL 쿼리 핵심**:
```sql
SELECT c.chunk_id, c.document_id, c.doc_type, c.page_start,
       LEFT(c.content, 1000) AS preview
FROM chunk c
JOIN insurer i ON c.insurer_id = i.insurer_id
WHERE i.insurer_code = 'SAMSUNG'
  AND c.doc_type = ANY(['가입설계서', '상품요약서', '사업방법서'])
  AND (c.content ILIKE '%진단비%' OR c.content ILIKE '%진단확정%' ...)
  AND c.content ~ '[0-9][0-9,]*\s*만\s*원'  -- 금액 패턴
ORDER BY doc_type_priority, page_start
LIMIT 3
```

---

### 2.4 Phase 4: Slot 추출 (`services/extraction/slot_extractor.py:834-878`)

#### 2.4.1 Coverage Type 결정
**함수**: `_determine_coverage_type()`

| coverage_code | coverage_type |
|---------------|---------------|
| A4200_1, A4210, A4209 | cancer_diagnosis |
| A4101, A4102, A4103 | cerebro_cardiovascular_diagnosis |
| A5100, A5200, A9630_1 | surgery_benefit |

**사용 설정 파일**: `config/mappings/coverage_code_groups.yaml`

#### 2.4.2 암진단비 슬롯 추출 (`slot_extractor.py:880-1027`)
**함수**: `_extract_cancer_diagnosis_slots()`

**추출 슬롯 목록**:

| slot_key | label | comparable | 추출기 |
|----------|-------|------------|--------|
| payout_amount | 진단비 지급금액(일시금) | True | `extract_diagnosis_lump_sum_slot()` |
| existence_status | 담보 존재 여부 | True | `extract_existence_status()` |
| payout_condition_summary | 지급조건 요약 | True | `extract_payout_condition_summary()` |
| diagnosis_scope_definition | 진단 범위 정의 | False | `extract_diagnosis_scope()` |
| waiting_period | 대기기간 | False | `extract_waiting_period()` |

#### 2.4.3 Subtype 슬롯 추출 (경계성종양 질의 시)
**조건**: 질의에 "제자리암", "경계성종양", "유사암" 키워드 포함

**추가 추출 슬롯**:

| slot_key | label | 추출기 |
|----------|-------|--------|
| subtype_in_situ_covered | 제자리암 보장 여부 | `extract_subtype_coverage_slot(subtype="in_situ")` |
| subtype_borderline_covered | 경계성종양 보장 여부 | `extract_subtype_coverage_slot(subtype="borderline")` |
| subtype_similar_cancer_covered | 유사암 보장 여부 | `extract_subtype_coverage_slot(subtype="similar_cancer")` |
| subtype_definition_excerpt | 암 유형 정의/조건 발췌 | `extract_subtype_definition_slot()` |
| partial_payment_rule | 감액/지급률 규정 | `extract_partial_payment_slot()` |

#### 2.4.4 금액 추출 로직 (`services/extraction/amount_extractor.py`)
**함수**: `extract_diagnosis_lump_sum()`

**금액 패턴**:
```python
AMOUNT_PATTERNS = [
    r'(\d[\d,]*)\s*만\s*원',      # "1,000만원"
    r'(\d[\d,]*)\s*천\s*만\s*원',  # "1천만원"
    r'(\d[\d,]*)\s*백\s*만\s*원',  # "5백만원"
]
```

**doc_type별 우선순위**:
```python
DOC_TYPE_PRIORITY = {
    "상품요약서": 3,
    "사업방법서": 2,
    "가입설계서": 1,
}
```

---

### 2.5 Phase 5: 응답 생성 (`api/compare.py:1335-1569`)

#### 2.5.1 대표 담보 선택 (`api/compare.py:1058-1206`)
**함수**: `_select_primary_coverage()`

**로직**:
1. Query Domain 판별 (CANCER, CARDIO, SURGERY 등)
2. Domain 기반 필터링
3. 메인 담보 우선 선택 (MAIN vs DERIVED)
4. 우선순위 점수 기반 정렬

**사용 설정 파일**:
- `config/coverage_domain.yaml`: coverage_code → domain
- `config/coverage_role.yaml`: coverage_code → MAIN/DERIVED

#### 2.5.2 사용자 요약 생성 (`api/compare.py:1208-1295`)
**함수**: `_generate_user_summary()`

**출력 예시**:
```
삼성의 암진단비(유사암제외) 정보를 조회했습니다.
해당 보험사에서 해당 담보를 보장합니다.
지급금액: 삼성 1,000만원
자세한 비교 내용은 오른쪽 패널을 확인해주세요.
```

#### 2.5.3 최종 응답 구조

```json
{
  "resolution_state": "RESOLVED",  // or "UNRESOLVED"
  "resolved_coverage_code": "A4200_1",
  "comparison_mode": "SUBTYPE",
  "subtype_targets": ["borderline"],

  "compare_axis": [...],
  "policy_axis": [...],
  "coverage_compare_result": [...],
  "slots": [
    {
      "slot_key": "payout_amount",
      "label": "진단비 지급금액(일시금)",
      "comparable": true,
      "insurers": [
        {
          "insurer_code": "SAMSUNG",
          "value": "1,000만원",
          "confidence": "high",
          "source_level": "COMPARABLE_DOC"
        }
      ]
    },
    {
      "slot_key": "subtype_borderline_covered",
      "label": "경계성종양 보장 여부",
      "comparable": true,
      "insurers": [
        {
          "insurer_code": "SAMSUNG",
          "value": "Y",
          "confidence": "high"
        }
      ]
    }
  ],

  "primary_coverage_code": "A4200_1",
  "primary_coverage_name": "암진단비(유사암제외)",
  "user_summary": "삼성의 경계성종양 보장 여부 및 감액 기준을 비교했습니다...",
  "anchor": {...},
  "debug": {...}
}
```

---

## 3. 데이터베이스 테이블 참조

### 3.1 핵심 테이블

| 테이블명 | 용도 | 주요 컬럼 |
|---------|------|----------|
| `insurer` | 보험사 정보 | insurer_id, insurer_code, insurer_name, ins_cd |
| `product` | 보험 상품 | product_id, insurer_id, product_name, product_version |
| `product_plan` | 상품 플랜 | plan_id, product_id, gender, age_min, age_max |
| `document` | 문서 메타 | document_id, insurer_id, doc_type, source_path, meta |
| `chunk` | 검색 청크 | chunk_id, document_id, content, embedding, page_start, meta |
| `coverage_standard` | 신정원 표준코드 | coverage_code, coverage_name, semantic_scope |
| `coverage_alias` | 담보명 매핑 | alias_id, insurer_id, coverage_code, raw_name, raw_name_norm, confidence |

### 3.2 주요 인덱스

| 인덱스명 | 테이블 | 용도 |
|---------|-------|------|
| `idx_chunk_content_trgm` | chunk | 키워드 검색 (pg_trgm) |
| `idx_chunk_embedding_hnsw` | chunk | 벡터 검색 (pgvector) |
| `idx_coverage_alias_raw_name_trgm` | coverage_alias | 담보명 유사 검색 |
| `idx_chunk_meta_coverage_code` | chunk | coverage_code 필터 |

### 3.3 주요 뷰

| 뷰명 | 용도 |
|-----|------|
| `coverage_name_map` | Coverage Resolution SSOT |
| `v_chunk_with_coverage` | 청크 + coverage_code 조회 |
| `v_easy_summary` | 쉬운요약서 문서 목록 |

---

## 4. 설정 파일 참조

### 4.1 매핑 설정 (`config/mappings/`)

| 파일명 | 용도 |
|-------|------|
| `insurer_alias.yaml` | 보험사명 → 코드 변환 |
| `coverage_code_groups.yaml` | coverage_code 그룹 정의 |
| `policy_keyword_patterns.yaml` | 약관 검색 키워드 |
| `slot_search_keywords.yaml` | 슬롯별 검색 키워드 |

### 4.2 규칙 설정 (`config/rules/`)

| 파일명 | 용도 |
|-------|------|
| `coverage_resolution.yaml` | 담보 해석 규칙 |
| `query_normalization.yaml` | 질의 정규화 규칙 |
| `intent_keywords.yaml` | 의도 감지 키워드 |
| `subtype_config.yaml` | Subtype 설정 |
| `doc_type_priority.yaml` | 문서 우선순위 |

---

## 5. 에러 케이스 및 대응

### 5.1 Resolution State별 처리

| 상태 | 조건 | 응답 | UI 동작 |
|-----|------|-----|---------|
| `RESOLVED` | similarity >= 0.5 또는 gap >= 0.15 | 전체 데이터 반환 | 비교표 표시 |
| `UNRESOLVED` | 후보 있으나 확정 불가 | suggested_coverages 반환 | 선택 UI 표시 |
| `INVALID` | 후보 없음 | 재입력 메시지 | 입력창 하이라이트 |

### 5.2 Subtype-only 질의 처리
**질의**: "경계성종양 비교해줘" (상위 담보 없음)

**처리**:
1. `is_multi_subtype_query()` = True
2. `resolution_state` = `UNRESOLVED`
3. 메시지: "담보를 인식하지 못했습니다. 비교를 위해서는 상위 담보(예: 암진단비)를 함께 입력해 주세요."
4. `suggested_coverages` = [A4200_1 암진단비, A4210 유사암진단비, ...]

---

## 6. 성능 최적화 포인트

### 6.1 인덱스 활용
- `pg_trgm` GIN 인덱스: ILIKE 검색 가속
- `pgvector` HNSW 인덱스: 벡터 검색 가속
- 복합 인덱스: `(insurer_id, doc_type)` 조합 필터

### 6.2 캐싱
- 설정 파일 모듈 로드 시 캐싱 (`_INSURER_ALIASES`, `_NORMALIZATION_RULES`)
- `comparison_slot_cache` 테이블 (선택적)

### 6.3 쿼리 최적화
- 보험사별 쿼리 분리 (쏠림 방지)
- 2-pass retrieval (금액 fallback)
- `LIMIT` 적용으로 불필요한 스캔 방지

---

## 7. 디버그 정보

API 응답의 `debug` 필드에서 확인 가능한 정보:

```json
{
  "debug": {
    "query": "삼성생명의 경계성종양 암진단시 담보가 얼마야",
    "insurers": ["SAMSUNG"],
    "resolved_policy_keywords": ["경계성"],
    "timing_ms": {
      "coverage_recommendation": 45.2,
      "compare_axis": 120.5,
      "policy_axis": 35.8,
      "amount_retrieval_2pass": 25.3,
      "slots": 15.1
    },
    "insurer_scope": {
      "insurer_scope_method": "query_single_explicit",
      "query_extracted_insurers": ["SAMSUNG"]
    },
    "coverage_resolution": {
      "status": "RESOLVED",
      "best_similarity": 0.52,
      "best_code": "A4200_1",
      "reason": "single_candidate_confident"
    },
    "slot_type_for_retrieval": "cancer_diagnosis",
    "slots_count": 10
  }
}
```

---

## 8. 관련 문서

- `CLAUDE.md`: 프로젝트 헌법 (필수 준수 원칙)
- `status.md`: 현재 시스템 상태
- `db/schema.sql`: 전체 DB 스키마
- `config/`: 모든 설정 파일

---

*문서 생성일: 2025-12-23*
*시스템 버전: recovery/step-3.7-delta-beta*
