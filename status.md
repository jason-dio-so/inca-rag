# 보험 약관 비교 RAG 시스템 - 진행 현황

> 최종 업데이트: 2025-12-22 (U-4.18-Ω: All Insurers Coverage Code Backfill)

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
| **STEP 5** | **LLM Assist 도입 (Query Assist + Evidence Summary)** | **기능/UI** | ✅ 완료 |
| **STEP 4.9-β** | **Diff / Compare / Evidence 공통 UX 규약 고정** | **UI** | ✅ 완료 |
| **STEP 4.9-β-1** | **좌/우 독립 스크롤 UX 고정 (Layout Fix)** | **UI** | ✅ 완료 |
| **STEP 4.10** | **Coverage Alias 확장 - 담보명 표준화 보강** | **기능** | ✅ 완료 |
| **STEP 4.10-γ** | **전 보험사 Coverage Alias 전수 검증** | **검증** | ✅ 완료 |
| **U-4.17** | **Compare 탭 NO_COMPARABLE_EVIDENCE 상태 표시** | **기능/UI** | ✅ 완료 |
| **U-4.18** | **Partial Failure & Source Boundary 안정화** | **안정성/UI** | ✅ 완료 |
| **STEP 4.12-γ** | **Subtype 비교 모드 분리 및 Coverage Lock Override** | **기능** | ⚠️ 수정됨 (U-4.18-β) |
| **U-4.18-β** | **Subtype Coverage 종속 원칙 강제** | **기능/UI** | ✅ 완료 |
| **U-4.18-γ** | **Evidence Source Boundary & Anti-Comparison UX** | **UI** | ✅ 완료 |
| **U-4.18-δ** | **Slots Anti-Overreach UX (역할 제한)** | **UI** | ✅ 완료 |
| **U-5.0-A** | **Coverage Name Mapping Table 기반 Resolution** | **아키텍처** | ✅ 완료 |
| **U-4.18-Ω** | **All Insurers Coverage Code Backfill** | **데이터/안정성** | ✅ 완료 |

---

## 🕐 시간순 상세 내역

> Step 1-42 + STEP 2.8~3.9 상세 기록: [status_archive.md](status_archive.md)

## U-4.18-Ω: All Insurers Coverage Code Backfill (2025-12-22)

### 목적
모든 보험사의 비교 가능 문서(가입설계서/상품요약서/사업방법서)에서 coverage_code 태깅 누락 문제를 해결하여 Compare false-negative("근거 부족") 제거

### 문제 분석
- 비교 가능 문서에 담보 관련 텍스트가 존재하는데
- chunk 단위에 `coverage_code`가 태깅되지 않아
- Compare 탭에서 "근거 부족"으로 오인 표시되는 사례 발생

### 작업 내용

**1. 신정원 기준 검증**
- coverage_alias.coverage_code → coverage_standard 매핑 전수 검증
- 모든 284개 alias가 28개 신정원 기준 코드에 정상 매핑 확인

**2. 오염 탐지 및 보완**
- 짧은 alias(6글자 이하)의 과도 매칭 문제 탐지
  - 예: "질병사망"(4글자), "상해수술비"(5글자) 등
- 최소 alias 길이 7글자 필터링 적용 (47개 alias 제외)

**3. Backfill 실행**
- 대상: 8개 보험사, 1,569개 chunk
- 결과: 624개 chunk 태깅 완료 (39.8%)
  - SAMSUNG: 95개 (59.0%)
  - MERITZ: 84개 (28.0%)
  - LOTTE: 135개 (56.3%)
  - KB: 80개 (61.1%)
  - DB: 65개 (40.1%)
  - HANWHA: 73개 (24.3%)
  - HEUNGKUK: 66개 (66.7%)
  - HYUNDAI: 26개 (14.8%)

### 구현

**tools/backfill_comparable_doc_coverage.py**
- coverage_standard 기반 canonical 검증
- 최소 alias 길이 필터링 (MIN_ALIAS_LENGTH=7)
- 보험사별 coverage_alias 기반 매칭
- match_source='backfill_alias' 태깅

### 검증
- Compare API 정상 동작 확인
- SAMSUNG/MERITZ evidence 정상 표시
- false-negative("근거 부족") 해소 확인

### 파일 변경
- `tools/backfill_comparable_doc_coverage.py` (신규)
- `status.md` (업데이트)

---

## U-4.18-β: Subtype Coverage 종속 원칙 강제 (2025-12-22)

### 목적
STEP 4.12-γ의 SUBTYPE_MULTI 독립 상태를 제거하고, Subtype이 Coverage에 종속되도록 원칙 강제

### 문제 분석 (STEP 4.12-γ의 문제)

**As-Is (STEP 4.12-γ 구현)**:
- "경계성 종양 / 제자리암" 질의 → `resolution_state: SUBTYPE_MULTI`
- Subtype이 독립적으로 비교 가능한 것처럼 처리
- Coverage 확정 없이 Subtype 탭 활성화

**To-Be (U-4.18-β 수정)**:
- "경계성 종양 / 제자리암" 질의 → `resolution_state: UNRESOLVED`
- Subtype은 Coverage에 종속된 하위 개념
- Coverage 확정 전에는 어떤 비교 UI도 노출 금지

### 핵심 원칙

1. **Coverage(담보) 확정이 모든 비교의 전제조건**
   - `resolution_state !== "RESOLVED"` → 우측 패널 전체 차단
   - Subtype-only 질의는 상위 담보 없이 비교 불가

2. **Subtype은 Coverage의 하위 개념**
   - 경계성 종양, 제자리암은 "암" 계열의 세부 분류
   - 상위 담보(암진단비 등)가 확정되어야 Subtype 탭 활성화

3. **UNRESOLVED 상태에서 안내 메시지 제공**
   - "담보를 인식하지 못했습니다. 비교를 위해서는 상위 담보(예: 암진단비)를 함께 입력해 주세요."
   - 암 도메인 대표 담보 추천 (암진단비, 유사암진단비, 재진단암진단비)

### 구현

**1. Backend: SUBTYPE_MULTI 제거**

`api/compare.py`:
```python
# CoverageResolutionResponse
status: Literal["RESOLVED", "UNRESOLVED", "INVALID"]  # SUBTYPE_MULTI 제거

# 멀티 Subtype 질의 처리
if is_multi_subtype:
    coverage_resolution = CoverageResolutionResponse(
        status="UNRESOLVED",  # SUBTYPE_MULTI → UNRESOLVED
        message="담보를 인식하지 못했습니다. 비교를 위해서는 상위 담보(예: 암진단비)를 함께 입력해 주세요.",
        suggested_coverages=cancer_domain_coverages,
    )
```

**2. Frontend: SUBTYPE_MULTI 핸들링 제거**

`ResultsPanel.tsx`:
```typescript
// 이전: if (resolutionState !== "RESOLVED" && !isSubtypeMulti)
// 수정:
if (resolutionState !== "RESOLVED") {
  // 모든 비교 UI 차단
}
```

**3. Subtype 탭 조건**

```typescript
// RESOLVED 상태에서만 Subtype 탭 표시
{response.subtype_comparison?.is_multi_subtype && (
  <TabsTrigger value="subtype">Subtype</TabsTrigger>
)}
```

### 설정 변경

`config/rules/coverage_resolution.yaml`:
```yaml
failure_messages:
  subtype_needs_coverage: "담보를 인식하지 못했습니다. 비교를 위해서는 상위 담보(예: 암진단비)를 함께 입력해 주세요."
```

### 검증 결과

| 테스트 | 입력 | 결과 |
|--------|------|------|
| Subtype-only 질의 | "경계성 종양 / 제자리암" | resolution_state: UNRESOLVED ✅ |
| 메시지 확인 | 위와 동일 | "담보를 인식하지 못했습니다..." ✅ |
| 추천 담보 | 위와 동일 | 암진단비, 유사암진단비, 재진단암진단비 ✅ |
| 정상 담보 질의 + lock | "암진단비" + locked | resolution_state: RESOLVED ✅ |

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `api/compare.py` | SUBTYPE_MULTI 제거, Subtype-only → UNRESOLVED |
| `config/rules/coverage_resolution.yaml` | subtype_needs_coverage 메시지 추가 |
| `apps/web/src/lib/ui-gating.config.ts` | SUBTYPE_MULTI 제거, RESOLVED만 허용 |
| `apps/web/src/lib/types.ts` | resolution_state에서 SUBTYPE_MULTI 제거 |
| `apps/web/src/components/ResultsPanel.tsx` | isSubtypeMulti 핸들링 제거, RESOLVED 게이트 강화 |

### DoD 체크리스트
- [x] SUBTYPE_MULTI 상태 제거 (Backend)
- [x] Subtype-only 질의 → UNRESOLVED 반환
- [x] UNRESOLVED 메시지에 상위 담보 안내 포함
- [x] Frontend에서 RESOLVED 외 모든 상태 UI 차단
- [x] Subtype 탭은 RESOLVED + is_multi_subtype일 때만 활성화
- [x] Docker 재빌드 및 테스트 통과

---

## U-4.18-γ: Evidence Source Boundary & Anti-Comparison UX (2025-12-22)

### 목적
Evidence 탭이 "비교 결과"로 오인되지 않도록 시각적 경계 강화 및 Anti-Comparison UX 적용

### 핵심 원칙

1. **Evidence ≠ Compare**
   - Evidence는 "근거 목록 열람" 용도
   - 비교/판단은 Compare 탭에서만 수행
   - Evidence에서 금액 비교 유도 금지

2. **Source Level 시각화**
   - 모든 Evidence 항목에 source_level 배지 표시
   - COMPARABLE_DOC: 가입설계서, 상품요약서, 사업방법서 (비교 가능 문서)
   - POLICY_ONLY: 약관 (참조용)
   - UNKNOWN: 출처 불명

3. **Anti-Comparison UX**
   - 좌/우 배치 금지 (수직 리스트만 허용)
   - 금액 강조(bold) 금지
   - 보험사 간 교차참조 금지
   - Score 표시 제거

### 구현

**1. Source Level 배지**

`EvidencePanel.tsx`:
```typescript
type SourceLevel = "COMPARABLE_DOC" | "POLICY_ONLY" | "UNKNOWN";

const SOURCE_LEVEL_CONFIG: Record<SourceLevel, {...}> = {
  COMPARABLE_DOC: { label: "비교 문서 근거", bgColor: "bg-blue-50", ... },
  POLICY_ONLY: { label: "약관 근거", bgColor: "bg-amber-50", ... },
  UNKNOWN: { label: "출처 불명", bgColor: "bg-gray-50", ... },
};

function getSourceLevel(docType: string): SourceLevel {
  const comparableDocs = ["가입설계서", "상품요약서", "사업방법서"];
  if (comparableDocs.includes(docType)) return "COMPARABLE_DOC";
  if (docType === "약관") return "POLICY_ONLY";
  return "UNKNOWN";
}
```

**2. 고정 경고 배너**

```typescript
<div className="mb-4 p-4 bg-amber-50 border-2 border-amber-300 rounded-lg sticky top-0 z-10">
  <AlertTriangle className="h-5 w-5 text-amber-600" />
  <p className="font-semibold">⚠️ 이 화면은 비교 결과가 아닙니다.</p>
  <p>Evidence는 각 보험사의 관련 문서에서 발췌된 '근거 목록'...</p>
</div>
```

**3. Anti-Comparison UX**
- Score 표시 제거 (opacity 및 텍스트 삭제)
- 금액 부분 일반 텍스트 처리 (강조 제거)
- 수직 리스트 레이아웃 유지

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/components/EvidencePanel.tsx` | source_level 배지, 경고 배너, Anti-Comparison UX |

### DoD 체크리스트
- [x] source_level 배지 구현 (COMPARABLE_DOC, POLICY_ONLY, UNKNOWN)
- [x] 고정 경고 배너 추가 (닫기 불가)
- [x] Score 표시 제거
- [x] Docker 재빌드 성공
- [x] status.md 업데이트

---

## U-4.18-δ: Slots Anti-Overreach UX (2025-12-22)

### 목적
Slots 탭이 Evidence 역할을 침범하지 않도록 역할 제한 강화

### 핵심 원칙

1. **Slots 역할 제한**
   - 비교 항목의 존재 여부
   - 정량 값 (금액, 횟수 등)
   - 차이 발생 사실 요약

2. **Slots 금지 사항**
   - 조건 상세 나열 ❌
   - 예외 조항 설명 ❌
   - 약관 문구 직접 인용 ❌
   - Evidence 요약/재서술 ❌

3. **길이 제한**
   - 최대 120자 또는 2줄
   - 초과 시: "일부 조건 요약 (자세한 내용은 Evidence에서 확인)"

### 구현

**1. Overreach 탐지 및 차단**

`SlotsTable.tsx`:
```typescript
function truncateSlotValue(value: string | null): { text: string; truncated: boolean } {
  // 조항 번호, 복수 숫자, 상세 조건 패턴 탐지
  const hasArticleNumber = /제\s*\d+\s*조|조항|약관/i.test(value);
  const multipleNumbers = (value.match(/\d+/g) || []).length >= 3;
  const hasDetailedCondition = /계약일로부터|경과\s*시|소액암|50%|90일/i.test(value);

  if (hasArticleNumber || multipleNumbers || hasDetailedCondition || value.length > 120) {
    return { text: SLOT_OVERFLOW_FALLBACK, truncated: true };
  }
  return { text: value, truncated: false };
}
```

**2. Source Hint 표시**

```typescript
function SourceHint({ sourceLevel }: { sourceLevel?: string }) {
  const label = SOURCE_HINT_LABELS[level] || "근거 부족";
  return <span className="text-[10px] text-muted-foreground">({label})</span>;
}
```

**3. Evidence 유도 안내 (Slots 하단)**

```typescript
<div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
  ※ Slots는 비교를 위한 요약 정보입니다.
  세부 조건 및 근거 문구는 Evidence 탭에서 확인하세요.
</div>
```

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `apps/web/src/components/SlotsTable.tsx` | truncateSlotValue(), SourceHint, Evidence 유도 안내 |

### DoD 체크리스트
- [x] Slots에서 상세 조건 해석 불가
- [x] 120자/2줄 초과 시 자동 치환
- [x] Source Hint 표시 (비교 문서 기준/약관 기준/근거 부족)
- [x] Evidence 유도 안내 문구 추가
- [x] Build 성공

---

## U-5.0-A: Coverage Name Mapping Table 기반 Resolution (2025-12-22)

### 목적
Coverage Resolution을 코드 하드코딩에서 DB 테이블(coverage_name_map) 기반으로 전환하여 Single Source of Truth 확립

### 핵심 원칙

1. **테이블 우선 Resolution**
   - Coverage Resolution은 coverage_alias + coverage_standard 테이블 조회 우선
   - LLM/rule은 보조 수단 (테이블에 없을 때만 사용)

2. **Subtype은 coverage_code에 종속**
   - Subtype 판단은 coverage_code 확정 후에만 가능
   - coverage_code 없이 Subtype만 질의 → UNRESOLVED

3. **combined_score = similarity × confidence**
   - 매칭 신뢰도(confidence) × 유사도(similarity)로 최종 순위 결정
   - 동일 유사도라도 confidence가 높은 alias 우선

### 스키마 변경

**1. coverage_standard 테이블 확장**

```sql
ALTER TABLE coverage_standard
ADD COLUMN IF NOT EXISTS semantic_scope TEXT DEFAULT 'UNKNOWN';
-- CANCER, CARDIO, SURGERY, INJURY, DEATH, UNKNOWN
```

**2. coverage_alias 테이블 확장**

```sql
ALTER TABLE coverage_alias
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT false;
ADD COLUMN IF NOT EXISTS confidence NUMERIC(3,2) DEFAULT 0.8;
-- confidence: 1.0 (신정원), 0.95 (상품요약서), 0.85 (사업방법서), 0.7 (약관)
```

**3. coverage_name_map 뷰 생성**

```sql
CREATE OR REPLACE VIEW coverage_name_map AS
SELECT
    i.insurer_code,
    ca.raw_name AS insurer_coverage_name,
    cs.coverage_name AS standard_coverage_name,
    ca.coverage_code,
    cs.semantic_scope,
    ca.is_primary,
    ca.confidence,
    ca.source_doc_type AS source
FROM coverage_alias ca
JOIN insurer i ON ca.insurer_id = i.insurer_id
JOIN coverage_standard cs ON ca.coverage_code = cs.coverage_code;
```

### 구현

**1. CoverageRecommendation 확장**

`services/retrieval/compare_service.py`:
```python
@dataclass
class CoverageRecommendation:
    insurer_code: str
    coverage_code: str
    coverage_name: str | None
    raw_name: str
    source_doc_type: str
    similarity: float
    confidence: float = 0.8       # U-5.0-A
    semantic_scope: str = "UNKNOWN"  # U-5.0-A
    combined_score: float = 0.0   # U-5.0-A: similarity × confidence
```

**2. recommend_coverage_codes() SQL 수정**

```sql
SELECT
    i.insurer_code,
    ca.coverage_code,
    cs.coverage_name,
    ca.raw_name,
    ca.source_doc_type,
    1 - (ca.embedding <=> %s) AS similarity,
    COALESCE(ca.confidence, 0.8) AS confidence,
    COALESCE(cs.semantic_scope, 'UNKNOWN') AS semantic_scope,
    (1 - (ca.embedding <=> %s)) * COALESCE(ca.confidence, 0.8) AS combined_score
FROM coverage_alias ca
...
ORDER BY combined_score DESC
```

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `db/migrations/005_coverage_name_map_enhancement.sql` | 마이그레이션 SQL (스키마 확장 + 뷰 생성) |
| `db/schema.sql` | coverage_standard, coverage_alias 컬럼 추가, coverage_name_map 뷰 |
| `services/retrieval/compare_service.py` | CoverageRecommendation 확장, combined_score 기반 정렬 |

### 검증 결과

| 테스트 | 결과 |
|--------|------|
| 마이그레이션 적용 | ✅ 성공 (28 coverage_standard, 284 coverage_alias) |
| semantic_scope 초기화 | ✅ CANCER 7건, CARDIO 7건, INJURY 3건, SURGERY 2건, DEATH 2건 |
| confidence 초기화 | ✅ 1.0 (279건), 0.7 (5건) |
| API 테스트 (UNRESOLVED) | ✅ similarity < threshold → UNRESOLVED |
| API 테스트 (RESOLVED) | ✅ locked_coverage_codes 전달 → RESOLVED |

### DoD 체크리스트
- [x] coverage_standard에 semantic_scope 컬럼 추가
- [x] coverage_alias에 is_primary, confidence 컬럼 추가
- [x] coverage_name_map 뷰 생성
- [x] combined_score = similarity × confidence 기반 정렬
- [x] 마이그레이션 적용 및 검증
- [x] API 정상 동작 확인

---

## STEP 4.12-γ: Subtype 비교 모드 분리 및 Coverage Lock Override (2025-12-22)

> ⚠️ **이 구현은 U-4.18-β에서 수정됨**: SUBTYPE_MULTI 독립 상태 제거

### 목적
"경계성 종양/제자리암" Subtype 비교가 암진단비(A4200_1)로 자동 고정되어 금액 슬롯이 나오는 현상 차단

### 문제 분석

**As-Is (문제 상황)**:
- 사용자가 "경계성 종양 / 제자리암" 비교를 요청
- 시스템이 암진단비(유사암 제외) A4200_1로 자동 coverage lock
- 결과: payout_amount 금액 비교 슬롯이 생성됨
- 실제로 원하는 것: 유사암 포함/제외, 지급비율, 정의/판정문구 비교

**To-Be (수정 후)**:
- Subtype 질의는 `comparison_mode = "SUBTYPE"`로 강제
- Coverage lock이 있어도 subtype_intent가 감지되면 lock override
- payout_amount 등 금액 슬롯 생성 금지
- 정의/조건 중심의 비교 결과 제공

### 핵심 원칙

1. **Subtype 질의는 Coverage Lock보다 우선한다**
   - locked_coverage_codes가 있어도 subtype_intent 감지 시 무시

2. **Subtype 모드에서 금액 슬롯 생성 금지**
   - payout_amount, diagnosis_lump_sum_amount 등 suppressed_slots_in_subtype 필터링

3. **comparison_mode 필드로 모드 구분**
   - "COVERAGE": 기존 금액 비교 모드
   - "SUBTYPE": 유사암/제자리암 정의 비교 모드

### 구현

**1. Subtype Intent Detection**

`api/compare.py`:
```python
def _detect_subtype_intent(
    query: str,
    ui_event_type: str | None = None,
    request_subtype_targets: list[str] | None = None,
) -> tuple[bool, list[str], str]:
    # 1. UI 이벤트 기반 트리거 (SUBTYPE_QUERY)
    # 2. Request에서 명시적 subtype_targets 전달
    # 3. Keyword 기반 트리거 (subtype_config.yaml 사용)
```

**2. Coverage Lock Override**

```python
# Subtype 모드에서는 coverage lock 강제 해제
if is_subtype_intent and effective_locked_codes:
    anchor_debug["previous_locked_codes"] = effective_locked_codes
    anchor_debug["coverage_lock_overridden"] = True
    effective_locked_codes = None  # Lock 해제
```

**3. Response Contract 변경**

```python
class CompareResponseModel(BaseModel):
    # STEP 4.12-γ: Comparison Mode
    comparison_mode: Literal["COVERAGE", "SUBTYPE"] = "COVERAGE"
    subtype_targets: list[str] | None = None
```

**4. Slot Suppression**

```python
if is_subtype_intent:
    suppressed_slot_keys = get_suppressed_slots_in_subtype()
    final_slots = [
        slot for slot in converted_slots
        if slot.slot_key not in suppressed_slot_keys
    ]
```

**5. User Summary 변경**

Subtype 모드에서는 금액 비교 문구 대신:
```
"{보험사}의 {subtype} 보장 여부 및 감액 기준을 비교했습니다.
금액 비교가 아닌 정의/조건 중심의 비교입니다."
```

### 설정 파일

**config/subtype_config.yaml**:
```yaml
subtype_keyword_map:
  경계성: borderline
  경계성종양: borderline
  제자리암: in_situ
  상피내암: in_situ
  유사암: similar_cancer
  소액암: minor_cancer

suppressed_slots_in_subtype:
  - payout_amount
  - diagnosis_lump_sum_amount
  - payout_condition_summary

subtype_display_names:
  borderline: 경계성종양
  in_situ: 제자리암(상피내암)
  similar_cancer: 유사암
  minor_cancer: 소액암
```

### 검증 결과

| 테스트 | 입력 | 결과 |
|--------|------|------|
| Keyword trigger | "경계성 종양 제자리암 비교" | is_intent=True, targets=[borderline, in_situ] ✅ |
| UI event trigger | ui_event_type="SUBTYPE_QUERY" | is_intent=True, trigger="ui_event" ✅ |
| Normal query | "암진단비 비교" | is_intent=False, trigger="none" ✅ |

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `api/compare.py` | _detect_subtype_intent() 추가, coverage lock override, comparison_mode 필드 |
| `api/config_loader.py` | get_subtype_keyword_map(), get_suppressed_slots_in_subtype() 추가 |
| `config/subtype_config.yaml` | subtype 설정 (keyword_map, suppressed_slots, display_names) |

### DoD 체크리스트
- [x] subtype 키워드/ui_event로 들어온 요청은 comparison_mode="SUBTYPE"
- [x] Subtype 모드에서 payout_amount 슬롯 생성 억제
- [x] Subtype 모드에서 coverage lock override
- [x] user_summary에 금액 비교 문구 없음
- [x] 회귀: 일반 "암진단비(유사암 제외)" 비교는 기존과 동일

---

## U-4.18: Partial Failure & Source Boundary 안정화 (2025-12-22)

### 목적
1. Partial Failure를 사용자에게 안전하게 격리
2. Slot/Compare 결과의 출처 경계(source_level)를 명시적으로 고정
3. "보여주면 안 되는 상태"를 절대 화면에 노출하지 않도록 차단

### 핵심 원칙

1. **Partial Failure는 "결과"가 아니다**
   - API 실패 시 부분 결과 표시 금지
   - 명시적 상태 UI로 전환

2. **Source는 절대 섞이지 않는다**
   - `source_level`: COMPARABLE_DOC | POLICY_ONLY | UNKNOWN
   - MIXED 상태 금지, source_level 없는 결과 렌더링 금지

3. **Compare 탭은 COMPARABLE_DOC 전용**
   - 약관 기반 정의/해석 비교 금지
   - source_level ≠ COMPARABLE_DOC → "비교 불가" 표시

### 구현

**1. Backend: source_level 필드 추가**

`services/retrieval/compare_service.py`:
```python
@dataclass
class InsurerCompareCell:
    # ...
    source_level: str = "UNKNOWN"  # "COMPARABLE_DOC" | "POLICY_ONLY" | "UNKNOWN"
```

`services/extraction/slot_extractor.py`:
```python
@dataclass
class SlotInsurerValue:
    # ...
    source_level: Literal["COMPARABLE_DOC", "POLICY_ONLY", "UNKNOWN"] = "UNKNOWN"
```

**2. Frontend: Global API Health Gate**

`apps/web/src/app/page.tsx`:
```typescript
const [apiHealth, setApiHealth] = useState<{
  isHealthy: boolean;
  errorMessage: string | null;
}>({ isHealthy: true, errorMessage: null });

// API 실패 시 결과 표시 차단
{!apiHealth.isHealthy ? (
  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
    <h3>일부 데이터를 불러오지 못했습니다</h3>
    <p>비교 결과의 신뢰성을 보장할 수 없어 표시를 중단합니다.</p>
  </div>
) : (
  <ResultsPanel ... />
)}
```

**3. Frontend: Compare 탭 source_level 렌더링**

`apps/web/src/components/CompareTable.tsx`:
```typescript
if (sourceLevel === "POLICY_ONLY") {
  return <td>비교 불가 (동일 기준 문서 없음)</td>;
}
if (sourceLevel === "UNKNOWN") {
  return <td>근거 부족</td>;
}
// COMPARABLE_DOC만 정상 표시
```

**4. Frontend: Slots 탭 source_level 렌더링**

`apps/web/src/components/SlotsTable.tsx`:
```typescript
function SourceLevelBadge({ sourceLevel }) {
  if (sourceLevel === "POLICY_ONLY") {
    return <Badge>⚠️ 약관 기준</Badge>;
  }
  return null;
}
```

**5. API Error Message 정제**

`apps/web/src/lib/api.ts`:
```typescript
function sanitizeErrorMessage(message: string): string {
  if (message.includes("<html") || message.includes("<!DOCTYPE")) {
    return "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
  }
  return message.replace(/<[^>]*>/g, "").trim();
}
```

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `services/retrieval/compare_service.py` | InsurerCompareCell에 source_level 추가 |
| `services/extraction/slot_extractor.py` | SlotInsurerValue에 source_level 추가 |
| `api/compare.py` | InsurerCompareCellResponse, SlotInsurerValueResponse에 source_level 추가 |
| `apps/web/src/app/page.tsx` | Global API Health Gate 구현 |
| `apps/web/src/lib/api.ts` | Error message sanitization |
| `apps/web/src/components/CompareTable.tsx` | source_level 기반 렌더링 |
| `apps/web/src/components/SlotsTable.tsx` | source_level 배지 표시 |

### DoD 체크리스트
- [x] API 실패 시 "보여주면 안 되는 상태" 노출 없음
- [x] source_level 없는 결과 없음 (기본값 UNKNOWN)
- [x] Compare 탭은 COMPARABLE_DOC 전용
- [x] 약관 기반 정보는 명확히 분리됨 (POLICY_ONLY 배지)
- [x] HTML 에러 메시지 직접 노출 차단

---

## U-4.17: Compare 탭 NO_COMPARABLE_EVIDENCE 상태 표시 (2025-12-22)

### 목적
Compare 탭에서 특정 보험사가 비교 가능 문서(가입설계서/상품요약서/사업방법서)가 없고 약관만 있는 경우 이를 명시적으로 표시

### 문제 분석

**As-Is (문제 상황)**:
- Summary 탭에서는 삼성 데이터가 정상 표시됨
- Compare 탭에서는 삼성 컬럼이 비어 있음 (왜 비었는지 설명 없음)
- 원인: A2 정책에 의해 약관 데이터는 Compare 탭에서 필터링됨

**To-Be (수정 후)**:
- Compare 탭에서 비교 가능 문서가 없는 경우 "비교 가능한 자료 없음 (약관만 존재)" 문구 표시
- 컬럼을 삭제하지 않고 상태 설명 제공

### 구현

**1. Backend: compare_status 필드 추가**

`services/retrieval/compare_service.py`:
```python
@dataclass
class InsurerCompareCell:
    insurer_code: str
    doc_type_counts: dict[str, int] = field(default_factory=dict)
    best_evidence: list[Evidence] = field(default_factory=list)
    resolved_amount: ResolvedAmount | None = None
    # U-4.17: 비교 가능 상태
    compare_status: str = "COMPARABLE"  # "COMPARABLE" | "NO_COMPARABLE_EVIDENCE"
```

**2. Backend: compare_status 판정 로직**

```python
# best_evidence가 비어있지만 약관에 데이터가 있으면 NO_COMPARABLE_EVIDENCE
compare_status = "COMPARABLE"
if not best_evidence:
    has_policy_evidence = "약관" in evidence_by_doc_type
    if has_policy_evidence:
        compare_status = "NO_COMPARABLE_EVIDENCE"
```

**3. API: InsurerCompareCellResponse 확장**

`api/compare.py`:
```python
class InsurerCompareCellResponse(BaseModel):
    insurer_code: str
    doc_type_counts: dict[str, int]
    best_evidence: list[EvidenceResponse]
    compare_status: str = "COMPARABLE"  # U-4.17
```

**4. Frontend: CompareTable.tsx 렌더링 분기**

```typescript
// U-4.17: NO_COMPARABLE_EVIDENCE 상태 처리
const compareStatus = (insurerData as any).compare_status as string | undefined;
if (compareStatus === "NO_COMPARABLE_EVIDENCE") {
  return (
    <td key={insurer} className="p-3 text-center">
      <div className="text-sm text-amber-600 bg-amber-50 rounded px-2 py-1">
        비교 가능한 자료 없음
        <br />
        <span className="text-xs text-muted-foreground">(약관만 존재)</span>
      </div>
    </td>
  );
}
```

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `services/retrieval/compare_service.py` | InsurerCompareCell에 compare_status 필드 추가, 판정 로직 구현 |
| `api/compare.py` | InsurerCompareCellResponse에 compare_status 필드 추가 |
| `apps/web/src/components/CompareTable.tsx` | NO_COMPARABLE_EVIDENCE 상태 UI 렌더링 |

### DoD 체크리스트
- [x] compare_status 필드 Backend 추가
- [x] API 응답에 compare_status 포함
- [x] Frontend에서 NO_COMPARABLE_EVIDENCE 상태 렌더링
- [x] Docker 컨테이너 재빌드 및 테스트
- [x] status.md 업데이트

---

## STEP 4.10-γ: 전 보험사 Coverage Alias 전수 검증 (2025-12-21)

### 목적
모든 보험사에 대해 A9630_1(다빈치로봇암수술비) 담보의 axis 생성 가능 여부 검증

### 1차 검증 결과

| insurer_code | axis_len | result | 비고 |
|--------------|----------|--------|------|
| DB | 8 | ✅ GREEN | - |
| HANWHA | 4 | ✅ GREEN | - |
| HEUNGKUK | 0 | ❌ RED | alias suffix 불일치 |
| HYUNDAI | 10 | ✅ GREEN | - |
| KB | 0 | ❌ RED | alias suffix 불일치 |
| LOTTE | 4 | ✅ GREEN | - |
| MERITZ | 10 | ✅ GREEN | - |
| SAMSUNG | 0 | ❌ RED | alias prefix/공백 불일치 |

### RED 케이스 원인 분석

| 보험사 | 기존 alias | chunk 실제 표현 | 원인 |
|--------|-----------|----------------|------|
| HEUNGKUK | `(갱신형_10년)` suffix | suffix 없음 | alias 너무 구체적 |
| KB | `【갱신계약】` suffix | suffix 없음 | alias 너무 구체적 |
| SAMSUNG | `[갱신형]` prefix | prefix 없음 | alias prefix 불일치 |

### alias 보강

| 보험사 | 추가 alias 수 | 대표 예시 |
|--------|--------------|----------|
| HEUNGKUK | +5건 | `다빈치및레보아이로봇 암수술비(갑상선암 및 전립선암 제외)` |
| KB | +5건 | `다빈치로봇 암수술비(갑상선암 및 전립선암 제외)` |
| SAMSUNG | +5건 | `다빈치로봇 수술비(1년감액)` |

### 2차 검증 결과 (보강 후)

| insurer_code | axis_len | result | doc_type_counts |
|--------------|----------|--------|-----------------|
| DB | 8 | ✅ GREEN | 가입설계서:4, 상품요약서:2, 사업방법서:2 |
| HANWHA | 4 | ✅ GREEN | 사업방법서:3, 상품요약서:1 |
| HEUNGKUK | 10 | ✅ GREEN | 가입설계서:6, 상품요약서:3, 사업방법서:1 |
| HYUNDAI | 10 | ✅ GREEN | 가입설계서:4, 상품요약서:6 |
| KB | 10 | ✅ GREEN | 가입설계서:6, 상품요약서:4 |
| LOTTE | 4 | ✅ GREEN | 가입설계서:4 |
| MERITZ | 10 | ✅ GREEN | 가입설계서:2, 상품요약서:3, 사업방법서:5 |
| SAMSUNG | 10 | ✅ GREEN | 가입설계서:5, 상품요약서:5 |

### 결론
- **8개 보험사 전체 GREEN**
- alias_text_match 전략으로 모든 보험사에서 axis 생성 성공
- A9630_1 총 alias: 34건 (기존 19건 + 추가 15건)

### DoD 체크리스트
- [x] 모든 insurer_code에 대해 GREEN 분류 완료
- [x] RED 케이스 3건 alias 보강
- [x] 보강 후 전체 GREEN 확인
- [x] coverage_locked == true 확인
- [x] __amount_fallback__ 노출 없음 확인
- [x] audit 문서 생성

### 산출물
- Audit 문서: `docs/audit/step_4_10_gamma_all_insurer_axis_audit.md`

---

## STEP 4.10: Coverage Alias 확장 - 담보명 표준화 보강 (2025-12-21)

### 목적
보험사별 담보명 불일치로 인한 False Negative (미보장 오판) 해결

### 문제점 (As-Is)
- 질의: "현대해상, DB손해보험의 다빈치로봇암수술비 비교"
- 시스템 응답: ❌ "현대해상은(는) 해당 담보가 확인되지 않습니다"
- 약관 기준 실제: ✅ 현대해상 보장 (로봇암수술 - 다빈치/레보아이)

### 원인 분석
| 보험사 | 약관상 담보명 |
|------|-------------|
| DB손해보험 | 다빈치로봇암수술비 |
| 현대해상 | 로봇암수술(다빈치및레보아이) |

- coverage_alias에 현대해상 표현 누락
- chunk 검색 시 coverage_code 태그가 아닌 담보명 텍스트 매칭 필요

### 해결 (To-Be)
1. **compare_axis 검색 로직 확장 (STEP 4.10 핵심)**
   - 기존: `chunk.meta->entities->coverage_code` 태그 기반 검색 → 결과 없음
   - 확장: `coverage_alias.raw_name`을 사용한 content ILIKE 텍스트 매칭

2. **coverage_alias 확장**
   - HYUNDAI A9630_1 alias 5건 추가:
     - 로봇암수술(다빈치및레보아이)(연간1회한)(갱신형)담보
     - 로봇암수술(다빈치및레보아이)(연간1회한)
     - 다빈치로봇암수술
     - 레보아이로봇암수술
     - 등

3. **coverage_standard 명칭 표준화**
   - A9630_1: "다빈치로봇암수술비" → "로봇/다빈치 암수술비"

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `services/retrieval/compare_service.py` | get_compare_axis() alias 기반 ILIKE 검색 로직 추가 |
| DB: coverage_alias | HYUNDAI A9630_1 alias 5건 추가 |
| DB: coverage_standard | A9630_1 coverage_name 표준화 |

### 검증 결과

| 시나리오 | 이전 | 이후 |
|----------|------|------|
| DB+HYUNDAI 다빈치로봇암수술비 | ❌ HYUNDAI 미보장 | ✅ 모든 보험사 보장 |
| compare_axis counts (HYUNDAI) | 0건 | 12건 |
| A9630_1 evidence | 없음 | 10건 |

### DoD 체크리스트
- [x] coverage_alias에 현대해상 표현 추가
- [x] 동일 질의에서 현대해상 보장 판정 성공
- [x] 기존 삼성/한화/롯데 결과 영향 없음
- [x] status.md STEP 4.10 완료 반영
- [x] 관련 커밋 생성

---






