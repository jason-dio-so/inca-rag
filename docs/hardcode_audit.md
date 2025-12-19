# STEP 2.8 하드코딩/임시 딕셔너리 자산화 정리

## 개요

본 문서는 codebase 내 하드코딩된 비즈니스 규칙을 분류하고 외부화 계획을 정리합니다.

## 분류 기준

| 등급 | 정의 | 조치 |
|------|------|------|
| **P0** | 비즈니스 규칙 / 도메인 지식 | 즉시 YAML 외부화 |
| **P1** | 품질 영향 키워드/패턴 | 권장 외부화 |
| **P2** | 알고리즘/정규식 | 코드 유지 가능 |

---

## P0 항목 (즉시 외부화)

### 1. INSURER_ALIASES
- **위치**: `api/compare.py:252-294`
- **용도**: 한글 보험사명/약칭 → insurer code 매핑
- **대상 파일**: `config/mappings/insurer_alias.yaml`
- **항목 수**: 35개

### 2. COMPARE_PATTERNS
- **위치**: `api/compare.py:297-307`
- **용도**: 비교 의도 표현 패턴
- **대상 파일**: `config/rules/compare_patterns.yaml`
- **항목 수**: 8개

### 3. POLICY_KEYWORD_PATTERNS
- **위치**: `services/retrieval/compare_service.py:44-70`
- **용도**: 질의 정규화 (예: "상피내암" → "제자리암")
- **대상 파일**: `config/mappings/policy_keyword_patterns.yaml`
- **항목 수**: 18개

### 4. DOC_TYPE_PRIORITY
- **위치**: `services/retrieval/compare_service.py:80-84`
- **용도**: source_doc_type 우선순위 가중치
- **대상 파일**: `config/rules/doc_type_priority.yaml`
- **항목 수**: 3개

### 5. SLOT_SEARCH_KEYWORDS
- **위치**: `services/retrieval/compare_service.py:498-563`
- **용도**: 슬롯별 2-pass retrieval 검색 키워드
- **대상 파일**: `config/mappings/slot_search_keywords.yaml`
- **항목 수**: 8개 카테고리

### 6. COVERAGE_CODE_GROUPS (3개)
- **위치**: `services/retrieval/compare_service.py:572-574`
- **항목**:
  - `CANCER_COVERAGE_CODES`: A4200_1, A4210, A4209, A4299_1
  - `CEREBRO_CARDIOVASCULAR_CODES`: A4101, A4102, A4103, A4104_1, A4105
  - `SURGERY_COVERAGE_CODES`: A5100, A5104_1, A5107_1, A5200, A5298_001, A5300, A9630_1
- **대상 파일**: `config/mappings/coverage_code_groups.yaml`

### 7. COVERAGE_CODE_TO_TYPE
- **위치**: `services/extraction/slot_extractor.py:174-193`
- **용도**: coverage_code → coverage_type 매핑
- **대상 파일**: `config/mappings/coverage_code_to_type.yaml`
- **항목 수**: 13개

---

## P1 항목 (권장 외부화)

### 1. 금액 추출 키워드 그룹
- **위치**: `services/extraction/amount_extractor.py`
- **항목**:
  - `POSITIVE_KEYWORDS` (lines 39-50): 12개
  - `NEGATIVE_KEYWORDS` (lines 53-64): 10개
  - `LUMP_SUM_KEYWORDS` (lines 72-82): 10개
  - `SURGERY_POSITIVE_KEYWORDS` (lines 88-97): 8개
  - `SURGERY_NEGATIVE_KEYWORDS` (lines 99-107): 7개
  - `DAILY_ANCILLARY_KEYWORDS` (lines 121-130): 9개
- **대상 파일**: `config/mappings/amount_keywords.yaml`

### 2. 테이블 헤더 토큰
- **위치**: `services/extraction/amount_extractor.py`
- **항목**:
  - `PREMIUM_HEADER_TOKENS` (lines 142-151): 7개
  - `COVERAGE_HEADER_TOKENS` (lines 154-164): 9개
- **대상 파일**: `config/mappings/table_header_tokens.yaml`

### 3. 뇌/심혈관/수술 기본 키워드
- **위치**: `services/retrieval/compare_service.py:76-77`
- **항목**:
  - `CEREBRO_CARDIOVASCULAR_KEYWORDS`: 4개
  - `SURGERY_BENEFIT_KEYWORDS`: 3개
- **대상 파일**: `config/mappings/slot_search_keywords.yaml` (통합)

---

## P2 항목 (코드 유지)

### 1. 성별/나이 정규식 패턴
- **위치**: `services/ingestion/plan_detector.py:41-93`
- **항목**:
  - `MALE_PATTERNS`: 10개 정규식
  - `FEMALE_PATTERNS`: 10개 정규식
  - `AGE_PATTERNS`: 7개 (pattern, lambda) 튜플
- **사유**: lambda 함수 포함으로 YAML 외부화 어려움

### 2. 단위 환산 배수
- **위치**: `services/extraction/amount_extractor.py:167-174`
- **항목**: `UNIT_MULTIPLIERS` (7개)
- **사유**: 불변 상수, 수정 가능성 낮음

### 3. 수술 횟수 제한 패턴
- **위치**: `services/extraction/amount_extractor.py:110-117`
- **항목**: `SURGERY_COUNT_PATTERNS` (6개 정규식)
- **사유**: 정규식 기반, 수정 가능성 낮음

### 4. 일시금 문맥 패턴
- **위치**: `services/extraction/amount_extractor.py:133-138`
- **항목**: `LUMP_SUM_CONTEXT_PATTERNS` (4개)
- **사유**: 정규식 기반, 간단한 패턴

---

## 이미 외부화 완료 (STEP 2.7-α)

| 항목 | 파일 |
|------|------|
| COVERAGE_DOMAINS | `config/coverage_domain.yaml` |
| DOMAIN_PRIORITY | `config/domain_priority.yaml` |
| COVERAGE_ROLES | `config/coverage_role.yaml` |
| DOMAIN_KEYWORDS | `config/domain_keywords.yaml` |
| DERIVED_KEYWORDS | `config/derived_keywords.yaml` |
| DISPLAY_NAMES | `config/display_names.yaml` |

---

## 외부화 계획 요약

### Phase 1: P0 항목 (필수)
1. `config/mappings/insurer_alias.yaml`
2. `config/rules/compare_patterns.yaml`
3. `config/mappings/policy_keyword_patterns.yaml`
4. `config/rules/doc_type_priority.yaml`
5. `config/mappings/slot_search_keywords.yaml`
6. `config/mappings/coverage_code_groups.yaml`
7. `config/mappings/coverage_code_to_type.yaml`

### Phase 2: P1 항목 (권장)
1. `config/mappings/amount_keywords.yaml`
2. `config/mappings/table_header_tokens.yaml`

---

## 작업 체크리스트

- [x] 전수 조사 완료
- [x] P0/P1/P2 분류 완료
- [x] P0 YAML 파일 생성
- [x] config_loader.py 확장
- [x] 기존 코드에서 import 교체
- [x] 테스트 통과 확인 (47 passed)
- [x] status.md 업데이트

## 생성된 파일 목록

### Config Files (신규)
- `config/mappings/insurer_alias.yaml` - 보험사 alias 매핑
- `config/mappings/policy_keyword_patterns.yaml` - 질의 정규화 패턴
- `config/mappings/slot_search_keywords.yaml` - 슬롯별 검색 키워드
- `config/mappings/coverage_code_groups.yaml` - coverage code 그룹
- `config/mappings/coverage_code_to_type.yaml` - code → type 매핑
- `config/rules/compare_patterns.yaml` - 비교 의도 패턴
- `config/rules/doc_type_priority.yaml` - 문서 유형 우선순위

### 수정된 파일
- `api/config_loader.py` - P0 로더 함수 추가
- `api/compare.py` - config loader 사용으로 전환
- `services/retrieval/compare_service.py` - config loader 사용으로 전환
- `services/extraction/slot_extractor.py` - config loader 사용으로 전환
