# 보험 약관 비교 RAG 시스템 - 진행 현황

> 최종 업데이트: 2025-12-20 (STEP 4.9: Single-Insurer Locked Coverage Detail View)

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
| **STEP 3.9** | **Anchor Persistence / explicit coverage lock** | **기능/UI** | ✅ 완료 (A/B/C/D verified) |
| **STEP 4.0** | **Diff Summary Text & Evidence Priority Ordering** | **UI/UX** | ✅ 완료 |
| **BUGFIX+REFACTOR** | **normalize_query_for_coverage 헌법 준수 리팩터링** | **버그수정/리팩터링** | ✅ 완료 |
| **STEP 4.1** | **다중 Subtype 비교 (경계성 종양/제자리암)** | **기능/UI** | ✅ 완료 |
| **STEP 4.2** | **DB 복구 안정화 (schema.sql 현행화 + Option A+)** | **DevOps/DB** | ✅ 완료 |
| **STEP 4.3** | **API/Container Code Sync Audit** | **DevOps/검증** | ✅ 완료 |
| **STEP 4.4** | **UI Contract Debug View (suggested_coverages 경로 고정)** | **UI/검증** | ✅ 완료 |
| **STEP 4.5** | **locked_coverage_codes 확장 (멀티 subtype 지원)** | **기능/UI** | ✅ 완료 |
| **STEP 4.5-β** | **복수 담보 선택 UI (체크박스 + 적용 버튼)** | **UI** | ✅ 완료 |
| **STEP 4.6** | **멀티 Subtype 비교 UX 고도화 (소비 규약 고정)** | **UI/아키텍처** | ✅ 완료 |
| **STEP 4.7** | **Subtype Description Quality 강화 (4요소 규약)** | **기능/UI** | ✅ 완료 |
| **STEP 4.7-β** | **단일 회사 특정 담보 조회 결과 생성 보장** | **기능** | ✅ 완료 |
| **STEP 4.7-γ** | **Single-Insurer Locked Coverage E2E 검증** | **검증** | ✅ 완료 |
| **STEP 4.9** | **Single-Insurer Locked Coverage Detail View** | **UI** | ✅ 완료 |

---

## 🕐 시간순 상세 내역

> Step 1-42 + STEP 2.8~3.9 상세 기록: [status_archive.md](status_archive.md)

## STEP 4.9: Single-Insurer Locked Coverage Detail View (2025-12-20)

### 목적
단일 보험사 + 특정 담보 고정(locked_coverage_codes) 시 전용 상세 뷰로 전환

### 전환 조건 (Contract)
```
selectedInsurers.length == 1
AND debug.anchor.coverage_locked == true
AND debug.anchor.locked_coverage_codes.length >= 1
```

### 검증 결과

| 시나리오 | 조건 | 기대 UI Mode | 결과 |
|---------|------|--------------|------|
| A | 단일 insurer, UNRESOLVED | GUIDE | ✅ PASS |
| B | 단일 insurer + locked | SINGLE_DETAIL | ✅ PASS |
| C | 2개 insurer + locked | COMPARE | ✅ PASS |

### 구현 내용
1. **SingleCoverageDetailView 컴포넌트**: 단일 보험사 전용 상세 화면
2. **determineUIMode 함수**: UI 모드 결정 (SINGLE_DETAIL / COMPARE / GUIDE)
3. **금액 표시**: best_evidence 기반만 사용 (resolved_amount 생성 금지)
4. **SlotsTable**: singleInsurer prop 추가로 단일 보험사 필터링

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/components/SingleCoverageDetailView.tsx` | 신규 - 상세 뷰 컴포넌트 |
| `apps/web/src/components/SlotsTable.tsx` | singleInsurer prop 추가 |
| `apps/web/src/app/page.tsx` | UI Mode 분기 로직 |

### 산출물
- Audit 문서: `docs/audit/step_4_9_single_insurer_ui_detail_view_20251220.md`

---

## STEP 4.7-γ: Single-Insurer Locked Coverage E2E 검증 (2025-12-20)

### 목적
STEP 4.7-β 변경사항이 Docker 컨테이너(E2E)에서 정상 동작하는지 확인

### 검증 결과

**PASS**: 모든 검증 조건 충족

| 기준 | 결과 | 상태 |
|------|------|------|
| `debug.anchor.coverage_locked == true` | true | ✅ |
| `debug.anchor.locked_coverage_codes` | ["A4200_1"] | ✅ |
| `coverage_compare_result[*].coverage_code` | ["A4200_1"] | ✅ |
| `coverage_code != "__amount_fallback__"` | A4200_1 | ✅ |
| `debug.retrieval.fallback_used` | true | ✅ |
| `debug.retrieval.fallback_reason` | no_tagged_chunks_for_locked_code | ✅ |
| `debug.retrieval.effective_locked_code` | A4200_1 | ✅ |

### 이슈 및 해결
- **초기 FAIL**: Docker 컨테이너에 최신 코드가 반영되지 않음
- **해결**: `docker compose -f docker-compose.demo.yml build api --no-cache` 후 재테스트 PASS

### 산출물
- Audit 문서: `docs/audit/step_4_7_single_insurer_locked_audit_20251220.md`

---

## STEP 4.7-β: 단일 회사 특정 담보 조회 결과 생성 보장 (2025-12-20)

### 목적
단일 회사 + 특정 담보 조회(`locked_coverage_codes`) 요청 시 RESOLVED 상태에서 실제 비교 결과가 생성되지 않는 문제 수정

### 문제 분석

**As-Is (문제 상황)**:
- 입력: `{"query": "암진단비", "insurers": ["SAMSUNG"], "locked_coverage_codes": ["A4200_1"]}`
- `resolution_state`: RESOLVED ✅
- `debug.anchor.coverage_locked`: true ✅
- `coverage_compare_result[0].coverage_code`: **`__amount_fallback__`** ❌

**원인**:
1. DB에 `A4200_1`로 태깅된 chunk가 0건
2. `get_compare_axis()`가 빈 결과 반환
3. 2-pass fallback으로 `get_amount_bearing_evidence()` 호출
4. 새 `CompareAxisResult` 생성 시 `coverage_code="__amount_fallback__"` 하드코딩

**To-Be (수정 후)**:
- `locked_coverage_codes`가 제공된 경우, fallback 결과의 `coverage_code`도 해당 locked code 사용
- `__amount_fallback__`은 locked 상태에서 UI/사용자에게 절대 노출 금지

### 구현

**1. compare_service.py**
- `compare()` 함수에 `locked_coverage_codes: list[str] | None` 파라미터 추가
- `effective_locked_code = locked_coverage_codes[0]` (단일 insurer 기준)
- fallback 시:
  - `coverage_code = effective_locked_code` (not `__amount_fallback__`)
  - `debug.retrieval.fallback_used = true`
  - `debug.retrieval.fallback_reason = "no_tagged_chunks_for_locked_code"`
  - `debug.retrieval.fallback_source = "amount_pass_2"`

**2. api/compare.py**
- `compare()` 호출 시 `locked_coverage_codes=effective_locked_codes` 전달

### 검증 기준 (DoD)

| 조건 | 기대값 |
|------|--------|
| `debug.anchor.coverage_locked` | `true` |
| `resolution_state` | `RESOLVED` |
| `coverage_compare_result[0].coverage_code` | `A4200_1` (not `__amount_fallback__`) |
| `debug.retrieval.fallback_used` | `true` (DB 태깅 누락 시) |

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `services/retrieval/compare_service.py` | `locked_coverage_codes` 파라미터 추가, fallback 시 effective_locked_code 사용 |
| `api/compare.py` | `compare()` 호출 시 `locked_coverage_codes` 전달 |
| `status.md` | STEP 4.7-β 문서화 |

### 비고
- Docker/DB 미실행 상태로 실제 E2E 테스트는 미수행
- 코드 변경 적용 후 서버 재시작 필요

---

## STEP 4.7: Subtype Description Quality 강화 (2025-12-20)

### 목적
Subtype별 비교 항목을 4요소(Definition/Condition/Boundary/Evidence)로 규격화하여 정보 품질 향상

### 4요소 규약

| 요소 | 설명 | 필수 |
|------|------|------|
| **Definition** (정의) | 해당 subtype의 약관 정의 | ✅ |
| **Condition** (지급 조건) | 보장 조건, 대기기간 등 | ✅ |
| **Boundary** (경계/감액/제한) | 감액, 지급률, 면책, 제외 조건 | ✅ |
| **Evidence** (근거 인용) | doc_type + page + excerpt | ✅ |

### Evidence 우선순위
1. 약관 (최우선)
2. 사업방법서
3. 가입설계서
4. 상품요약서 (보조만)

### 구현

**1. config/rules/subtype_slots.yaml**
- `boundary` info_type 추가 (priority: 4, required: true)
- `boundary_keywords` 리스트: 감액, 지급률, 면책, 제외, 미지급, 한도, 90일 등
- 모든 subtype `comparison_focus`에 "경계/감액/제한" 추가

**2. services/extraction/subtype_extractor.py**
- `BOUNDARY_KEYWORDS` 상수 정의
- `_extract_boundary()` 함수: 경계/감액/제한 정보 추출
- `evidence_ref` 필드 강화: `doc_type`, `excerpt` 추가
- `unknown_reason` 필드: 미확인 시 사유 표시

**3. apps/web/src/lib/types.ts**
- `SubtypeComparisonItem.evidence_ref` 강화:
  - `doc_type?: string | null` (약관, 사업방법서, 상품요약서)
  - `excerpt?: string | null` (원문 발췌 1-2문장)
- `unknown_reason?: string | null` 추가

**4. apps/web/src/components/SubtypeComparePanel.tsx**
- `infoTypeOrder`: coverage → definition → conditions → boundary
- `EvidenceIndicator` 컴포넌트: doc_type/page/excerpt 표시
- Boundary 미발견 시 "특이 조건 없음" 표시

### 검증 시나리오 (모두 PASS)

| 시나리오 | 입력 | 결과 |
|----------|------|------|
| A: Multi-subtype 4요소 | `query: "경계성 종양과 제자리암 비교"` | 4 info_types (definition, coverage, conditions, boundary), evidence_ref with doc_type/excerpt ✅ |
| B: locked_coverage_codes | `locked_coverage_codes: ["A4200_1","A4210"]` | `debug.anchor.coverage_locked: true` ✅ |
| C: UNRESOLVED | `query: "다빈치 수술비 비교"` | `resolution_state: UNRESOLVED`, suggested_coverages 표시 ✅ |

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `config/rules/subtype_slots.yaml` | boundary info_type + keywords 추가 |
| `services/extraction/subtype_extractor.py` | _extract_boundary(), enhanced evidence_ref |
| `apps/web/src/lib/types.ts` | SubtypeComparisonItem.evidence_ref 강화 |
| `apps/web/src/components/SubtypeComparePanel.tsx` | EvidenceIndicator 컴포넌트, 4요소 순서 |

---

## STEP 4.6: 멀티 Subtype 비교 UX 고도화 (2025-12-20)

### 목적
1. **정답 소비 규약 고정**: Backend가 제공하는 유일한 정답 경로를 UI에서 일관되게 소비
2. **멀티 Subtype 비교 UX 정식화**: 경계성 종양 + 제자리암 등 복수 subtype 동시 비교 지원

### 절대 규약 (Hard Contract Rules)

**Coverage Lock 규약** (단 하나의 정답 경로):
```
debug.anchor.coverage_locked
debug.anchor.locked_coverage_codes
```
- ❌ 최상위 필드 참조 금지
- ❌ anchor_debug 직접 참조 금지

**Suggested Coverage 소비 규약**:
```
coverage_resolution.suggested_coverages
```
- ❌ debug 내부 추천 데이터 사용 금지

### 구현

**1. ResultsPanel.tsx - Lock 규약 수정**
- `debug.anchor.*` 경로만 사용
- Contract Debug View에 정답 경로 명시

**2. SubtypeComparePanel.tsx - Subtype별 결과 분리 표시**
- Accordion 형태로 Subtype별 그룹핑
- 각 Subtype: 보장 여부 / 정의 요약 / 지급 조건
- 금액 중심 단일 테이블 표현 금지

**3. Debug View 책임 분리**
- "🔧 Debug (개발자 전용)" 라벨
- 경고 메시지 추가: "이 섹션은 개발자/QA 전용입니다"
- 사용자 UX 판단 기준으로 사용 금지

### 검증 시나리오 (모두 PASS)

| 시나리오 | 입력 | 결과 |
|----------|------|------|
| A: 단일 subtype | `locked_coverage_codes: ["A4200_1"]` | `coverage_locked: true`, RESOLVED ✅ |
| B: 멀티 subtype | `locked_coverage_codes: ["A4200_1", "A4210"]` | `coverage_locked: true`, SUBTYPE_MULTI, 2개 subtype ✅ |
| C: 미선택 | (없음) | UNRESOLVED, suggested_coverages 표시 ✅ |

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `ResultsPanel.tsx` | debug.anchor.* 경로 사용, Debug 섹션 책임 분리 |
| `SubtypeComparePanel.tsx` | Subtype별 Accordion 그룹핑 UI |

### 관련 커밋
- `ecc8738`: feat: STEP 4.6 multi-subtype UX refinement with contract rules

---

## STEP 4.5-β: 복수 담보 선택 UI (2025-12-20)

### 목적
멀티 subtype 비교를 위해 복수 담보를 체크박스로 선택하고 한 번에 비교 실행

### 구현

**1. CoverageGuidePanel 개선**
- 단일 클릭 버튼 → 체크박스 목록으로 변경
- similarity 퍼센트 표시
- "N개 담보로 비교" 적용 버튼 추가
- `onSelectCoverages` 콜백 (복수 선택)

**2. page.tsx**
- `handleSelectCoverages`: 복수 담보 선택 핸들러
- `lockedCoverages` 배열로 복수 담보 저장

**3. Checkbox 컴포넌트**
- `@radix-ui/react-checkbox` 설치
- `ui/checkbox.tsx` 생성

### 검증 시나리오

| 시나리오 | 입력 | 결과 |
|----------|------|------|
| 단일 선택 | `locked_coverage_codes: ["A4200_1"]` | `debug.anchor.coverage_locked: true` ✅ |
| 복수 선택 | `locked_coverage_codes: ["A4200_1", "A4210"]` | `debug.anchor.coverage_locked: true` ✅ |

**주의**: `coverage_locked` 정보는 `debug.anchor` 필드에 포함됨 (최상위가 아님)

### 관련 커밋
- `e90a928`: feat: STEP 4.5-β multi-select coverage UI with checkboxes

---

## STEP 4.5: locked_coverage_codes 확장 (2025-12-20)

### 목적
멀티 subtype 비교를 위해 `locked_coverage_code` (단일)을 `locked_coverage_codes` (복수)로 확장

### 변경 사항

**1. Backend (api/compare.py)**
- `locked_coverage_codes: list[str] | None` 필드 추가
- `locked_coverage_codes` 우선, `locked_coverage_code` fallback 처리
- `anchor_debug.locked_coverage_codes` 배열로 표시

**2. Frontend**
- `types.ts`: `CompareRequestWithIntent.locked_coverage_codes` 추가
- `page.tsx`: `lockedCoverage` → `lockedCoverages` (배열) 변경
- `ResultsPanel.tsx`: Contract Debug에 `locked_coverage_codes` 표시

### 하위 호환성
- 기존 `locked_coverage_code` (단일)도 계속 지원
- 복수 형태가 우선 적용됨

### 관련 커밋
- `d901d37`: feat: STEP 4.5 locked_coverage_codes for multi-subtype support

---

## STEP 4.4: UI Contract Debug View (2025-12-20)

### 목적
UI가 `coverage_resolution.suggested_coverages` 경로만 사용하는지 확인 및 개발용 디버그 뷰 추가

### 확인 결과

1. **UI Contract 검증**: 이미 올바르게 구현됨
   - `types.ts`: `suggested_coverages`는 `CoverageResolution` 내부에만 존재
   - `page.tsx:256-257`: `response.coverage_resolution?.suggested_coverages ?? []`
   - `ResultsPanel.tsx:102-118`: `resolution_state !== "RESOLVED"`일 때 렌더링 차단

2. **Contract Debug View 추가**: ResultsPanel에 보라색 테마의 디버그 패널
   - 표시 항목: `resolution_state`, `coverage_resolution.status`, `suggested_coverages.length`, `locked_coverage_code`
   - RESOLVED/UNRESOLVED/INVALID 모든 상태에서 표시

3. **검증 시나리오 결과**: 3개 모두 PASS
   | 시나리오 | 질의 | 결과 |
   |----------|------|------|
   | A | "다빈치 수술비 비교" | UNRESOLVED + 3개 후보 ✅ |
   | B | "경계성 종양 보장 비교" | UNRESOLVED + 2개 후보 ✅ |
   | C | "피자 추천" | INVALID + 0개 후보 ✅ |

### 관련 커밋
- `4cd249d`: feat: STEP 4.4 Contract Debug View for UI suggested_coverages

---

## STEP 4.3: API/Container Code Sync Audit (2025-12-20)

### 목적
STEP 4.2 DB 복구 후 API가 coverage 추천을 정상 반환하는지 검증

### 확인 결과

1. **컨테이너 코드 동기화**: 이미지 빌드 방식 (코드 마운트 없음)
   - 컨테이너 내부 파일 = 로컬 파일 (2026 lines 일치)

2. **표준 재빌드 명령**:
   ```bash
   docker compose -f docker-compose.demo.yml build api && \
   docker compose -f docker-compose.demo.yml up -d api
   ```

3. **테스트 결과**: 4개 시나리오 모두 PASS
   | 시나리오 | 질의 | 결과 |
   |----------|------|------|
   | A | "다빈치 수술비 비교" | UNRESOLVED + 3개 후보 ✅ |
   | B | "삼성과 현대 다빈치 수술비를 비교해줘" | UNRESOLVED + 3개 후보 ✅ |
   | C | "경계성 종양 보장 비교" | UNRESOLVED + 2개 후보 ✅ |
   | D | "피자 추천" | INVALID ✅ |

4. **초기 오진 원인**: 잘못된 필드 확인
   - ❌ 최상위 `suggested_coverages` (존재하지 않음)
   - ✅ `coverage_resolution.suggested_coverages` (정상 데이터 존재)

### 결론
- 코드 수정 불필요
- API는 설계대로 정상 작동 중
- 감사 리포트: `docs/audit/api_sync_report_20251220.md`

### 관련 커밋
- `b112f2a`: docs(audit): add api sync report verifying coverage suggestions work correctly

---

## STEP 4.2: DB 복구 안정화 (schema.sql 현행화 + Option A+) (2025-12-20)

### 배경
Docker crash 후 DB 재생성 시:
- coverage_standard/coverage_alias가 수동 입력으로 잘못 적재됨
- migrations 2건 (trgm 인덱스, comparison_slot_cache)이 미적용됨
- 엑셀 기준 28개 표준코드 vs 6개 수동 입력 불일치

### 수행 내용

1. **schema.sql 현행화 (squash)**
   - `idx_chunk_content_trgm`: chunk.content 전체 trigram 인덱스
   - `idx_chunk_content_trgm_policy`: 약관 전용 부분 인덱스
   - `idx_chunk_insurer_doctype`: 복합 검색 인덱스
   - `comparison_slot_cache` 테이블 + 인덱스 + 트리거

2. **Option A+ 스크립트 추가**
   - 경로: `tools/reset_db_option_a_plus.sh`
   - coverage_standard/coverage_alias TRUNCATE
   - `담보명mapping자료.xlsx` 기반 적재 (28개 표준코드, 264개 alias)
   - 누락 인덱스/테이블 자동 생성
   - 검증: rowcount, extension, index, table

3. **감사 리포트**
   - `docs/audit/db_gap_report_20251220.md`

### 검증 결과

| 항목 | 기대값 | 실제값 | 상태 |
|------|--------|--------|------|
| coverage_standard | 28 | 28 | ✅ |
| coverage_alias | 264 | 264 | ✅ |
| pg_trgm extension | 존재 | 존재 | ✅ |
| trgm 인덱스 | 2+ | 2 | ✅ |
| comparison_slot_cache | 존재 | 존재 | ✅ |

### 관련 커밋
- `e31a53c`: chore(db): squash migrations into schema.sql
- `637feec`: tools: add reset_db_option_a_plus for reproducible coverage reload

### 주의사항
- API 컨테이너 재빌드 필요 시 `docker compose -f docker-compose.demo.yml build api`
- 새 DB 생성 시 schema.sql만으로 전체 스키마 적용됨
- coverage 데이터는 `tools/reset_db_option_a_plus.sh` 또는 `load_coverage_mapping.py`로 적재

---

## STEP 4.1: 다중 Subtype 비교 (경계성 종양/제자리암) (2025-12-20)

### 목표
- 경계성 종양, 제자리암 등 **질병 하위 개념(Subtype)**이 복수로 포함된 질의에 대해
- **정의·포함 여부·조건 중심 비교** 제공 (금액 중심 비교가 아님)
- 헌법 준수: 모든 Subtype 정의는 YAML 설정 파일에서 로드
- **SUBTYPE_MULTI 상태 도입**: 멀티 Subtype 입력 시 Resolution Lock 금지

### 핵심 규칙

1. **경계성 종양 / 제자리암은 단일 담보가 아니다**
   - 두 개 모두 `암 subtype` 이며 하나의 coverage_code로 RESOLVED 하면 안 된다

2. **멀티 subtype 입력 시 Resolution Lock 금지**
   - `resolution_state = SUBTYPE_MULTI`
   - `resolved_coverage_code = null`
   - `locked_coverage_code = null`
   - 담보 선택 UI 노출 금지

### 구현

**1. 설정 파일**
- `config/rules/subtype_slots.yaml`: Subtype 정의 SSOT
  - BORDERLINE_TUMOR (경계성 종양)
  - CIS_CARCINOMA (제자리암/상피내암)
  - SIMILAR_CANCER (유사암)
  - RECURRENT_CANCER (재진단암)
  - STROKE (뇌졸중)
  - CEREBROVASCULAR (뇌혈관질환)
  - ISCHEMIC_HEART (허혈성심장질환)

**2. Backend**
- `services/extraction/subtype_extractor.py`: Subtype 추출 서비스
  - `extract_subtypes_from_query()`: 질의에서 subtype 추출
  - `is_multi_subtype_query()`: 복수 subtype 질의 판별
  - `extract_subtype_comparison()`: 보험사별 비교 추출
- `api/compare.py`:
  - `resolution_state`에 `SUBTYPE_MULTI` 추가 (line 227, 304)
  - 멀티 Subtype 감지 시 SUBTYPE_MULTI 상태 강제 (line 1552-1616)
  - SUBTYPE_MULTI 상태 특별 처리 (line 1327-1371)

**3. Frontend**
- `apps/web/src/lib/types.ts`: SubtypeComparison 타입 추가
- `apps/web/src/components/SubtypeComparePanel.tsx`: Subtype 비교 테이블 컴포넌트
- `apps/web/src/components/ResultsPanel.tsx`: Subtype 탭 연동

### API 응답 변경

```typescript
interface SubtypeComparison {
  subtypes: string[];  // ["BORDERLINE_TUMOR", "CIS_CARCINOMA"]
  comparison_items: SubtypeComparisonItem[];
  is_multi_subtype: boolean;  // true
}

interface SubtypeComparisonItem {
  subtype_code: string;
  subtype_name: string;
  info_type: string;  // definition, coverage, conditions
  info_label: string;  // 정의, 보장 여부, 지급 조건
  insurer_code: string;
  value: string | null;
  confidence: "high" | "medium" | "low" | "not_found";
}
```

### 검증 시나리오

| 시나리오 | 입력 | 기대 결과 | 상태 |
|---------|------|----------|------|
| A | "경계성 종양과 제자리암을 삼성과 메리츠로 비교해줘" | `SUBTYPE_MULTI`, subtypes=2개 | ✅ PASS |
| B | "제자리암, 경계성 종양 차이 알려줘" | `SUBTYPE_MULTI`, subtypes=2개 | ✅ PASS |
| 단일 | "경계성 종양 보장 비교" | `RESOLVED` (A4210) | ✅ PASS |

### 테스트
- `tests/test_subtype_extractor.py`: 8개 유닛 테스트 (PASS)
  - 단일/복수 subtype 추출
  - Alias 매칭 (상피내암 → CIS_CARCINOMA)
  - 도메인별 조회
  - 설정 파일 로드 확인

### 커밋
- `e4bd059`: feat: STEP 4.1 multi-subtype comparison (borderline + in-situ)

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `config/rules/subtype_slots.yaml` | 신규 - Subtype 정의 SSOT |
| `services/extraction/subtype_extractor.py` | 신규 - Subtype 추출 서비스 |
| `api/compare.py` | subtype_comparison 필드 추가 |
| `apps/web/src/lib/types.ts` | SubtypeComparison 타입 추가 |
| `apps/web/src/components/SubtypeComparePanel.tsx` | 신규 - 비교 테이블 컴포넌트 |
| `apps/web/src/components/ResultsPanel.tsx` | Subtype 탭 연동 |
| `tests/test_subtype_extractor.py` | 신규 - 8개 유닛 테스트 |

---

## STEP 4.0: Diff Summary Text & Evidence Priority Ordering (2025-12-20)

### 목표
- 비교 결과 가독성 향상: Diff 탭에 요약 문구 추가
- Evidence 신뢰성 표시: P1/P2/P3 우선순위로 정렬 및 표시
- 표현만 변경, 비교 로직/계산/해석 변경 금지

### 구현

**1. Diff Summary Text**
- `config/rules/diff_summary_rules.yaml`: 요약 문구 템플릿 정의
- `apps/web/src/lib/diff-summary.config.ts`: 프론트엔드 규칙 로더
- Diff 탭 상단에 요약 섹션 추가

**2. Evidence Priority**
- `config/rules/evidence_priority_rules.yaml`: 우선순위 분류 규칙
- `apps/web/src/lib/evidence-priority.config.ts`: P1/P2/P3 분류 로직

| 우선순위 | 이름 | 설명 | 표시 |
|----------|------|------|------|
| P1 | 결정 근거 | 금액/값이 직접 추출된 문장 | ⭐⭐⭐ (펼침) |
| P2 | 해석 근거 | 정의/조건 설명 문장 | ⭐⭐ (접힘) |
| P3 | 보조 근거 | 요약/설명성 문장 | ⭐ (접힘) |

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `config/rules/diff_summary_rules.yaml` | 신규 - Diff 요약 규칙 |
| `config/rules/evidence_priority_rules.yaml` | 신규 - Evidence 우선순위 규칙 |
| `apps/web/src/lib/diff-summary.config.ts` | 신규 - Diff 요약 config |
| `apps/web/src/lib/evidence-priority.config.ts` | 신규 - Evidence 우선순위 config |
| `apps/web/src/components/DiffSummary.tsx` | 요약 섹션 추가 |
| `apps/web/src/components/EvidencePanel.tsx` | 우선순위 정렬 및 배지 표시 |

### 금지 사항 준수
- ✅ Diff 계산 로직 변경 없음
- ✅ Evidence 내용 수정/요약 없음
- ✅ 유리/불리/추천 표현 미사용
- ✅ Resolution Lock 영향 없음

---

## BUGFIX + REFACTOR: normalize_query_for_coverage 헌법 준수 리팩터링 (2025-12-20)

### 문제
- 질의: "삼성과 현대 다빈치 수술비를 비교해줘"
- 증상: `resolution_state: INVALID`, `recommended_coverage_codes: []`
- 원인: `normalize_query_for_coverage()`가 보험사명을 제거하지 않아 pg_trgm similarity가 낮음

### 1차 수정 (c98ef9c)
- 보험사명 제거 기능 추가
- 의도 표현/조사 제거 기능 추가
- **문제**: 하드코딩 fallback 리스트 존재 (헌법 위반)

### 2차 리팩터링 (헌법 준수)
`services/retrieval/compare_service.py` 재수정:
1. **하드코딩 fallback 제거**: `_load_insurer_aliases()`에서 하드코딩 리스트 제거
2. **설정 파일 외부화**: `config/rules/query_normalization.yaml` 신규 생성
   - `intent_suffixes`: 의도 표현 suffix 목록
   - `trailing_particles_pattern`: 끝 조사 정규식
   - `intermediate_particles`: 중간 조사 정규식
   - `punctuation_pattern`: 특수문자 정규식
3. **SSOT 유지**: 보험사 alias는 `config/mappings/insurer_alias.yaml`만 사용
4. **회귀 테스트 추가**: `tests/test_query_normalization.py` (9개 테스트)

### 결과
| 질의 | Before | After |
|------|--------|-------|
| "삼성과 현대 다빈치 수술비를 비교해줘" | INVALID | UNRESOLVED (A9630_1 다빈치로봇암수술비) |
| "삼성 암진단비" | "삼성 암진단비" | "암진단비" |
| "메리츠 뇌졸중진단비 알려줘" | "메리츠 뇌졸중진단비 알려줘" | "뇌졸중진단비" |

### 파일 변경
| 파일 | 변경 내용 |
|------|----------|
| `services/retrieval/compare_service.py` | 하드코딩 제거, YAML 로드 방식으로 변경 |
| `config/rules/query_normalization.yaml` | 신규 - 정규화 규칙 설정 파일 |
| `tests/test_query_normalization.py` | 신규 - 9개 회귀 테스트 |

### 커밋
- `c98ef9c`: fix: normalize_query_for_coverage strips insurer names and intent suffixes
- `941ab2a`: refactor: move query normalization rules to config and remove hardcoding

---

## STEP 3.9: Anchor Persistence / Explicit Coverage Lock (2025-12-20)

### 목표
- 대표 담보가 한 번 확정되면 모든 재질의에서 anchor 고정
- 사용자가 명시적으로 "담보 변경" 버튼을 누르기 전까지 lock 유지
- insurers와 coverage가 절대 흔들리지 않도록 보장

### 검증 시나리오 (A/B/C/D 모두 PASS)

| 시나리오 | 입력 | 기대 결과 | 상태 |
|----------|------|----------|------|
| A | `다빈치 수술비` → 후보 선택 | 🔒 lock UI 표시, locked_coverage_code=A9630_1 | ✅ |
| B | `삼성과 현대의 다빈치로봇암 수술비 비교` | lock 유지, RESOLVED | ✅ |
| C | `현대랑 삼성 다빈치 수술비 알려줘` | anchor 유지 | ✅ |
| D | Evidence/Diff/Slots 탭 전환 | anchor/insurers 불변 | ✅ |

### Backend 검증

```bash
curl -s http://localhost:8000/compare -H "Content-Type: application/json" \
  -d '{"query":"삼성과 현대의 다빈치로봇암 수술비 비교","insurers":["SAMSUNG","HYUNDAI"],"locked_coverage_code":"A9630_1"}'

# 결과:
resolution_state: RESOLVED
primary_coverage_code: A9630_1
recommended (debug): []  # 재추천 없음
anchor: coverage_code=A9630_1 유지
```

### 구현

**Frontend (page.tsx)**:
- `lockedCoverage` state 추가 (code, name)
- `handleSelectCoverage`에서 lock 설정
- `handleUnlockCoverage`로 명시적 unlock
- `handleSendMessage`에서 lockedCoverage 있으면 항상 locked_coverage_code 전달

**Frontend (ChatPanel.tsx)**:
- 🔒 lock UI 표시 (amber 배경 + "담보 변경" 버튼)
- props: lockedCoverage, onUnlockCoverage 추가

**Backend**:
- `locked_coverage_code`가 있으면 coverage resolver 완전 스킵
- resolution_state 항상 RESOLVED

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/app/page.tsx` | lockedCoverage state, handleUnlockCoverage 추가 |
| `apps/web/src/components/ChatPanel.tsx` | 🔒 lock UI + UNLOCK 버튼 |

### 커밋
- `7a4ee05`: feat: STEP 3.9 Anchor Persistence with explicit coverage lock

---

