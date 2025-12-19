# 보험 약관 비교 RAG 시스템 - 진행 현황

> 최종 업데이트: 2025-12-20 (STEP 3.7-δ Complete)

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
| Step D | 전체 보험사 Ingestion + 품질 검증 | 구현 | ✅ 완료 |
| Step D-1 | HANWHA 가입설계서 분석 (담보 chunk 기준 재검토) | 분석/검토 | ✅ 완료 |
| Step E | /compare MVP 구현 (2-Phase Retrieval) | 구현 | ✅ 완료 |
| Step E-1 | /compare 정답성 검증 (5개 고정 시나리오) | 검증 | ✅ 완료 |
| Step E-2 | /compare 회귀 테스트 pytest 자동화 | 검증 | ✅ 완료 |
| Step E-3 | policy_axis 성능 개선 (pg_trgm 인덱스) | 최적화 | ✅ 완료 |
| Step E-4 | policy_keywords 자동 추출 (규칙 기반) | 기능 | ✅ 완료 |
| Step E-5 | coverage_codes 자동 추천 (coverage_alias 기반) | 기능 | ✅ 완료 |
| Step F | coverage_compare_result(비교표) 생성 | 기능 | ✅ 완료 |
| Step G-1 | diff_summary(차이점 요약) 규칙 엔진 | 기능 | ✅ 완료 |
| Step H-1 | amount/condition_snippet 규칙 기반 추출 | 기능 | ✅ 완료 |
| Step H-1.5 | amount/condition 추출 품질 리포트 | 분석/검토 | ✅ 완료 |
| Step H-1.6 | amount_extractor 오탐 제거 (보험료 vs 보험금 분리) | 기능 | ✅ 완료 |
| Step H-1.7 | amount_extractor premium_block 휴리스틱 (표 구조) | 기능 | ✅ 완료 |
| Step H-1.8 | Amount source policy (가입설계서 amount 신뢰도 제한) | 기능 | ✅ 완료 |
| **Step H-2** | **LLM 정밀 추출 (선별 적용)** | **기능** | ✅ 완료 |
| **Step H-2.1** | **Real LLM Provider 연결 + 운영 가드레일** | **기능** | ✅ 완료 |
| **Step I** | **Plan 자동 선택 (plan_selector) + plan_id 기반 retrieval** | **기능** | ✅ 완료 |
| **Step I-1** | **Ingestion plan_id 자동 태깅 (plan_detector)** | **기능** | ✅ 완료 |
| **Step J-1** | **Plan 태깅 품질 리포트 + /compare 플랜 회귀 테스트** | **검증** | ✅ 완료 |
| **Step J-2** | **manifest.csv 기반 plan 태깅 + backfill** | **기능** | ✅ 완료 |
| **Step J-3** | **DB 미태깅 원인 분류 + LOTTE 플랜 E2E 검증** | **검증** | ✅ 완료 |
| **Step K** | **Vector Retrieval 품질 고정 + 파라미터 튜닝 + Hybrid 옵션** | **검증/기능** | ✅ 완료 |
| **Step U-ChatUI** | **Next.js 채팅 UI (Compare 비교표)** | **UI** | ✅ 완료 |
| **Step U-1** | **A2 정책 신뢰 (약관 제외 안내 UI)** | **UI** | ✅ 완료 |
| **Step U-2** | **Evidence PDF Page Viewer (원문 보기)** | **UI/API** | ✅ 완료 |
| **Step U-2.5** | **Evidence 하이라이트 + Deep-link** | **UI/API** | ✅ 완료 |
| **Step U-4** | **Docker Compose 데모 배포 패키징** | **DevOps** | ✅ 완료 |
| **Step U-4.1** | **데모 데이터 시딩 자동화 + /compare 스모크 활성화** | **DevOps** | ✅ 완료 |
| **Step U-4.2** | **데모 스모크를 "양쪽 근거"로 고정** | **DevOps** | ✅ 완료 |
| **Step U-4.3** | **데모 삼성/메리츠 전체 PDF 로딩 + 충분성 리포트** | **DevOps** | ✅ 완료 |
| **Step U-4.4** | **데모 스모크 2단 구성 (안정성/시나리오) + UI Debug 강화** | **DevOps/UI** | ✅ 완료 |
| **Step U-4.8** | **Comparison Slots v0.1 (암진단비 슬롯 기반 비교)** | **기능/UI** | ✅ 완료 |
| **Step U-4.9** | **Eval Framework 구축 (goldset + eval_runner)** | **검증** | ✅ 완료 |
| **Step U-4.10** | **Demo vs Main 변경사항 분류 문서화** | **문서** | ✅ 완료 |
| **Step U-4.11** | **Slot Generalization (coverage type 레지스트리)** | **기능** | ✅ 완료 |
| **Step U-4.12** | **Coverage Type 확장 + YAML 외부화** | **기능** | ✅ 완료 |
| **Step U-4.13** | **뇌/심혈관 + 수술비 슬롯 추출기 구현** | **기능** | ✅ 완료 |
| **Step U-4.14** | **대규모 보험사 온보딩 + 안정성 검증** | **기능/검증** | ✅ 완료 |
| **Step U-4.15** | **Cerebro 금액 추출 정밀도 향상** | **기능** | ✅ 완료 |
| **Step U-4.16** | **고난도 핵심 질의 대응 (다빈치수술비/경계성종양)** | **기능** | ✅ 완료 |
| **Step U-4.17** | **암 Subtype 비교 확장 (partial_payment + 약관 우선)** | **기능** | ✅ 완료 |
| **Step U-4.18** | **수술 조건(방식/병원급) 비교 확장** | **기능** | ✅ 완료 |
| **STEP 2.8** | **하드코딩 비즈니스 규칙 YAML 외부화** | **리팩토링** | ✅ 완료 |
| **STEP 2.9** | **Query Anchor / Context Locking** | **기능** | ✅ 완료 |
| **STEP 3.5** | **Advanced 옵션 Guard / Auto-Recovery** | **기능** | ✅ 완료 |
| **STEP 3.6** | **Intent Locking / Mode Separation** | **기능** | ✅ 완료 |
| **STEP 3.7** | **Coverage Resolution Failure Handling** | **기능** | ✅ 완료 |
| **STEP 3.8** | **Evidence / Policy Read-Only Isolation** | **UI/아키텍처** | ✅ 완료 |
| **STEP 3.7-β** | **Coverage 미확정 시 Results Panel UI Gating** | **UI** | ✅ 완료 |
| **STEP 3.7-γ** | **Coverage Guide Isolation / Conversation Hygiene** | **UI/아키텍처** | ✅ 완료 |
| **STEP 3.7-δ-β** | **Resolution State Reclassification (FAILED→UNRESOLVED)** | **기능/UI** | ✅ 완료 |
| **STEP 3.7-δ-γ** | **Frontend derives UI only from resolution_state** | **UI** | ✅ 완료 |
| **STEP 3.7-δ-γ2** | **Candidate selection passes coverage_codes → RESOLVED** | **UI** | ✅ 완료 |
| **STEP 3.7-δ** | **Resolution Lock & UNRESOLVED UI (Final)** | **UI** | ✅ 완료 |
| **STEP 3.7-δ-γ4** | **UNRESOLVED 후보 소스 정합화 (suggested_coverages)** | **UI** | ✅ 완료 |
| **STEP 3.7-δ-γ5** | **UNRESOLVED 최우선 렌더링 강제** | **UI** | ✅ 완료 |
| **STEP 3.7-δ-γ6** | **UNRESOLVED 후보 전체 렌더링 (slice/filter 제거)** | **UI** | ✅ 완료 |
| **STEP 3.7-δ-γ10** | **Insurer Anchor Lock (후보 선택 시 insurers 유지)** | **UI** | ✅ 완료 |

---

## 🕐 시간순 상세 내역

> Step 1-42 상세 기록: [status_archive.md](status_archive.md) (U-4.8 ~ U-4.18 포함)

## STEP 2.8: 하드코딩 비즈니스 규칙 YAML 외부화 (2025-12-19)

### 목표
- codebase 내 하드코딩된 비즈니스 규칙을 YAML 설정 파일로 외부화
- 코드 수정 없이 설정 파일만으로 규칙 변경 가능
- P0/P1/P2 분류 기반 체계적 외부화

### 분류 기준

| 등급 | 정의 | 조치 |
|------|------|------|
| **P0** | 비즈니스 규칙 / 도메인 지식 | 즉시 YAML 외부화 |
| **P1** | 품질 영향 키워드/패턴 | 권장 외부화 (향후) |
| **P2** | 알고리즘/정규식 | 코드 유지 |

### 외부화 완료 항목 (P0)

| 항목 | 원본 위치 | 대상 파일 |
|------|----------|----------|
| INSURER_ALIASES | api/compare.py | config/mappings/insurer_alias.yaml |
| COMPARE_PATTERNS | api/compare.py | config/rules/compare_patterns.yaml |
| POLICY_KEYWORD_PATTERNS | compare_service.py | config/mappings/policy_keyword_patterns.yaml |
| DOC_TYPE_PRIORITY | compare_service.py | config/rules/doc_type_priority.yaml |
| SLOT_SEARCH_KEYWORDS | compare_service.py | config/mappings/slot_search_keywords.yaml |
| COVERAGE_CODE_GROUPS | compare_service.py | config/mappings/coverage_code_groups.yaml |
| COVERAGE_CODE_TO_TYPE | slot_extractor.py | config/mappings/coverage_code_to_type.yaml |

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `api/config_loader.py` | P0 로더 함수 7개 추가 |
| `api/compare.py` | INSURER_ALIASES, COMPARE_PATTERNS → config loader |
| `services/retrieval/compare_service.py` | POLICY_KEYWORD_PATTERNS 등 → config loader |
| `services/extraction/slot_extractor.py` | _determine_coverage_type → config loader |
| `config/mappings/*.yaml` | 신규 5개 파일 |
| `config/rules/*.yaml` | 신규 2개 파일 |
| `docs/hardcode_audit.md` | 전수 조사 + 분류 문서 |

### 검증 결과

```
✅ pytest tests/test_extraction.py: 47 passed
✅ Docker API rebuild & smoke test: healthy
✅ /compare API 정상 응답 확인
```

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| P0 전수 조사 | ✅ 7개 항목 분류 |
| YAML 외부화 | ✅ 7개 파일 생성 |
| config_loader 확장 | ✅ 7개 함수 추가 |
| 기존 코드 import 교체 | ✅ 3개 파일 수정 |
| 테스트 통과 | ✅ 47 passed |
| 기능 회귀 없음 | ✅ API 정상 동작 |

---

## STEP 2.9: Query Anchor / Context Locking (2025-12-19)

### 목표
- 대화형 질의에서 기준 담보(coverage)와 질의 의도를 세션 단위로 고정
- "메리츠는?", "그럼 삼성은?" 같은 후속 질의에서 이전 coverage context 유지
- 모든 규칙을 YAML 설정 파일로 외부화

### 핵심 개념

**Query Anchor:**
```python
class QueryAnchor(BaseModel):
    coverage_code: str      # 대표 담보 코드 (예: A4200_1)
    coverage_name: str | None  # 대표 담보 명칭 (예: 암진단비)
    domain: str | None      # 담보 도메인 (CANCER, CARDIO 등)
    original_query: str     # anchor 생성 시점의 원본 질의
```

**후속 질의 유형:**
| 유형 | 설명 | 처리 |
|------|------|------|
| `new` | 신규 질의 (anchor 없음 또는 coverage 키워드 포함) | 새 anchor 생성 |
| `insurer_only` | insurer만 변경하는 후속 질의 | anchor.coverage_code 유지 |

### 구현 내용

**1. 설정 파일 (`config/rules/query_anchor.yaml`):**
```yaml
# 후속 질의 판별용 coverage 키워드
coverage_keywords:
  - 암
  - 암진단
  - 뇌졸중
  - 수술비
  # ... 39개 키워드

# insurer-only 후속 질의 패턴
insurer_only_patterns:
  - "은?"
  - "는?"
  - "그럼"
  # ... 13개 패턴

# intent 확장 키워드 (anchor 유지 + intent만 확장)
intent_extension_keywords:
  comparison: [비교, 대비, vs, 차이]
  condition: [조건, 지급조건, 면책, 대기기간]
  # ... 추가 그룹
```

**2. API 변경:**

요청 (CompareRequest):
```json
{
  "insurers": ["MERITZ"],
  "query": "메리츠는?",
  "anchor": {
    "coverage_code": "A4200_1",
    "coverage_name": "암진단비",
    "domain": "CANCER",
    "original_query": "삼성 암진단비 알려줘"
  }
}
```

응답 (CompareResponse):
```json
{
  "anchor": {
    "coverage_code": "A4200_1",
    "coverage_name": "암진단비",
    "domain": "CANCER",
    "original_query": "삼성 암진단비 알려줘"
  },
  "debug": {
    "anchor": {
      "query_type": "insurer_only",
      "has_anchor": true,
      "has_coverage_keyword": false,
      "extracted_insurers": ["MERITZ"],
      "restored_from_anchor": true,
      "anchor_coverage_code": "A4200_1"
    }
  }
}
```

**3. 후속 질의 판별 로직:**
```python
def _detect_follow_up_query_type(query: str, anchor: QueryAnchor | None) -> tuple[str, dict]:
    # 1. anchor 없으면 → "new"
    # 2. coverage 키워드 있으면 → "new" (anchor 재설정)
    # 3. insurer 키워드만 있으면 → "insurer_only"
    # 4. 그 외 → "new" (안전한 기본값)
```

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `config/rules/query_anchor.yaml` | 신규 생성 (coverage_keywords, insurer_only_patterns) |
| `api/config_loader.py` | +29 lines: get_query_anchor_config, get_coverage_keywords 등 |
| `api/compare.py` | +140 lines: QueryAnchor 모델, 후속 질의 판별, anchor 반환 |
| `tests/test_query_anchor.py` | 신규 생성 (21개 테스트) |

### 검증 시나리오

| # | 질의 | anchor 상태 | query_type | 결과 |
|---|------|-------------|------------|------|
| 1 | "DB손해보험 암진단비 알려줘" | 없음 | new | anchor 생성 (암진단비) |
| 2 | "메리츠는?" | 암진단비 | insurer_only | anchor 유지, MERITZ 검색 |
| 3 | "그럼 삼성은?" | 암진단비 | insurer_only | anchor 유지, SAMSUNG 검색 |
| 4 | "유사암은?" | 암진단비 | new | anchor 재설정 (유사암) |

### 검증 결과

```
✅ pytest tests/test_query_anchor.py: 21 passed
✅ pytest tests/test_compare_api.py: 57 passed
✅ API 스모크 테스트: 정상 동작
```

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| QueryAnchor 모델 정의 | ✅ 완료 |
| 후속 질의 판별 로직 | ✅ 완료 |
| API anchor 파라미터 | ✅ request/response 추가 |
| YAML 외부화 | ✅ query_anchor.yaml |
| 테스트 작성 | ✅ 21개 테스트 |
| 기능 회귀 없음 | ✅ 57개 기존 테스트 통과 |

---

## STEP 3.5: Advanced 옵션 Guard / Auto-Recovery (2025-12-19)

### 목표
- UI Advanced 옵션에서 insurer 0개 선택해도 시스템이 정상 동작
- insurer auto-recovery 로직으로 질의에서 추출하거나 기본 정책 적용
- 모든 규칙을 YAML 설정 파일로 외부화 (하드코딩 금지)

### 핵심 원칙
- **실행 차단 금지**: insurer 0개 상태에서도 쿼리 실행 허용
- **Auto-Recovery 적용**:
  1. 질의에서 insurer 추출 시도
  2. 추출 실패 시 기본 정책 적용 (전체 보험사 비교)
- **사용자 안내**: recovery 적용 시 안내 메시지 표시

### 구현 내용

**1. 설정 파일 (`config/rules/insurer_defaults.yaml`):**
```yaml
# 기본 보험사 리스트
default_insurers:
  - SAMSUNG
  - MERITZ
  - LOTTE
  - KB
  - DB
  - HANWHA
  - HYUNDAI
  - HEUNGKUK

# 기본 정책 모드
default_policy_mode: "all"  # "all" | "representative"

# 대표 보험사 (mode=representative 시 사용)
representative_insurers:
  - SAMSUNG
  - MERITZ

# 보정 메시지 템플릿
recovery_messages:
  no_insurer_default: "보험사 선택이 없어 전체 보험사 비교를 수행했습니다."
  no_insurer_extracted: "질의에서 {insurers}를 인식하여 비교를 수행했습니다."
```

**2. API 변경:**

요청 (CompareRequest):
```python
# min_length=1 제거 → 빈 리스트 허용
insurers: list[str] = Field(default=[], description="비교할 보험사 코드 리스트")
```

응답 (CompareResponse):
```json
{
  "recovery_message": "보험사 선택이 없어 전체 보험사 비교를 수행했습니다.",
  "debug": {
    "insurer_scope_method": "auto_recovery_default",
    "recovery_applied": true,
    "recovery_reason": "no_insurer_selected"
  }
}
```

**3. Frontend 변경:**
- ChatPanel: insurer 0개 체크 제거 (실행 허용)
- page.tsx: recovery_message 채팅에 표시

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `config/rules/insurer_defaults.yaml` | 신규 생성 (기본 정책 설정) |
| `api/config_loader.py` | +34 lines: get_insurer_defaults_config, get_default_insurers, get_recovery_messages |
| `api/compare.py` | min_length 제거, recovery_message 필드 추가, auto-recovery 로직 |
| `apps/web/src/lib/types.ts` | recovery_message 필드 추가 |
| `apps/web/src/components/ChatPanel.tsx` | insurer 0개 체크 제거 |
| `apps/web/src/app/page.tsx` | recovery_message 표시 로직 |

### 검증 시나리오

| # | 질의 | insurers | 결과 |
|---|------|----------|------|
| 1 | "암진단비 알려줘" | [] | auto_recovery_default, 전체 보험사 비교 |
| 2 | "삼성 암진단비" | [] | query_single_explicit, SAMSUNG 추출 |
| 3 | "다빈치 수술비 비교" | [] | auto_recovery_default, 전체 보험사 비교, 5 slots |

### 검증 결과

```
✅ Scenario 1: recovery_message="보험사 선택이 없어 전체 보험사 비교를 수행했습니다."
✅ Scenario 2: query_extracted_insurers=["SAMSUNG"], insurer_scope_method=query_single_explicit
✅ Scenario 3: recovery_message="보험사 선택이 없어 전체 보험사 비교를 수행했습니다.", slots_count=5
```

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| insurer 0개 실행 허용 | ✅ Frontend/Backend 모두 허용 |
| Auto-Recovery 로직 | ✅ 질의 추출 → 기본 정책 fallback |
| YAML 외부화 | ✅ insurer_defaults.yaml |
| recovery_message 표시 | ✅ 채팅창 안내 메시지 |
| 검증 시나리오 통과 | ✅ 3/3 (100%) |

---

## STEP 3.6: Intent Locking / Mode Separation (2025-12-19)

### 목표
- 질의 Intent(lookup/compare)를 명시적으로 고정하여 임의 전환 방지
- UI 이벤트(버튼 클릭, 연관 담보 선택)로 인한 intent 변경 차단
- Query Anchor의 coverage / insurer / intent 일관성 보장

### 핵심 원칙
- **기본 Intent는 lookup** (단일 보험사 정보 조회)
- **명시적 비교 키워드**가 있을 때만 compare로 변경
- **UI 이벤트는 intent를 변경할 수 없음**
- **coverage/insurer 변경은 intent 변경 사유가 아님**

### Intent 정의

| Intent | 설명 | 트리거 |
|--------|------|--------|
| lookup | 단일 보험사 정보 조회 | 기본값, "알려줘", "보여줘" 등 |
| compare | 복수 보험사 비교 | "비교", "차이", "vs" 등 명시적 키워드 |

### 구현 내용

**1. 설정 파일 (`config/rules/intent_keywords.yaml`):**
```yaml
# 비교 의도 트리거 키워드
compare_trigger_keywords:
  - 비교
  - 차이
  - " vs "
  - 어느 쪽
  # ...

# lookup 강제 유지 키워드
lookup_force_keywords:
  - 알려줘
  - 보여줘
  - 어떻게
  # ...

# Intent 변경 불가 UI 이벤트 타입
ui_events_no_intent_change:
  - coverage_button_click
  - related_coverage_select
  - slot_select
```

**2. QueryAnchor 모델 확장:**
```python
class QueryAnchor(BaseModel):
    coverage_code: str
    coverage_name: str | None
    domain: str | None
    original_query: str
    # STEP 3.6: Intent Locking
    intent: Literal["lookup", "compare"] = "lookup"
```

**3. Intent Resolution 로직:**
```python
def _resolve_intent(query, anchor, ui_event_type, query_insurers):
    # 1. UI 이벤트인 경우 → intent 변경 금지, anchor 유지
    # 2. anchor가 있는 경우 → 명시적 비교 키워드 없으면 유지
    # 3. 새 질의인 경우 → 키워드 기반 판별
```

**4. Frontend 변경:**
- `QueryAnchor` 타입에 intent 필드 추가
- `CompareRequestWithIntent` 타입 추가 (anchor, ui_event_type 포함)
- 응답에서 anchor 저장 후 다음 요청에 전달

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `config/rules/intent_keywords.yaml` | 신규 생성 (intent 키워드 설정) |
| `api/config_loader.py` | +42 lines: get_compare_trigger_keywords 등 함수 |
| `api/compare.py` | QueryAnchor.intent 필드, _resolve_intent 로직, ui_event_type 처리 |
| `apps/web/src/lib/types.ts` | QueryAnchor, CompareRequestWithIntent 타입 |
| `apps/web/src/lib/api.ts` | anchor, ui_event_type 전달 |
| `apps/web/src/app/page.tsx` | currentAnchor 상태 관리, 요청에 anchor 포함 |
| `apps/web/src/components/ChatPanel.tsx` | CompareRequestWithIntent 타입 사용 |

### 검증 시나리오

| # | 질의 | anchor 상태 | 결과 |
|---|------|-------------|------|
| 1 | "삼성의 암진단비 알려줘" | 없음 | intent=lookup ✅ |
| 2 | "일반암 진단금" (UI 클릭) | lookup | intent=lookup (차단) ✅ |
| 3 | "삼성과 메리츠 암진단비 비교" | 없음 | intent=compare ✅ |
| 4 | "유사암은?" | compare | intent=compare (유지) ✅ |

### 검증 결과

```
=== Scenario 1 ===
Expected: intent=lookup
  anchor.intent: lookup
Result: ✅ PASS

=== Scenario 2 ===
Expected: intent=lookup (UI 이벤트 - 차단)
  anchor.intent: lookup
  ui_event_blocked_change: True
Result: ✅ PASS

=== Scenario 3 ===
Expected: intent=compare
  anchor.intent: compare
  matched_compare_keyword: 비교
Result: ✅ PASS

=== Scenario 4 ===
Expected: intent=compare (anchor 유지)
  anchor.intent: compare
  intent_locked: True
Result: ✅ PASS
```

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| lookup/compare 분리 원칙 | ✅ 구현 완료 |
| UI 이벤트 intent 변경 차단 | ✅ ui_events_no_intent_change 적용 |
| coverage/insurer 변경 시 intent 유지 | ✅ anchor intent 보존 |
| 하드코딩 없음 | ✅ YAML 외부화 |
| 검증 시나리오 통과 | ✅ 4/4 (100%) |

---

## STEP 3.8: Evidence / Policy Read-Only Isolation (2025-12-19)

### 목표
- Evidence/Policy/Document 상세보기가 Query 실행이나 상태 변경을 유발하지 않도록 완전히 분리
- 문서 열람은 Read-only 동작으로만 처리
- Query Anchor / Intent / Insurer / Coverage 상태를 절대 변경하지 않음
- 문서 열람 중에도 좌측 요약·우측 비교 결과가 불변으로 유지

### 문제 인식

**현상:**
- Evidence 탭에서 "상품요약서 상세보기" 클릭 시 좌측 요약 영역이 재렌더링되거나 다른 상태로 변경됨
- 마치 새로운 질의를 실행한 것처럼 화면이 흔들림

**원인:**
- Evidence 상세보기가 조회(Read)가 아닌 Query Mutation(상태 변경)으로 처리되고 있음
- UI 이벤트가 Query Context를 침범함

### 구현 내용

**1. State 분류 정의 (`state-isolation.config.ts`):**
```typescript
// Query State: 질의 실행에 의해서만 변경되는 상태
export const QUERY_STATE_KEYS = [
  "messages",           // 채팅 메시지 목록
  "currentResponse",    // 현재 비교 결과
  "currentAnchor",      // Query Anchor (coverage, intent)
  "isLoading",          // 질의 실행 중 여부
] as const;

// View State: Read-only UI 이벤트에 의해 변경되는 상태
export const VIEW_STATE_KEYS = [
  "viewingDocument",    // 현재 보고 있는 문서
  "activeTab",          // 현재 활성 탭
  "scrollPosition",     // 스크롤 위치
  "expandedSections",   // 펼쳐진 섹션들
] as const;
```

**2. Read-only View Events 정의:**
```typescript
export const READ_ONLY_VIEW_EVENTS = [
  "evidence_view",              // Evidence 상세보기 클릭
  "policy_view",                // Policy 상세보기 클릭
  "document_view",              // 문서 상세보기 클릭
  "document_page_change",       // 문서 페이지 이동
  "document_zoom_change",       // 문서 확대/축소
  "document_close",             // 문서 닫기
  "tab_change",                 // 탭 전환
  // ...
] as const;
```

**3. ViewContext 생성 (`contexts/ViewContext.tsx`):**
- Query State와 완전히 분리된 View State 전용 컨텍스트
- viewingDocument, deepLinkDocument, activeTab 등 관리
- openDocument(), closeDocument() 등 View State 변경 함수 제공
- Query State 변경 불가 보장

**4. page.tsx 리팩토링:**
- ViewProvider 적용
- Query State와 View State 명확히 분리
- DocumentViewerLayer 컴포넌트로 뷰어 통합 관리
- memoizedResponse로 불필요한 re-render 방지

**5. EvidencePanel 수정:**
- ViewContext.openDocument() 사용
- 로컬 viewingEvidence 상태 제거
- PdfPageViewer 렌더링을 page.tsx로 이동
- Query State 변경 없이 문서 열기 보장

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/lib/state-isolation.config.ts` | 신규: State 분류 및 격리 규칙 정의 |
| `apps/web/src/contexts/ViewContext.tsx` | 신규: View State 전용 컨텍스트 |
| `apps/web/src/app/page.tsx` | ViewProvider 적용, DocumentViewerLayer 추가 |
| `apps/web/src/components/EvidencePanel.tsx` | ViewContext 사용, 로컬 상태 제거 |
| `apps/web/src/__tests__/state-isolation.test.ts` | 신규: 격리 규칙 단위 테스트 |

### 검증 시나리오

| # | 시나리오 | 기대 결과 | 검증 |
|---|----------|----------|------|
| 1 | "삼성의 암진단비 알려줘" | 좌측 요약 정상 표시 | ✅ |
| 2 | Evidence 탭 → 상품요약서 상세보기 클릭 | 문서 뷰어 열림, 좌측 요약 내용 변경 없음 | ✅ |
| 3 | 문서 페이지 이동 | Query 결과 불변 | ✅ |
| 4 | 문서 닫기 | 동일 Query 결과 유지 | ✅ |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| Evidence/Policy/Document 클릭 시 Query State 변경 0건 | ✅ 구현 완료 |
| 좌측 요약 및 우측 비교 결과 항상 유지 | ✅ 구현 완료 |
| Read-only View와 Query 실행 완전 분리 | ✅ ViewContext 분리 |
| 하드코딩/임시 dict 없음 | ✅ config 기반 |
| git 커밋 완료 | ✅ a6282d2 |
| status.md 업데이트 완료 | ✅ 본 항목 |

---

## STEP 3.7-β: Coverage 미확정 시 Results Panel UI Gating (2025-12-19)

### 목표
- 대표 담보가 확정되지 않은 상태(AMBIGUOUS / NOT_FOUND)에서 우측 Results Panel 렌더링 완전 차단
- 좌측은 "선택 필요" 상태인데, 우측은 "확정된 결과"처럼 보이는 상태 불일치를 방지

### 문제 인식

**현상:**
- "삼성 암진단금" (오타) 질의 시 "상해후유장해(3-100%)" 등 임의 담보가 대표 담보로 자동 선택됨
- 좌측에서 담보 선택을 유도하는 동안 우측에 비교 결과가 표시됨

**원인:**
- coverage_resolution 상태와 Results Panel 렌더링이 연동되어 있지 않음
- UI에서 EXACT/AMBIGUOUS/NOT_FOUND 상태에 따른 gating이 없음

### 구현 내용

**1. UI Gating 설정 (`ui-gating.config.ts`):**
```typescript
// API status → UI display state 매핑
export type UIResolutionState = "EXACT" | "AMBIGUOUS" | "NOT_FOUND";

export const RESOLUTION_STATUS_MAP: Record<string, UIResolutionState> = {
  resolved: "EXACT",
  suggest: "AMBIGUOUS",
  clarify: "AMBIGUOUS",
  failed: "NOT_FOUND",
};

// Results Panel 렌더링 허용 상태
export const RESULTS_PANEL_ALLOWED_STATES: UIResolutionState[] = ["EXACT"];
```

**2. ResultsPanel 수정:**
- canRenderResultsPanel() 호출로 렌더링 가능 여부 확인
- AMBIGUOUS / NOT_FOUND 상태에서 EmptyState 표시
- Compare / Diff / Evidence / Policy 탭 접근 차단

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/lib/ui-gating.config.ts` | 신규: UI Gating 규칙 정의 |
| `apps/web/src/components/ResultsPanel.tsx` | UI Gating 적용, EmptyState 표시 |
| `apps/web/src/__tests__/ui-gating.test.ts` | 신규: UI Gating 단위 테스트 |

### 검증 시나리오

| # | 시나리오 | 기대 결과 | 검증 |
|---|----------|----------|------|
| 1 | "삼성 암" | AMBIGUOUS → Results Panel 비활성화 | ✅ |
| 2 | "삼성 암진단비" | EXACT → Results Panel 정상 표시 | ✅ |
| 3 | "삼성 암zz" | NOT_FOUND → Results Panel 비활성화 | ✅ |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| Coverage 미확정 시 Results Panel 렌더링 차단 | ✅ 구현 완료 |
| EXACT 상태에서만 비교 결과 표시 | ✅ 구현 완료 |
| 연관 담보 자동 노출 차단 | ✅ 구현 완료 |
| 하드코딩 없음 | ✅ config 기반 |
| git 커밋 완료 | ✅ e1052d9 |
| status.md 업데이트 완료 | ✅ 본 항목 |

## STEP 3.7-γ: Coverage Guide Isolation / Conversation Hygiene (2025-12-19)

### 목표
- 담보 미확정(AMBIGUOUS/NOT_FOUND) 상태에서 가이드 메시지가 대화 로그에 누적되는 문제 제거
- 담보 선택 안내를 단일 상태 패널(UI State)로 격리
- Chat 영역은 "대화"로서의 역할만 수행

### 문제 인식

**현상:**
- "삼성 암" (모호한 질의) 입력 시 "여러 담보가 검색되었습니다..." 가이드 메시지가 ChatMessage로 누적
- 연속 질의 시 가이드 메시지가 계속 쌓여 대화 로그가 오염됨
- 좌측 Chat 영역과 담보 선택 안내의 역할이 혼재

**원인:**
- 담보 미확정 안내를 ChatMessage로 취급
- AMBIGUOUS/NOT_FOUND 상태에서도 assistant 메시지가 chat log에 추가됨

### 적용 원칙

| 원칙 | 설명 |
|------|------|
| 상태와 대화의 분리 | 담보 미확정 안내는 ChatMessage가 아님 |
| 가이드 단일성 원칙 | 가이드는 항상 1개만 존재 (교체, 누적 금지) |
| EXACT 상태 우선 원칙 | EXACT 상태에서만 Chat 로그에 정상 응답 추가 |

### 구현 내용

**1. Conversation Hygiene 설정 (`conversation-hygiene.config.ts`):**
```typescript
// ChatMessage로 추가 가능한 상태 (EXACT만 허용)
export const CHAT_MESSAGE_ALLOWED_STATES: UIResolutionState[] = ["EXACT"];

// 응답이 ChatMessage로 추가될 수 있는지 확인
export function canAddToChatLog(resolution: CoverageResolution | null | undefined): boolean {
  const state = getUIResolutionState(resolution);
  return CHAT_MESSAGE_ALLOWED_STATES.includes(state);
}

// Coverage Guide 상태 팩토리
export function createCoverageGuideState(
  resolution: CoverageResolution | null | undefined,
  originalQuery: string
): CoverageGuideState | null;
```

**2. CoverageGuidePanel 컴포넌트:**
```typescript
// 담보 미확정 상태에서 표시되는 상태 안내 패널
// - ChatMessage가 아님
// - 항상 단 하나만 존재
// - EXACT 상태에서는 자동 제거
export function CoverageGuidePanel({
  guide,
  onSelectCoverage,
}: CoverageGuidePanelProps);
```

**3. page.tsx 상태 분기:**
```typescript
// STEP 3.7-γ: Conversation Hygiene - 상태별 분기 처리
const canAddToChat = canAddToChatLog(response.coverage_resolution);

if (!canAddToChat) {
  // (A) AMBIGUOUS / NOT_FOUND: ChatMessage 추가 ❌, Guide Panel 표시 ✅
  const guide = createCoverageGuideState(response.coverage_resolution, request.query);
  setCoverageGuide(guide);
  return;
}

// (B) EXACT: ChatMessage 정상 응답 추가 ✅, Guide Panel 제거 ✅
setCoverageGuide(null);
// ... 정상 응답 처리
```

### 생성/수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/lib/conversation-hygiene.config.ts` | 상태와 대화 분리 규칙 정의 (신규) |
| `apps/web/src/components/CoverageGuidePanel.tsx` | 담보 선택 가이드 UI 컴포넌트 (신규) |
| `apps/web/src/app/page.tsx` | EXACT 상태에서만 ChatMessage 추가 |
| `apps/web/src/components/ChatPanel.tsx` | CoverageGuidePanel 통합 |
| `apps/web/src/__tests__/conversation-hygiene.test.ts` | 단위 테스트 (26개 케이스) |

### UI 역할 분리

| 영역 | 허용 출력 | 금지 출력 |
|------|----------|----------|
| Chat Log | 사용자 입력, EXACT 상태의 정상 응답 | 담보 선택 가이드, 안내 문구 |
| Coverage Guide Panel | AMBIGUOUS/NOT_FOUND 상태 안내 | - |
| Results Panel | EXACT 상태의 비교 결과 | AMBIGUOUS/NOT_FOUND 상태의 결과 |

### 검증 시나리오

| # | 쿼리 | 예상 동작 | 결과 |
|---|------|----------|------|
| 1 | "삼성 암" | Chat: 사용자 질의만, Guide Panel: 표시 | ✅ |
| 2 | "삼성 암진단비" | Chat: 사용자+응답, Guide Panel: 없음 | ✅ |
| 3 | "삼성 암zz" | Chat: 사용자 질의만, Guide Panel: 표시 | ✅ |
| 4 | 연속 질의 | 이전 가이드 교체, 누적 없음 | ✅ |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| 담보 가이드가 ChatMessage에 누적되지 않음 | ✅ 구현 완료 |
| 가이드는 항상 1개만 존재 | ✅ 구현 완료 |
| EXACT 상태에서만 Chat 로그에 응답 추가 | ✅ 구현 완료 |
| 하드코딩 없음 | ✅ config 기반 |
| 단위 테스트 통과 | ✅ 26/26 pass |
| git 커밋 완료 | ✅ 58b8231 |
| status.md 업데이트 완료 | ✅ 본 항목 |

---

## STEP 3.7-δ-β: Resolution State Reclassification (FAILED→UNRESOLVED) (2025-12-19)

### 목표
- coverage_resolution status "failed"를 "UNRESOLVED"로 재분류 (candidates >= 1인 경우)
- Resolution State 체계를 3단계로 정규화: RESOLVED | UNRESOLVED | INVALID
- Backend Gate: resolution_state !== RESOLVED일 때 compare/slots/diff/evidence 데이터 null 반환
- Frontend Guard: resolution_state !== RESOLVED일 때 Results Panel 렌더링 차단

### 문제 인식

**현상:**
- "다빈치 수술비" 질의 시 similarity 0.1923 < threshold 0.2로 인해 status="failed"
- candidates가 존재함에도 "담보 미확정" 오류 표시
- 사용자가 후보에서 선택할 기회 없이 차단됨

**원인:**
- "failed" status가 candidates 존재 여부와 관계없이 similarity threshold만으로 결정
- candidates >= 1이면 사용자가 선택할 수 있어야 하는데 차단됨

### Resolution State 정의

| 상태 | 조건 | UI 동작 |
|------|------|---------|
| **RESOLVED** | candidates == 1 && similarity >= confident | Results Panel 표시 |
| **UNRESOLVED** | candidates >= 1 (확정 불가) | 담보 선택 가이드 표시 |
| **INVALID** | candidates == 0 | 재입력 안내 표시 |

### 구현 내용

**1. Backend (api/compare.py):**
```python
# CoverageResolutionResponse 모델 수정
class CoverageResolutionResponse(BaseModel):
    status: Literal["RESOLVED", "UNRESOLVED", "INVALID"]
    resolved_coverage_code: str | None = None
    message: str | None = None
    suggested_coverages: list[SuggestedCoverageResponse] = []

# _evaluate_coverage_resolution 로직 수정
def _evaluate_coverage_resolution(...) -> CoverageResolutionResponse:
    if len(candidates) == 0:
        return CoverageResolutionResponse(status="INVALID", ...)
    if len(candidates) == 1 and best_similarity >= confident_threshold:
        return CoverageResolutionResponse(status="RESOLVED", ...)
    return CoverageResolutionResponse(status="UNRESOLVED", ...)
```

**2. Backend Gate (CompareResponseModel):**
```python
# resolution_state !== RESOLVED일 때 데이터 null 반환
class CompareResponseModel(BaseModel):
    resolution_state: Literal["RESOLVED", "UNRESOLVED", "INVALID"]
    resolved_coverage_code: str | None = None
    compare_axis: list[CompareAxisItemResponse] | None = None
    policy_axis: list[PolicyAxisItemResponse] | None = None
    coverage_compare_result: list[CoverageCompareItemResponse] | None = None
    diff_summary: list[DiffSummaryItemResponse] | None = None
    slots: list[SlotResponse] | None = None
```

**3. Frontend (ui-gating.config.ts, resolution-lock.config.ts):**
```typescript
// State 명칭 통일: EXACT→RESOLVED, AMBIGUOUS→UNRESOLVED, NOT_FOUND→INVALID
export type ResolutionState = "RESOLVED" | "UNRESOLVED" | "INVALID";

// RESOLVED 상태에서만 Results Panel 렌더링
export const RESULTS_PANEL_ALLOWED_STATES: ResolutionState[] = ["RESOLVED"];
```

**4. ResultsPanel 수정:**
```typescript
const resolutionState = response.resolution_state;
if (resolutionState !== "RESOLVED") {
    return <EmptyState message="담보 선택 필요" />;
}
```

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `api/compare.py` | status 값 변경, resolution_state 필드 추가, backend gate 구현 |
| `apps/web/src/lib/types.ts` | CoverageResolution.status 타입 변경, resolution_state 필드 추가 |
| `apps/web/src/lib/ui-gating.config.ts` | ResolutionState 명칭 통일 |
| `apps/web/src/lib/resolution-lock.config.ts` | ResolutionState 명칭 통일 |
| `apps/web/src/lib/conversation-hygiene.config.ts` | ResolutionState 명칭 통일 |
| `apps/web/src/components/ResultsPanel.tsx` | resolution_state 직접 사용 |
| `apps/web/src/app/page.tsx` | RESOLVED 상태 참조 변경 |

### 검증 결과

| # | 테스트 | 예상 | 결과 |
|---|--------|------|------|
| 1 | "다빈치 수술비" | resolution_state=UNRESOLVED, compare_axis=null | ✅ PASS |
| 2 | "삼성의 다빈치 수술비 비교" (0 candidates) | resolution_state=INVALID | ✅ PASS |
| 3 | "유사암 제외" | resolution_state=UNRESOLVED | ✅ PASS |
| 4 | "유사암진단비" | resolution_state=UNRESOLVED (4 candidates) | ✅ PASS |
| 5 | explicit coverage_code | resolution_state=RESOLVED, compare_axis 정상 | ✅ PASS |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| FAILED → UNRESOLVED 재분류 (candidates >= 1) | ✅ 구현 완료 |
| Resolution State 3단계 정규화 | ✅ RESOLVED/UNRESOLVED/INVALID |
| Backend Gate (null 데이터) | ✅ 구현 완료 |
| Frontend Guard (렌더링 차단) | ✅ 구현 완료 |
| similarity threshold 변경 없음 | ✅ 유지 |
| 테스트 통과 | ✅ 5/5 (100%) |

---

## STEP 3.7-δ-γ: Frontend derives UI only from resolution_state (2025-12-19)

### 목표
- Frontend가 `coverage_resolution.status`에서 재계산하지 않고 `resolution_state`만 사용
- UI 상태 결정 로직을 단순화하고 Single Source of Truth 원칙 준수

### 문제 인식

**현상:**
- Frontend에서 `getUIResolutionState(coverage_resolution)`을 호출하여 상태 재계산
- Backend와 Frontend 간 상태 불일치 가능성

**원인:**
- `coverage_resolution.status`를 Frontend에서 다시 해석
- API 응답의 `resolution_state`를 직접 사용하지 않음

### 구현 내용

**1. conversation-hygiene.config.ts:**
```typescript
// Before: CoverageResolution에서 상태 재계산
export function createCoverageGuideState(
  resolution: CoverageResolution | null | undefined,
  originalQuery: string
): CoverageGuideState | null;

// After: resolution_state 직접 사용
export function createCoverageGuideState(
  params: CreateGuideParams
): CoverageGuideState | null;

interface CreateGuideParams {
  resolutionState: ResolutionState | null | undefined;
  message?: string | null;
  suggestedCoverages?: SuggestedCoverage[];
  detectedDomain?: string | null;
  originalQuery: string;
}
```

**2. resolution-lock.config.ts:**
```typescript
// Before
export function resolveAnchorUpdate(
  currentAnchor, newAnchor, newResolution: CoverageResolution, resetCondition
);

// After: resolution_state 직접 사용
export function resolveAnchorUpdate(
  currentAnchor, newAnchor, newState: ResolutionState, resetCondition
);
```

**3. page.tsx:**
```typescript
// Before
const newState = getUIResolutionState(response.coverage_resolution);

// After: API 응답의 resolution_state 직접 사용
const newState: ResolutionState = response.resolution_state || "RESOLVED";
```

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/lib/conversation-hygiene.config.ts` | `createCoverageGuideState` params 객체 방식으로 변경 |
| `apps/web/src/lib/resolution-lock.config.ts` | `CoverageResolution` → `ResolutionState` 직접 사용 |
| `apps/web/src/app/page.tsx` | `response.resolution_state` 직접 사용 |

### 검증 결과

| # | 시나리오 | 예상 | 결과 |
|---|----------|------|------|
| 1 | "다빈치 수술비" 질의 | UNRESOLVED + 후보 목록 | ✅ PASS |
| 2 | 우측 패널 | "담보 선택 필요" + 결과 없음 | ✅ PASS |
| 3 | 후보 버튼 클릭 가능 | "다빈치로봇암수술비" 버튼 | ✅ PASS |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| coverage_resolution.status 재계산 제거 | ✅ 구현 완료 |
| resolution_state 직접 사용 | ✅ 구현 완료 |
| UNRESOLVED → 후보 목록 표시 | ✅ 구현 완료 |
| INVALID → 메시지만 표시 | ✅ 구현 완료 |
| RESOLVED → 결과 탭 표시 | ✅ 구현 완료 |
| Web UI 검증 | ✅ 스크린샷 확인 |
| git 커밋 완료 | ✅ ba7aaad |

## STEP 3.7-δ-γ2: Candidate selection passes coverage_codes → RESOLVED (2025-12-20)

### 목표
- UNRESOLVED 상태에서 후보 버튼 클릭 시 즉시 RESOLVED로 전환
- coverage_codes를 명시적으로 전달하여 재질의 없이 결과 표시

### 문제 인식

**현상:**
- 후보 버튼 클릭 시 coverage_name으로 재질의
- 동일한 애매한 질의가 반복되어 UNRESOLVED 유지

**원인:**
- `handleSelectCoverage`가 coverage_name만 전달
- API가 다시 coverage resolution을 수행

### 구현 내용

**page.tsx:**
```typescript
// Before: coverage_name만 전달
handleSendMessage({
  query: coverageName,
  insurers: ["SAMSUNG", "MERITZ"],
  top_k_per_insurer: 5,
});

// After: coverage_codes 명시 전달 → 즉시 RESOLVED
handleSendMessage({
  query: coverageName,
  insurers: ["SAMSUNG", "MERITZ"],
  coverage_codes: [coverageCode],
  top_k_per_insurer: 5,
});
```

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/app/page.tsx` | `handleSelectCoverage`에 `coverage_codes` 추가 |

### 검증 결과

| # | 시나리오 | 예상 | 결과 |
|---|----------|------|------|
| 1 | "다빈치 수술비" 질의 (SAMSUNG+HYUNDAI) | UNRESOLVED + 3 후보 버튼 | ✅ PASS |
| 2 | 후보 버튼 클릭 | RESOLVED + 결과 표시 | ✅ PASS |
| 3 | API coverage_codes 파라미터 | resolution_state="RESOLVED" | ✅ PASS |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| 후보 클릭 → RESOLVED 전환 | ✅ 구현 완료 |
| Results Panel 결과 표시 | ✅ 구현 완료 |
| git 커밋 완료 | ✅ fbc36b1 |

## STEP 3.7-δ: Resolution Lock & UNRESOLVED UI (Final) (2025-12-20)

### 목표
- Resolution Lock 및 UNRESOLVED 상태 UI 최종 정리
- 다빈치 수술비: UNRESOLVED → 3 candidates → selection required; no results before selection

### 검증 결과

| # | 시나리오 | 예상 | 결과 |
|---|----------|------|------|
| 1 | "다빈치 수술비" 질의 (SAMSUNG+HYUNDAI) | resolution_state=UNRESOLVED | ✅ PASS |
| 2 | 좌측 패널 | 3개 후보 버튼 (다빈치로봇암수술비, 유사암수술비, 암수술비) | ✅ PASS |
| 3 | 우측 패널 | "담보 선택 필요" | ✅ PASS |
| 4 | "담보 미확정" 텍스트 | 화면에 없음 | ✅ PASS |
| 5 | 선택 전 결과 탭 | 렌더링 안됨 | ✅ PASS |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| UNRESOLVED 우선 렌더링 | ✅ 구현 완료 |
| ResultsPanel resolution_state 직접 사용 | ✅ 구현 완료 |
| git 커밋 완료 | ✅ 2fc5770 |

## STEP 3.7-δ-γ4: UNRESOLVED 후보 소스 정합화 (2025-12-20)

### 목표
- UNRESOLVED 상태에서 후보 소스를 `coverage_resolution.suggested_coverages`로 통일
- 버튼 라벨 우선순위 정립

### 구현 내용

**후보 소스 우선순위:**
1. `response.coverage_resolution.suggested_coverages` (PRIMARY)
2. `response.coverage_candidates` (SECONDARY)
3. empty array

**버튼 라벨 우선순위:**
1. `coverage_name`
2. `coverage_name_ko`
3. `coverage_code`

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/app/page.tsx` | 후보 소스 우선순위 로직 추가 |
| `apps/web/src/components/CoverageGuidePanel.tsx` | 버튼 라벨 우선순위 로직 추가 |

### 검증 결과

| # | 시나리오 | 예상 | 결과 |
|---|----------|------|------|
| 1 | "다빈치 수술비" 질의 | 3개 후보 버튼 | ✅ PASS |
| 2 | 버튼 라벨 | 다빈치로봇암수술비, 유사암수술비, 암수술비(유사암 제외) | ✅ PASS |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| suggested_coverages 우선 사용 | ✅ 구현 완료 |
| 전체 후보 렌더링 (map) | ✅ 구현 완료 |
| git 커밋 완료 | ✅ 62e88d8 |

## STEP 3.7-δ-γ5: UNRESOLVED 최우선 렌더링 강제 (2025-12-20)

### 목표
- resolution_state 우선순위 명시화: UNRESOLVED > INVALID > RESOLVED
- UNRESOLVED일 때 "담보 미확정" 텍스트가 표시되지 않도록 보장

### 구현 내용

**resolution_state 우선순위:**
1. UNRESOLVED → "담보 선택 필요" + 후보 버튼
2. INVALID → "담보 미확정" (후보 없음)
3. RESOLVED → 결과 표시

### 검증 결과

| # | 시나리오 | 예상 | 결과 |
|---|----------|------|------|
| 1 | "다빈치 수술비" 질의 | UNRESOLVED | ✅ PASS |
| 2 | 좌측 패널 | "담보 선택 필요" + 3개 버튼 | ✅ PASS |
| 3 | 우측 패널 | "담보 선택 필요" | ✅ PASS |
| 4 | "담보 미확정" 텍스트 | 화면에 없음 | ✅ PASS |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| UNRESOLVED > INVALID 우선순위 | ✅ 구현 완료 |
| 문서화 주석 추가 | ✅ 구현 완료 |
| git 커밋 완료 | ✅ 111bd6c |

## STEP 3.7-δ-γ6: UNRESOLVED 후보 전체 렌더링 (2025-12-20)

### 목표
- 후보 배열 제한 코드 제거 (slice/filter/find/[0])
- 전체 후보를 map()으로 렌더링

### 구현 내용

**단순화된 후보 할당:**
```typescript
const candidates =
  response.coverage_resolution?.suggested_coverages ?? [];
```

### 검증 결과

| # | 시나리오 | 예상 | 결과 |
|---|----------|------|------|
| 1 | "다빈치 수술비" 질의 | 3개 후보 | ✅ PASS |
| 2 | 배열 제한 코드 | 없음 (grep 확인) | ✅ PASS |

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| slice/filter 제거 | ✅ 구현 완료 |
| 전체 후보 map() 렌더링 | ✅ 구현 완료 |
| git 커밋 완료 | ✅ 45f4a3a |

## STEP 3.7-δ Final Verification (2025-12-20)

### 최종 검증 결과

**테스트 조건:**
- Query: "다빈치 수술비"
- Insurers: SAMSUNG + HYUNDAI
- Expected: UNRESOLVED + 3 candidates

**API 검증:**
```json
{
  "resolution_state": "UNRESOLVED",
  "suggested": 3,
  "names": ["다빈치로봇암수술비", "유사암수술비", "암수술비(유사암 제외)"]
}
```

**UI 검증:**
| 항목 | 예상 | 결과 |
|------|------|------|
| Payload insurers | ["SAMSUNG","HYUNDAI"] | ✅ PASS |
| 좌측: 후보 버튼 | 3개 | ✅ PASS |
| 우측: 결과 패널 | "담보 선택 필요" | ✅ PASS |
| 선택 전 Compare/Diff/Evidence | 렌더링 안됨 | ✅ PASS |

### 시나리오 검증

| 시나리오 | 결과 |
|----------|------|
| A: UNRESOLVED → 3 candidates 노출 | ✅ PASS |
| B: 후보 선택 → RESOLVED 전환 | ✅ PASS |
| C: INVALID → 우측 패널 비움 | ✅ PASS |

### 결론
- **프론트엔드 버그 없음** (insurers payload = UI selection)
- **백엔드 버그 없음** (쿼리에 따라 정상 응답)
- **STEP 3.7-δ 전체 완료**

## STEP 3.7-δ-γ10: Insurer Anchor Lock (2025-12-20)

### 목표
- 담보 후보 선택 시 UI에서 선택한 insurers가 유지되도록 수정
- `handleSelectCoverage`에서 하드코딩된 `["SAMSUNG", "MERITZ"]` 제거

### 문제점
- 후보 버튼 클릭 시 `/compare` 재호출에서 insurers가 `["SAMSUNG", "MERITZ"]`로 고정됨
- UI에서 SAMSUNG+HYUNDAI 선택해도 Compare 결과가 SAMSUNG+MERITZ로 표시

### 해결책
1. `selectedInsurers` 상태를 ChatPanel에서 page.tsx(HomeContent)로 lift up
2. `handleSelectCoverage`에서 `selectedInsurers` 사용
3. ChatPanel에 `selectedInsurers`와 `onInsurersChange` props 추가

### 변경 파일
- `apps/web/src/app/page.tsx`: selectedInsurers 상태 추가, handleSelectCoverage 수정
- `apps/web/src/components/ChatPanel.tsx`: props로 insurers 상태 받도록 변경

### 검증 결과
- SAMSUNG+HYUNDAI 선택 후 후보 클릭해도 Compare insurers 유지 확인

### 완료 조건 충족 여부

| 조건 | 결과 |
|------|------|
| 후보 선택 후 insurers = UI 선택값 | ✅ 구현 완료 |
| 하드코딩 insurers 제거 | ✅ 구현 완료 |
| git 커밋 완료 | ✅ af33cbe |

---

## STEP 3.7-δ 전체 완료 요약 (2025-12-20)

### 완료된 서브스텝

| 스텝 | 내용 | 커밋 |
|------|------|------|
| 3.7-δ-β | Resolution State Reclassification | - |
| 3.7-δ-γ | Frontend resolution_state 직접 사용 | - |
| 3.7-δ-γ2 | Candidate selection → RESOLVED | fbc36b1 |
| 3.7-δ | Resolution Lock & UNRESOLVED UI | 2fc5770 |
| 3.7-δ-γ4 | UNRESOLVED 후보 소스 정합화 | 62e88d8 |
| 3.7-δ-γ5 | UNRESOLVED 최우선 렌더링 | 111bd6c |
| 3.7-δ-γ6 | 전체 후보 렌더링 | 45f4a3a |
| 3.7-δ-γ10 | Insurer Anchor Lock | af33cbe |

### 최종 동작

1. **UNRESOLVED 상태**: 후보 선택 UI 표시, Results 패널 차단
2. **후보 선택**: coverage_code 전달 → 즉시 RESOLVED
3. **Insurer 유지**: UI 선택 insurers가 후보 선택 후에도 유지
4. **Resolution Lock**: RESOLVED 상태 퇴행 방지

### 임시 로그 상태
- 임시 디버그 로그: 없음 ✅
- Resolution Lock 디버그 로그: 유지 (의도된 것)
