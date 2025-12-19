# 보험 약관 비교 RAG 시스템 - 진행 현황

> 최종 업데이트: 2025-12-19

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

---

## 🕐 시간순 상세 내역

> Step 1-20 상세 기록: [status_archive.md](status_archive.md)

### 21. Step H-1.8: Amount source policy (가입설계서 amount 신뢰도 제한) [기능]

**목표:**
- 가입설계서의 구조적 오탐 문제를 우회하여 사용자에게 노출되는 금액 정확도 향상
- 금액은 상품요약서/사업방법서 중심으로 제공하고, 가입설계서는 보조로 전환

**구현 내용:**
1. `ResolvedAmount` dataclass 추가:
   - `amount_value`, `amount_text`, `unit`, `confidence`
   - `source_doc_type`: 금액이 선택된 doc_type
   - `source_document_id`: 원본 document ID

2. `amount_source_priority` 정책:
   - 우선순위: 상품요약서 > 사업방법서 > 가입설계서
   - 상위 우선순위 doc_type에 유효한 금액이 있으면 해당 금액 선택

3. 가입설계서 confidence 제한:
   - `doc_type=='가입설계서' AND confidence=='low'` → 제외
   - `confidence=='high'` 또는 `'medium'` → 선택 가능

4. `InsurerCompareCell`에 `resolved_amount` 필드 추가:
   - 각 보험사 셀에 대표 금액 1개만 노출
   - `best_evidence`의 개별 amount는 기존대로 유지 (상세 정보)

**수정된 파일:**
| 파일 | 설명 |
|------|------|
| `services/retrieval/compare_service.py` | ResolvedAmount, amount_source_priority 로직 |
| `tests/test_amount_source_policy.py` | 단위 테스트 10개 |

**API 응답 변경:**
```json
{
  "coverage_compare_result": [{
    "insurers": [{
      "insurer_code": "SAMSUNG",
      "resolved_amount": {
        "amount_value": 10000000,
        "amount_text": "1,000만원",
        "unit": "만원",
        "confidence": "high",
        "source_doc_type": "상품요약서",
        "source_document_id": 123
      },
      "best_evidence": [...]
    }]
  }]
}
```

**추가된 테스트 (10개):**
| 테스트 | 설명 |
|--------|------|
| `test_상품요약서_우선_선택` | 상품요약서 > 가입설계서 우선순위 |
| `test_사업방법서_가입설계서보다_우선` | 사업방법서 > 가입설계서 우선순위 |
| `test_가입설계서_low_confidence_제외` | confidence='low' 제외 |
| `test_가입설계서_high_confidence_선택` | confidence='high' 선택 |
| `test_모든_amount_none이면_resolved_amount도_none` | 전부 None이면 None |
| `test_빈_evidence_리스트` | 빈 리스트 처리 |
| `test_상품요약서_사업방법서_가입설계서_전체_우선순위` | 3개 doc_type 우선순위 |
| `test_상품요약서_amount_none이면_사업방법서_선택` | fallback 동작 |
| `test_가입설계서_medium_confidence_선택` | medium 허용 |
| `test_약관_doc_type은_amount_없음` | 약관 제외 확인 |

**pytest 결과:**
```
97 passed in 18.09s
```

**효과:**
- 가입설계서의 구조적 오탐(보험료 vs 보험금 혼동) 문제를 정책으로 우회
- 사용자에게 노출되는 `resolved_amount`는 신뢰도 높은 상품요약서/사업방법서 우선
- `best_evidence`에는 모든 doc_type의 amount가 그대로 유지 (상세 분석용)
- 회귀 없음: 기존 87 + 신규 10 = 97 tests 모두 PASS

---

### 22. Step H-2: LLM 정밀 추출 (선별 적용) [기능]

**목표:**
- H-1.8 정책으로 resolved_amount가 비어있는 셀에 대해 LLM으로 보강
- 선별 호출: 필요한 케이스만 (비용/속도/환각 최소화)
- 근거(span) 필수: 환각 방지

**적용 범위 (선별 조건):**
모든 조건 충족 시에만 LLM 호출:
1. `resolved_amount.amount_value is None`
2. `best_evidence` 중 `doc_type=='가입설계서'` evidence 존재
3. `evidence.amount.confidence in ('low', 'medium')` OR `amount is None`
4. `query`가 금액 의도 포함 (얼마, 한도, 금액, 지급 등)

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `services/extraction/llm_schemas.py` | Pydantic 모델 (LLMExtractResult 등) |
| `services/extraction/llm_prompts.py` | System/User 프롬프트 템플릿 |
| `services/extraction/llm_client.py` | LLMClient 프로토콜 + Fake/Disabled 클라이언트 |
| `tests/test_llm_refinement.py` | 단위 테스트 17개 |

**핵심 스키마:**
```python
class LLMAmount(BaseModel):
    label: Literal["benefit_amount", "premium_amount", "unknown"]
    amount_value: int | None
    amount_text: str | None
    unit: str | None
    confidence: Literal["high", "medium", "low"]
    span: LLMSpan | None  # 근거 span (환각 방지)
```

**업그레이드 조건:**
1. `label == "benefit_amount"` (보험료 차단)
2. `confidence in ("high", "medium")` (low 제외)
3. `span.text`가 chunk_text에 실제로 포함됨 (환각 방지)

**안전장치:**
- `premium_amount`는 절대 resolved_amount로 승격 금지
- span 검증: LLM이 준 span.text가 원문에 없으면 결과 폐기
- 호출 제한: `LLM_MAX_CALLS_PER_REQUEST` (기본 8)
- 예외 발생 시 요청 전체 200 유지 + debug에만 기록

**환경변수:**
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `LLM_ENABLED` | 0 | LLM 활성화 여부 |
| `LLM_MAX_CALLS_PER_REQUEST` | 8 | 요청당 최대 호출 횟수 |
| `LLM_PROVIDER` | openai | LLM 제공자 (추후) |
| `LLM_MODEL` | gpt-4o-mini | LLM 모델 (추후) |

**테스트 케이스 (17개):**
| 테스트 | 설명 |
|--------|------|
| `test_resolved_amount_already_exists_no_call` | resolved_amount 있으면 호출 0회 |
| `test_no_enrollment_evidence_no_call` | 가입설계서 없으면 호출 0회 |
| `test_enrollment_confidence_high_no_call` | confidence high이면 호출 0회 |
| `test_no_amount_intent_no_call` | 금액 의도 없으면 호출 0회 |
| `test_premium_amount_no_upgrade` | premium_amount → 업그레이드 금지 |
| `test_benefit_amount_medium_upgrade` | benefit_amount + medium → 업그레이드 |
| `test_benefit_amount_low_no_upgrade` | benefit_amount + low → 업그레이드 금지 |
| `test_span_not_in_text_discard` | span 환각 → 결과 폐기 |
| `test_max_calls_limit` | 호출 제한 검증 |
| `test_llm_disabled_no_crash` | LLM disabled → 200 유지 |
| `test_약관_evidence_not_processed` | A2 정책 유지 |

**pytest 결과:**
```
114 passed in 18.13s
```

**효과:**
- LLM_ENABLED=0 상태에서도 100% 테스트 통과
- FakeLLMClient로 CI 환경에서 안정적 테스트
- 실제 LLM 연동은 추후 구현 예정 (환경변수로 활성화)
- 회귀 없음: 기존 97 + 신규 17 = 114 tests 모두 PASS

---

### 23. Step H-2.1: Real LLM Provider 연결 + 운영 가드레일 [기능]

**목표:**
- OpenAI API 실제 연결 구현 (LLM_ENABLED=1 시 활성화)
- PII 마스킹으로 개인정보 보호
- 운영 메트릭/로그 기록
- 스모크 테스트 스크립트 제공

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `services/extraction/pii_masker.py` | PII 마스킹 유틸리티 (주민번호, 전화번호, 계좌, 이메일) |
| `tests/test_pii_masker.py` | PII 마스킹 단위 테스트 (25개) |
| `tools/run_compare_with_llm_toggle.sh` | LLM 토글 스모크 테스트 스크립트 |

**OpenAILLMClient 구현:**
```python
class OpenAILLMClient:
    """
    - timeout(8s), retry(2), exponential backoff 지원
    - PII 마스킹 자동 적용
    - 메트릭 수집 (latency, success/failure, PII 마스킹 개수)
    """
```

**PII 마스킹 패턴:**
| 타입 | 패턴 | 대체 |
|------|------|------|
| 주민등록번호 | `YYMMDD-NNNNNNN` | `[주민번호]` |
| 전화번호 | `010-XXXX-XXXX` 등 | `[전화번호]` |
| 이메일 | `xxx@domain.com` | `[이메일]` |
| 계좌번호 | 10~16자리 숫자 | `[계좌번호]` |

**환경변수 (확장):**
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `LLM_ENABLED` | 0 | LLM 활성화 여부 |
| `LLM_PROVIDER` | openai | LLM 제공자 |
| `LLM_MODEL` | gpt-4o-mini | LLM 모델 |
| `LLM_TIMEOUT_SECONDS` | 8 | LLM 호출 타임아웃 |
| `LLM_MAX_CALLS_PER_REQUEST` | 8 | 요청당 최대 호출 횟수 |
| `LLM_MAX_CHARS_PER_CALL` | 4000 | 호출당 최대 문자 수 |
| `LLM_MAX_RETRIES` | 2 | 최대 재시도 횟수 |
| `OPENAI_API_KEY` | - | OpenAI API 키 (LLM_ENABLED=1 시 필수) |

**상세 메트릭 (LLMRefinementStats):**
```python
@dataclass
class LLMRefinementStats:
    llm_calls_attempted: int      # 시도된 호출 수
    llm_calls_succeeded: int      # 성공 호출 수
    llm_upgrades: int             # 업그레이드 횟수
    llm_failures_by_reason: dict  # 실패 이유별 카운트
    llm_total_latency_ms: float   # 총 레이턴시
```

**스모크 테스트 사용법:**
```bash
# LLM OFF (기본, CI 환경)
./tools/run_compare_with_llm_toggle.sh

# LLM ON (실제 API 호출)
LLM_ENABLED=1 OPENAI_API_KEY=sk-xxx ./tools/run_compare_with_llm_toggle.sh
```

**pytest 결과:**
```
139 passed in 18.19s
```

**효과:**
- LLM_ENABLED=0 상태에서 139개 테스트 모두 통과
- PII 마스킹으로 개인정보 보호 (LLM 호출 전 자동 적용)
- OpenAI API 연결 준비 완료 (환경변수로 활성화)
- 메트릭 수집으로 운영 가시성 확보
- 회귀 없음: 기존 114 + 신규 25 = 139 tests 모두 PASS

---

### 24. Step I: Plan 자동 선택 + plan_id 기반 retrieval [기능]

**목표:**
- /compare 요청에 age/gender 포함 시 product_plan에서 plan 자동 선택
- compare_axis retrieval에 plan_id 필터 적용
- policy_axis는 A2 정책 유지 (plan 무시)

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `services/retrieval/plan_selector.py` | Plan 자동 선택 모듈 |
| `tools/seed_product_plans.py` | 테스트용 Plan 데이터 seed 스크립트 |
| `tests/test_plan_selector.py` | Plan selector 단위 테스트 (15개) |

**API 스키마 확장:**
```python
class CompareRequest(BaseModel):
    # ... 기존 필드 ...
    age: int | None = None     # 피보험자 나이 (0~150)
    gender: Literal["M", "F"] | None = None  # 피보험자 성별
```

**debug 응답에 selected_plan 추가:**
```json
{
  "debug": {
    "selected_plan": [
      {"insurer_code": "SAMSUNG", "product_id": 1, "plan_id": 101, "reason": "gender_match(M)"}
    ]
  }
}
```

**Plan 선택 우선순위:**
1. gender 정확 일치 (M/F) > U (공용)
2. age 범위가 더 좁은 plan 우선
3. plan_name 존재 (명시적) 우선
4. 조건 없으면 plan_id=None (공통 문서만)

**Retrieval SQL 반영:**
```sql
-- plan_id가 있으면:
WHERE (c.plan_id = :plan_id OR c.plan_id IS NULL)

-- plan_id가 없으면:
WHERE c.plan_id IS NULL
```

**테스트 케이스 (15개):**
| 테스트 | 설명 |
|--------|------|
| `test_no_product_found` | product 없으면 plan_id=None |
| `test_no_age_gender_provided` | age/gender 없으면 plan 선택 안함 |
| `test_gender_exact_match_preferred` | gender 정확 일치 우선 |
| `test_gender_universal_fallback` | 정확 일치 없으면 U 선택 |
| `test_age_range_narrower_preferred` | age 범위 좁은 것 우선 |
| `test_no_matching_plan` | 조건 맞는 plan 없으면 None |
| `test_multiple_insurers` | 여러 보험사 각각 선택 |
| `test_age_gender_fields_in_request` | API에 필드 존재 |
| `test_age_gender_optional` | age/gender는 optional |
| `test_gender_validation` | M/F만 허용 |
| `test_policy_axis_no_plan_filter` | A2: policy_axis는 plan 무시 |

**pytest 결과:**
```
154 passed in 18.34s
```

**효과:**
- age/gender 기반 plan 자동 선택
- 보험사별 다른 plan 선택 가능
- A2 정책 유지 (약관은 plan 무관)
- 회귀 없음: 기존 139 + 신규 15 = 154 tests 모두 PASS

---

### 25. Step I-1: Ingestion plan_id 자동 태깅 (plan_detector) [기능]

**목표:**
- 문서 경로/파일명/메타에서 성별(M/F)·나이구간을 감지하여 document.plan_id 자동 태깅
- chunk.plan_id는 document.plan_id 상속
- 기존 데이터는 backfill 도구로 일괄 갱신

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `services/ingestion/plan_detector.py` | Plan 감지 모듈 (성별/나이 패턴 매칭) |
| `tools/backfill_plan_ids.py` | 기존 document/chunk plan_id 백필 도구 |
| `tests/test_plan_detector.py` | Plan detector 단위 테스트 (69개) |

**성별 감지 패턴:**
```python
MALE_PATTERNS = [
    r"남성", r"남자", r"\b남\b", r"\(남\)", r"_남_", r"-남-",
    r"남형", r"\bmale\b", r"\bM형\b", r"남성형",
]
FEMALE_PATTERNS = [
    r"여성", r"여자", r"\b여\b", r"\(여\)", r"_여_", r"-여-",
    r"여형", r"\bfemale\b", r"\bF형\b", r"여성형",
]
```

**나이 감지 패턴:**
| 패턴 | 예시 | 결과 |
|------|------|------|
| `XX세 이하` | 40세이하 | (None, 40) |
| `XX세 이상` | 41세이상 | (41, None) |
| `XX-YY세` | 20-40세 | (20, 40) |
| `만XX세` | 만40세 | (40, 40) |
| `XX대` | 30대 | (30, 39) |
| `XX세 미만` | 40세미만 | (None, 39) |
| `XX세 초과` | 40세초과 | (41, None) |

**감지 우선순위:**
1. meta (gender/age 필드)
2. doc_title (문서 제목)
3. source_path (파일명 → 폴더명)

**Ingestion 파이프라인 통합:**
```python
# ingest.py에서 plan_id 자동 감지
if plan_id is None and manifest.insurer_code:
    detector_result = detect_plan_id(
        conn=db_writer.conn,
        insurer_code=manifest.insurer_code,
        source_path=str(pdf_path),
        doc_title=manifest.document.title,
        meta=manifest.document.meta,
    )
    if detector_result.plan_id:
        plan_id = detector_result.plan_id
        logger.info(f"Plan auto-detected: {plan_id} ({detector_result.reason})")
```

**Backfill 도구 사용법:**
```bash
# Dry-run (실제 업데이트 없이 시뮬레이션)
python tools/backfill_plan_ids.py --dry-run

# 특정 보험사만
python tools/backfill_plan_ids.py --insurer SAMSUNG

# 전체 실행
python tools/backfill_plan_ids.py

# 현재 상태 확인
python tools/backfill_plan_ids.py --verify-only
```

**테스트 케이스 (69개):**
| 테스트 클래스 | 테스트 수 | 설명 |
|--------------|----------|------|
| TestDetectGender | 11 | 성별 패턴 감지 |
| TestDetectAgeRange | 9 | 나이 범위 패턴 감지 |
| TestDetectFromPath | 6 | 파일 경로 기반 감지 |
| TestDetectFromMeta | 5 | 메타데이터 기반 감지 |
| TestDetectPlanInfo | 3 | 통합 감지 우선순위 |
| TestFindMatchingPlanId | 3 | DB plan 매칭 |
| TestDetectPlanId | 3 | 전체 감지 플로우 |
| TestEdgeCases | 4 | 엣지 케이스 |
| TestPatternCoverage | 25 | 모든 패턴 커버리지 |

**pytest 결과:**
```
223 passed in 18.31s
```

**효과:**
- Ingestion 시 파일 경로/메타에서 plan 자동 감지
- 기존 문서 plan_id 백필 도구 제공
- 69개 테스트로 패턴 커버리지 보장
- 회귀 없음: 기존 154 + 신규 69 = 223 tests 모두 PASS

---

### 26. Step J-1: Plan 태깅 품질 리포트 + /compare 플랜 회귀 테스트 [검증]

**목표:**
- 8개 보험사 전체에 대해 plan_id 태깅 결과를 정량 리포트로 생성
- /compare가 age/gender 입력에 따라 plan이 올바르게 선택되는지 회귀 테스트
- LOTTE(남/여), DB(연령) 중심으로 플랜 영향 검증

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `tools/audit_plan_tagging.py` | Plan 태깅 품질 리포트 생성 스크립트 |
| `artifacts/audit/plan_tagging_report.md` | 리포트 출력 파일 |
| `tests/test_compare_api_plan_cases.py` | Plan 회귀 테스트 (14개) |

**리포트 지표:**
| 지표 | 설명 |
|------|------|
| doc_type별 plan_id 분포 | NULL vs non-NULL |
| gender별 plan 분포 | M/F/U |
| age_range 분포 | age_min/age_max 히스토그램 |
| plan 충돌 탐지 | 동일 경로 다른 plan_id, 성별 불일치 |

**리포트 사용법:**
```bash
# 리포트 생성
python tools/audit_plan_tagging.py

# 출력만 (파일 저장 없이)
python tools/audit_plan_tagging.py --print-only

# 커스텀 출력 경로
python tools/audit_plan_tagging.py --output my_report.md
```

**회귀 테스트 케이스 (14개):**
| 테스트 클래스 | 테스트 수 | 설명 |
|--------------|----------|------|
| TestPlanSelectorInvocation | 4 | age/gender에 따른 plan 선택 |
| TestA2PolicyWithPlan | 2 | A2 정책 유지 검증 |
| TestMultipleInsurersWithPlan | 2 | 여러 보험사 동시 비교 |
| TestCommonDocumentsRegression | 2 | 공통 문서 회귀 |
| TestPlanEdgeCases | 4 | 엣지 케이스 |

**핵심 테스트:**
| 테스트 | 검증 내용 |
|--------|----------|
| `test_male_vs_female_different_plans` | LOTTE: gender=M vs F → 다른 plan 선택 |
| `test_age_39_vs_41_different_plans` | DB: age=39 vs 41 → 다른 plan 선택 |
| `test_compare_axis_no_policy_with_plan` | plan 선택 시에도 약관은 compare_axis에 없음 |
| `test_multiple_insurers_each_has_plan` | 여러 보험사 각각 plan 선택됨 |

**backfill 도구 CI 지원:**
```bash
# CI에서 DB 없어도 에러 없이 종료
python tools/backfill_plan_ids.py --verify-only --skip-if-empty
```

**pytest 결과:**
```
237 passed in 22.47s
```

**효과:**
- Plan 태깅 품질을 정량적으로 측정 가능
- age/gender에 따른 plan 선택 동작 회귀 테스트
- A2 정책(약관 분리) 유지 검증
- CI 환경 지원 (--skip-if-empty)
- 회귀 없음: 기존 223 + 신규 14 = 237 tests 모두 PASS

---

### 27. Step J-2: manifest.csv 기반 plan 태깅 + backfill + 재검증 [기능]

**목표:**
- manifest 파일에 plan 정보(gender, age_min, age_max)를 명시하여 plan_id 태깅
- backfill 시 manifest 우선 → detector fallback 전략
- LOTTE(성별), DB(연령) 중심으로 plan_id가 실제로 채워지는지 검증

**생성/수정된 파일:**
| 파일 | 설명 |
|------|------|
| `data/lotte/*/*.manifest.yaml` | LOTTE 8개 문서 manifest (gender: M/F) |
| `data/db/가입설계서/*.manifest.yaml` | DB 2개 문서 manifest (age_min/max) |
| `services/ingestion/db_writer.py` | `find_plan_by_attributes()` 추가 |
| `tools/backfill_plan_ids.py` | `--manifest` 옵션 추가 |
| `tests/test_compare_api_plan_cases.py` | Plan evidence 테스트 5개 추가 |

**manifest plan 필드:**
```yaml
schema_version: manifest_v1
insurer_code: LOTTE
doc_type: 상품요약서
plan:
  gender: M      # M/F/U
  age_min: null  # null 또는 정수
  age_max: null  # null 또는 정수
```

**Plan 매칭 우선순위:**
1. `age_specificity`: age 제약이 있는 plan 우선 (NULL보다 구체적)
2. `gender_score`: 정확한 gender 매칭 우선 (M/F > U)
3. `age_range`: 더 좁은 범위 우선

**backfill --manifest 사용법:**
```bash
# manifest 우선 모드
python tools/backfill_plan_ids.py --manifest --insurer LOTTE

# dry-run
python tools/backfill_plan_ids.py --manifest --dry-run
```

**Plan 태깅 결과:**
| 보험사 | 전체 문서 | plan_id 있음 | 태깅률 |
|--------|----------|-------------|--------|
| LOTTE | 8 | 8 | **100.0%** |
| DB | 5 | 2 | **40.0%** |
| 기타 | 25 | 0 | 0.0% |
| **합계** | **38** | **10** | **26.3%** |

**LOTTE Plan 분포:**
- 남성(M): 4개 문서 (plan_id=6)
- 여성(F): 4개 문서 (plan_id=8)

**DB Plan 분포:**
- 40세이하: 1개 문서 (plan_id=11, 남성-40세이하)
- 41세이상: 1개 문서 (plan_id=12, 남성-41세이상)
- 공통: 3개 문서 (plan_id=NULL)

**추가된 테스트 (5개):**
| 테스트 | 설명 |
|--------|------|
| `test_lotte_evidence_plan_id_in_debug` | LOTTE plan 선택 정보 검증 |
| `test_lotte_male_vs_female_evidence_chunks` | 남/여 다른 plan 선택 |
| `test_db_age_based_plan_selection` | 나이에 따른 plan 선택 |
| `test_plan_filter_affects_retrieval` | plan 필터가 retrieval에 적용 |
| `test_insurer_with_vs_without_plans` | plan 있는/없는 보험사 비교 |

**pytest 결과:**
```
242 passed in 23.02s
```

**효과:**
- manifest로 plan 정보 명시 → detector보다 신뢰도 높은 태깅
- LOTTE 100%, DB 40% plan 태깅 달성
- age_specificity 우선 매칭으로 공용 plan 대신 구체적 plan 선택
- 회귀 없음: 기존 237 + 신규 5 = 242 tests 모두 PASS

---

### 28. Step J-3: DB 미태깅 원인 분류 + LOTTE 플랜 E2E 검증 [검증]

**목표:**
- DB의 plan_id NULL 문서 3개에 대한 원인 분류 및 근거 명시
- LOTTE 플랜이 실제 검색 결과(evidence, resolved_amount)에 미치는 효과 E2E 검증
- SAMSUNG (plan 없음) 회귀 테스트

**1. DB 미태깅 원인 분류 리포트:**

| document_id | doc_type | reason | 판정 |
|-------------|----------|--------|------|
| 8 | 사업방법서 | COMMON_DOC_EXPECTED | ✅ 정상 NULL |
| 9 | 상품요약서 | COMMON_DOC_EXPECTED | ✅ 정상 NULL |
| 10 | 약관 | COMMON_DOC_EXPECTED | ✅ 정상 NULL |

**결론:** DB의 3개 미태깅 문서는 모두 `COMMON_DOC_EXPECTED` (공통 문서)로 분류되어 **plan_id = NULL이 의도된 동작**입니다.
- 사업방법서, 상품요약서, 약관은 플랜 구분 없이 모든 플랜에 공통으로 적용
- manifest 보강 불필요

**2. LOTTE 플랜 E2E 검증 테스트:**

| 테스트 | 검증 내용 | 결과 |
|--------|----------|------|
| `test_lotte_gender_m_vs_f_different_plan_ids` | 남/여 다른 plan_id 선택 | ✅ PASS |
| `test_lotte_gender_m_vs_f_evidence_document_difference` | best_evidence.document_id 차이 | ✅ PASS |
| `test_lotte_gender_m_vs_f_resolved_amount_source_difference` | resolved_amount 소스 차이 | ⚠️ WARN (금액 미추출) |
| `test_db_age_39_vs_41_different_plan_ids` | 39세/41세 다른 plan_id 선택 | ✅ PASS |
| `test_db_age_39_vs_41_evidence_or_amount_change` | evidence 또는 amount 변화 | ✅ PASS |

**3. SAMSUNG 회귀 테스트 (plan 없음):**

| 테스트 | 검증 내용 | 결과 |
|--------|----------|------|
| `test_samsung_no_plan_same_results_with_different_gender` | gender 달라도 결과 동일 | ✅ PASS |
| `test_samsung_no_plan_same_results_with_different_age` | age 달라도 결과 동일 | ✅ PASS |
| `test_samsung_no_plan_same_compare_axis` | plan 파라미터로 결과 안 달라짐 | ✅ PASS |
| `test_samsung_vs_lotte_plan_effect_comparison` | plan 있는/없는 보험사 비교 | ✅ PASS |

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `tools/audit_unassigned_plans.py` | 미태깅 원인 분류 스크립트 |
| `artifacts/audit/db_unassigned_plans.md` | DB 미태깅 원인 리포트 |
| `tests/test_compare_api_plan_effects.py` | Plan 효과 E2E 테스트 (9개) |

**pytest 결과:**
```
251 passed in 26.25s
```

**효과:**
- DB 미태깅 3개 → 모두 COMMON_DOC_EXPECTED (정상 NULL)
- LOTTE: gender 변경 시 다른 plan/evidence 반환 검증
- DB: age 변경 시 다른 plan/evidence 반환 검증
- SAMSUNG: plan 없어도 age/gender 파라미터에 영향 안 받음 (회귀 없음)
- 회귀 없음: 기존 242 + 신규 9 = 251 tests 모두 PASS

---

### 29. Step K: Vector Retrieval 품질 고정 + 파라미터 튜닝 + Hybrid 옵션 [검증/기능]

**목표:**
- pgvector 기반 compare_axis retrieval이 8개 보험사 전체에서 안정적으로 동작
- "잘 나와야 하는 근거"를 테스트로 고정해서 이후 변경에도 품질 유지
- HNSW/쿼리 파라미터(ef_search, top_k) 튜닝을 벤치마크로 문서화
- coverage_codes가 없거나 애매한 질의에서 Hybrid(벡터+키워드) fallback 옵션 제공

**1. 고정 질의 세트 (18개 케이스):**

| 카테고리 | 케이스 | 설명 |
|----------|--------|------|
| 2사 비교 | case_01~03 | 삼성 vs 메리츠/롯데, DB vs KB |
| Plan 기반 | case_04~05 | DB age 39/41 |
| 8개사 전체 | case_06~08 | 암진단비, 뇌졸중, 질병수술비 |
| 단일사 | case_09~12 | 제자리암, 입원일당, LOTTE 성별 |
| 키워드만 | case_13~15 | coverage_codes 비움 |
| A2 정책 | case_16 | compare_axis에 약관 없음 검증 |
| Quota | case_17~18 | top_k_per_insurer 검증 |

**2. Retrieval 품질 회귀 테스트:**

| 테스트 클래스 | 테스트 수 | 설명 |
|--------------|----------|------|
| TestRetrievalQuality | 54 | min_total, min_per_insurer, max_per_insurer |
| TestA2PolicyCompliance | 18 | compare_axis에 약관 없음 |
| TestDocTypeRequirements | 36 | must_include/exclude doc_types |
| TestCoverageCodeRequirements | 18 | coverage_code 포함 검증 |
| TestResponseStructure | 10 | 응답 구조 검증 |
| TestPlanSelection | 3 | age/gender plan 선택 |

**3. 벤치마크 스크립트:**

```bash
# 벤치마크 실행
python tools/benchmark_compare_axis.py

# 커스텀 옵션
python tools/benchmark_compare_axis.py --iterations 50 --output custom_report.md
```

**벤치마크 파라미터:**
| 파라미터 | 기본값 | 권장값 | 설명 |
|----------|--------|--------|------|
| top_k_per_insurer | 5 | 5 | 속도/품질 균형 |
| top_k_per_insurer | 3 | 3 | 속도 우선 |
| top_k_per_insurer | 8~10 | 8 | 품질 우선 |
| ef_search | 40 | 40 | HNSW 파라미터 (벡터 검색 시) |

**4. Hybrid 옵션 (기본 OFF):**

```bash
# Hybrid fallback 활성화
COMPARE_AXIS_HYBRID=1

# HNSW ef_search 파라미터
COMPARE_AXIS_EF_SEARCH=40

# 벡터 검색 top_k
COMPARE_AXIS_VECTOR_TOP_K=20
```

**Hybrid 로직:**
1. coverage_codes 검색 결과가 부족할 때 (보험사당 최소 1개 미달)
2. 벡터 검색 실행 (pgvector HNSW 인덱스)
3. 기존 결과와 병합 (중복 제거)

**debug 응답에 추가된 필드:**
```json
{
  "debug": {
    "hybrid_enabled": false,
    "hybrid_used": false,
    "timing_ms": {
      "compare_axis_vector": 123.45
    }
  }
}
```

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `tests/fixtures/retrieval_cases.yaml` | 고정 질의 세트 (18개) |
| `tests/test_vector_retrieval_quality.py` | Retrieval 품질 회귀 테스트 |
| `tools/benchmark_compare_axis.py` | 벤치마크 스크립트 |

**pytest 결과:**
```
316 passed, 74 skipped, 6 warnings in 49.56s
```

**효과:**
- 18개 고정 질의 세트로 retrieval 품질 회귀 방지
- A2 정책 유지 검증 (약관은 compare_axis에 절대 없음)
- Hybrid 옵션으로 coverage_codes 없을 때 벡터 검색 fallback 가능
- 파라미터 튜닝 벤치마크 도구 제공
- 회귀 없음: 기존 251 + 신규 65 = 316 tests 모두 PASS (74 skipped)

---

### 30. Step U-ChatUI: Next.js 채팅 UI (Compare 비교표) [UI]

**목표:**
- ChatGPT 스타일의 채팅 UI로 보험 비교 결과 표시
- /compare API 연동
- 탭 기반 결과 표시 (Compare, Evidence, Policy, Debug)

**기술 스택:**
- Next.js 16 + TypeScript
- Tailwind CSS + shadcn/ui
- Lucide Icons

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `apps/web/src/app/page.tsx` | 메인 채팅 페이지 |
| `apps/web/src/components/ChatInput.tsx` | 채팅 입력 컴포넌트 |
| `apps/web/src/components/CompareTable.tsx` | 비교표 컴포넌트 |
| `apps/web/src/components/EvidencePanel.tsx` | 근거 자료 패널 |
| `apps/web/src/lib/api.ts` | API 유틸리티 |
| `apps/web/src/lib/types.ts` | TypeScript 타입 정의 |

**효과:**
- ChatGPT 스타일 UI로 보험 비교 결과 직관적 표시
- 탭으로 Compare/Evidence/Policy/Debug 구분
- 모바일 반응형 지원

---

### 31. Step U-1: A2 정책 신뢰 (약관 제외 안내 UI) [UI]

**목표:**
- A2 정책(약관 제외)을 UI에서 명시적으로 안내
- 사용자가 비교 결과의 근거 범위를 이해할 수 있도록 표시

**구현 내용:**
1. Compare 탭에 안내 문구 추가:
   - "※ 비교 결과는 가입설계서·상품요약서·사업방법서를 기준으로 산출됩니다."
   - "※ 약관은 비교 계산에 사용되지 않습니다."

2. Policy 탭에 약관 설명 추가:
   - 약관은 정책/정의 근거 확인용으로만 제공됨을 안내

3. UI defensive filter 추가:
   - `filterNonPolicy()` 함수로 약관 제외 (서버 A2 정책의 이중 안전장치)

**수정된 파일:**
| 파일 | 설명 |
|------|------|
| `apps/web/src/components/CompareTable.tsx` | A2 안내 문구 + defensive filter |
| `apps/web/src/components/EvidencePanel.tsx` | Policy 탭 안내 + defensive filter |

**효과:**
- 사용자가 비교 결과의 근거 범위를 명확히 인지
- 서버 A2 정책 + UI defensive filter로 이중 안전

---

### 32. Step U-2: Evidence PDF Page Viewer (원문 보기) [UI/API]

**목표:**
- Evidence에서 View 버튼 클릭 시 PDF 원문 페이지 이미지 표시
- Backend: PyMuPDF 기반 PDF 렌더링 API
- Frontend: 전체화면 PDF 뷰어 (페이지 이동, 줌)

**Backend 구현:**

1. `GET /documents/{document_id}/page/{page}` 엔드포인트:
   - PyMuPDF (fitz)로 PDF → PNG 렌더링
   - scale 파라미터 (1.0~4.0, 기본 2.0)
   - lru_cache + disk cache (`artifacts/page_cache/`)
   - 보안: DB source_path만 사용, path traversal 방지

2. `GET /documents/{document_id}/info` 엔드포인트:
   - 문서 정보 (page_count, source_path) 반환

**Frontend 구현:**

`PdfPageViewer.tsx` 컴포넌트:
- 전체화면 모달
- 페이지 이동 (← → 키보드, 버튼)
- 스케일 토글 (1x/2x/3x)
- ESC로 닫기
- 로딩/에러 상태 처리
- Copy ref 버튼

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `api/document_viewer.py` | PDF 페이지 렌더링 API |
| `tests/test_document_viewer.py` | API 테스트 (7개) |
| `apps/web/src/components/PdfPageViewer.tsx` | PDF 뷰어 컴포넌트 |

**수정된 파일:**
| 파일 | 설명 |
|------|------|
| `api/main.py` | document_viewer 라우터 등록 |
| `apps/web/src/components/EvidencePanel.tsx` | View 버튼 연결 |
| `apps/web/src/components/CompareTable.tsx` | View 버튼 연결 |

**API 응답:**
```
GET /documents/1/page/1?scale=2
→ 200 OK, Content-Type: image/png
```

**효과:**
- Evidence에서 원문 PDF 페이지를 바로 확인 가능
- 키보드 네비게이션으로 빠른 페이지 이동
- 캐싱으로 반복 요청 최적화

---

### 33. Step U-2.5: Evidence 하이라이트 + Deep-link [UI/API]

**목표:**
- View 버튼으로 PDF 열 때 근거 텍스트가 페이지 내 어디인지 시각적으로 표시
- Deep-link URL로 특정 페이지+하이라이트 상태 공유 가능

**Backend 구현:**

`GET /documents/{document_id}/page/{page}/spans` 엔드포인트:
- Query param: `q` (하이라이트할 텍스트, 최대 200자), `max_hits` (기본 5)
- PyMuPDF `search_for()` + fuzzy matching (SequenceMatcher)
- bbox 좌표 반환 (PDF 좌표계 기준)

**응답 예시:**
```json
{
  "document_id": 1,
  "page": 5,
  "hits": [
    {"bbox": [72.0, 100.0, 300.0, 120.0], "score": 1.0, "text": "매칭된 텍스트..."}
  ]
}
```

**Frontend 구현:**

1. `PdfPageViewer` props 확장:
   - `highlightQuery?: string` 추가
   - `/spans?q=` API 호출하여 bbox 조회
   - 노란색 투명 박스로 하이라이트 표시
   - scale(1x/2x/3x) 변경 시 bbox도 비례 확대

2. Evidence/Compare에서 highlightQuery 전달:
   - `evidence.snippet?.slice(0, 120)` 전달

3. Deep-link URL 지원:
   - `?doc=123&page=5&hl=<encoded>` 형태
   - 새로고침해도 동일 상태 복원
   - ESC 또는 닫기 버튼으로 URL 파라미터 제거

**생성/수정된 파일:**
| 파일 | 설명 |
|------|------|
| `api/document_viewer.py` | `/spans` 엔드포인트 추가 |
| `tests/test_document_viewer.py` | spans API 테스트 8개 추가 |
| `apps/web/src/components/PdfPageViewer.tsx` | highlight overlay 추가 |
| `apps/web/src/components/EvidencePanel.tsx` | highlightQuery 전달 |
| `apps/web/src/components/CompareTable.tsx` | highlightQuery 전달 |
| `apps/web/src/app/page.tsx` | deep-link URL 처리 |

**curl 예시:**
```bash
curl "http://localhost:8000/documents/1/page/1/spans?q=보험금&max_hits=3"
```

**UI 흐름:**
1. Evidence 카드에서 View 버튼 클릭
2. PdfPageViewer 열림 → 0.1초 후 `/spans?q=` 호출
3. 매칭된 영역에 노란색 투명 박스 표시 (best-effort)

**테스트 케이스 (8개):**
| 테스트 | 설명 |
|--------|------|
| `test_spans_success` | 정상 응답 구조 |
| `test_spans_with_hits` | bbox 포함 확인 |
| `test_spans_no_match` | 매칭 없으면 hits=[] |
| `test_spans_document_not_found` | 404 |
| `test_spans_page_out_of_range` | 404 |
| `test_spans_query_required` | q 필수 (422) |
| `test_spans_max_hits` | max_hits 동작 |
| `test_spans_long_query_truncated` | 긴 쿼리 처리 |

**효과:**
- 근거 텍스트 위치를 시각적으로 확인 가능
- Deep-link로 특정 근거 페이지 공유 가능
- 하이라이트는 best-effort (매칭 실패 시 조용히 fallback)

---

### 34. Step U-4: Docker Compose 데모 배포 패키징 [DevOps]

**목표:**
- `git clone` 후 한 번의 명령으로 전체 시스템 실행
- DB + API + Web + Nginx 4개 서비스 통합 배포
- 스모크 테스트 자동 실행

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `docker-compose.demo.yml` | 데모용 Docker Compose |
| `api/Dockerfile` | FastAPI 백엔드 이미지 |
| `apps/web/Dockerfile` | Next.js 프론트엔드 이미지 |
| `deploy/nginx.conf` | Nginx 리버스 프록시 설정 |
| `tools/demo_up.sh` | 원클릭 실행 스크립트 |
| `README.md` | 데모 실행 가이드 |

**서비스 구성:**
| 서비스 | 이미지 | 포트 | 설명 |
|--------|--------|------|------|
| db | pgvector/pgvector:pg16 | 5432 | PostgreSQL + pgvector |
| api | (빌드) | 8000 | FastAPI 백엔드 |
| web | (빌드) | 3000 | Next.js 프론트엔드 |
| nginx | nginx:alpine | 80 | 리버스 프록시 |

**Nginx 라우팅:**
```
/api/*  → api:8000 (strip /api prefix)
/       → web:3000
```

**사용법:**
```bash
# 데모 실행
./tools/demo_up.sh

# 이미지 재빌드
./tools/demo_up.sh --build

# 볼륨 삭제 후 재시작
./tools/demo_up.sh --clean

# 종료
docker compose -f docker-compose.demo.yml down
```

**접속 URL:**
| 서비스 | URL |
|--------|-----|
| Web UI | http://localhost |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

**스모크 테스트:**
- `/health` API 체크
- `/api/health` Nginx 경유 체크
- `/compare` 간단 요청 테스트

**효과:**
- git clone → `./tools/demo_up.sh` 한 줄로 전체 시스템 실행
- 4개 서비스 의존성 자동 관리 (healthcheck + depends_on)
- 스모크 테스트로 배포 검증 자동화

---

### 35. Step U-4.1: 데모 데이터 시딩 자동화 + /compare 스모크 활성화 [DevOps]

**목표:**
- `./tools/demo_up.sh` 실행 시 데이터 시딩까지 자동화
- DB 스키마 적용 → Coverage 매핑 로드 → SAMSUNG/MERITZ ingestion → /compare 스모크 테스트
- 컨테이너 경로 정합성: `SOURCE_PATH_ROOT` 환경변수로 source_path 변환

**수정/생성된 파일:**
| 파일 | 설명 |
|------|------|
| `services/ingestion/ingest.py` | `SOURCE_PATH_ROOT` 환경변수 지원 추가 |
| `tools/demo_seed.sh` | 데이터 시딩 스크립트 (단독 실행 가능) |
| `tools/demo_up.sh` | 데이터 시딩 단계 통합 |
| `api/Dockerfile` | tools 폴더 복사 추가 |
| `README.md` | API 스키마(`insurers`) 수정 |

**SOURCE_PATH_ROOT 동작:**
```python
# ingest.py에서 source_path 변환
source_path_root = os.environ.get("SOURCE_PATH_ROOT")
if source_path_root:
    rel_path = pdf_path.relative_to(root)
    source_path = str(Path(source_path_root) / rel_path)
    # 예: /Users/.../data/samsung/... → /app/data/samsung/...
```

**demo_up.sh 시딩 단계:**
1. Coverage 매핑 로드 (`data/담보명mapping자료.xlsx`)
2. SAMSUNG ingestion (약관/요약서/사업방법서/가입설계서)
3. MERITZ ingestion
4. 적재 결과 확인 (문서/청크 수)

**적재 결과:**
```
문서: 9개
청크: 3,216개 (SAMSUNG 1,279 + MERITZ 1,937)
```

**스모크 테스트 결과:**
```
/health: OK
/api/health (via nginx): OK
/compare: PASS (4개 근거)
```

**compare 응답 요약:**
- compare_axis: 4개 근거
- coverage_compare_result: 4개 담보
- diff_summary: 4개 차이점
- policy_axis: SAMSUNG 30개, MERITZ 30개 약관 근거

**효과:**
- `git clone` → `./tools/demo_up.sh` 한 번으로 데이터 적재까지 완료
- /compare 스모크 테스트 PASS로 배포 검증
- 컨테이너 경로 정합성으로 PDF Viewer 정상 동작

---

### 36. Step U-4.8: Comparison Slots v0.1 (암진단비 슬롯 기반 비교) [기능/UI]

**목표:**
- 암진단비 담보군에 대해 슬롯 기반 비교 제공
- 슬롯별로 값(value)과 근거(evidence)가 연결
- A2 정책 유지: 약관은 비교 계산에 사용하지 않되, 정의/면책 근거로는 제공

**PRD:**
- PRD: `docs/U-4.8_slots_PRD.md`
- 대상 담보: A4200_1(암진단비), A4210(유사암진단비), A4209(재진단암진단비)

**슬롯 정의 (v0.1):**
| slot_key | label | comparable | source |
|----------|-------|------------|--------|
| payout_amount | 지급금액 | true | 가입설계서/상품요약서/사업방법서 |
| existence_status | 담보 존재 여부 | true | 가입설계서/상품요약서/사업방법서 |
| payout_condition_summary | 지급조건 요약 | true | 상품요약서/사업방법서/가입설계서 |
| diagnosis_scope_definition | 진단 범위 정의 | false | 약관 |
| waiting_period | 대기기간 | false | 약관 |

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `ontology/comparison_slots.v0.1.yaml` | 슬롯 정의 YAML |
| `db/migrations/20251218_add_comparison_slots.sql` | DB 마이그레이션 (선택적 캐시) |
| `services/extraction/slot_extractor.py` | 슬롯 추출 서비스 |
| `apps/web/src/components/SlotsTable.tsx` | UI 슬롯 테이블 컴포넌트 |
| `eval/goldset_u48_slots.csv` | 평가 골드셋 (10개 케이스) |
| `tools/run_u48_eval.sh` | U-4.8 평가 스크립트 |

**API 변경:**
```json
{
  "slots": [
    {
      "slot_key": "payout_amount",
      "label": "지급금액",
      "comparable": true,
      "insurers": [
        {
          "insurer_code": "SAMSUNG",
          "value": "3,000만원",
          "confidence": "high",
          "evidence_refs": [{"document_id": 1, "page_start": 5}]
        },
        {
          "insurer_code": "MERITZ",
          "value": null,
          "confidence": "not_found",
          "reason": "가입설계서/상품요약서/사업방법서에서 금액 미확인"
        }
      ],
      "diff_summary": "SAMSUNG: 3,000만원. MERITZ은(는) 미확인."
    }
  ]
}
```

**UI 변경:**
- Slots 탭 추가 (암진단비 요청 시 기본 탭)
- 비교 항목: 테이블 형태로 보험사별 값/confidence 표시
- 정의/참고: 약관 기반 정보 (비교 계산 미사용 안내)
- A2 정책 안내 배지 표시

**Acceptance Criteria:**
- AC1: 최소 3개 슬롯(payout_amount, existence_status, payout_condition_summary) 표시
- AC2: not_found 시 slot 단위로 reason 표시
- AC3: evidence 최대 3개 기본 노출, score=0.00 → N/A 대체
- AC4: demo_up.sh 스모크 유지 + U-4.8 eval 10개 PASS

**실행 방법:**
```bash
# 1. 마이그레이션 (선택적)
psql -U postgres -d inca_rag -f db/migrations/20251218_add_comparison_slots.sql

# 2. 백엔드 (변경 자동 적용)
python -m uvicorn api.main:app --reload

# 3. 프론트엔드
cd apps/web && npm run dev

# 4. 스모크 + U-4.8 평가
./tools/demo_up.sh --down
./tools/run_u48_eval.sh
```

**효과:**
- 암진단비 질문에 대해 구조화된 슬롯 비교 제공
- "삼성과 메리츠의 암진단비 비교해줘" → 지급금액/존재여부/조건요약 슬롯 표시
- A2 정책 유지: 약관은 정의/참고용으로만 제공

---

### 37. Step U-4.9: Eval Framework 구축 (goldset + eval_runner) [검증]

**목표:**
- 데모 비교 결과의 정확성을 자동으로 검증할 수 있는 Eval 프레임워크 구축
- "이 비교 결과를 우리가 얼마나 믿어도 되는지" 자동 판단

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `eval/goldset_cancer_minimal.csv` | 암진단비 정답셋 (4개 케이스) |
| `eval/eval_runner.py` | Eval 실행기 (API 호출 → 정답 비교) |
| `tools/run_demo_eval.sh` | 데모 신뢰성 기준선 원샷 스크립트 |

**Goldset 컬럼:**
```
query,insurer,coverage_code,slot_key,expected_value,expected_doc_type
```

**Eval Runner 지표:**
| 지표 | 설명 |
|------|------|
| coverage_resolve_rate | expected coverage_code가 resolved_coverage_codes에 포함 |
| slot_fill_rate | expected slot이 실제로 채워졌는지 |
| value_correct_rate | 값이 정답과 일치하는지 (정규화 비교) |
| evidence_doc_type_match_rate | 근거 doc_type이 expected와 일치 (optional) |

**현재 Eval 결과:**
```
- Total cases: 4
- Coverage resolve rate: 100%
- Slot fill rate: 100%
- Value correctness: 100%
```

**사용법:**
```bash
# 원샷 실행 (audit + eval)
./tools/run_demo_eval.sh

# eval만 실행
python eval/eval_runner.py
```

**효과:**
- 데모 신뢰성 기준선 확립 (100% 정확도 검증)
- 회귀 방지: 변경 후 eval 재실행으로 정확도 유지 확인
- audit_slots.py + eval_runner.py 이중 검증 체계

---

### 38. Step U-4.10: Demo vs Main 변경사항 분류 문서화 [문서]

**목표:**
- 데모에서 수정된 로직이 본선(main/dev)에 반영되어야 하는지 분류
- 체리픽/PR 전략 제안 및 반영 후 검증 체크리스트 제공

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `docs/demo_vs_main_diff.md` | Demo vs Main 변경사항 분류 문서 |

**분류 결과:**

| 분류 | 파일 수 | 핵심 내용 |
|------|--------|----------|
| 공통 반영 | 12개 | amount_extractor, slot_extractor, compare_service, tests |
| 데모 전용 | 9개 | eval/*, tools/run_demo_eval.sh, docker-compose.demo.yml |

**공통 반영 대상 (Critical):**
- `services/extraction/amount_extractor.py` - LUMP_SUM 키워드, premium-negative 거리 비교
- `services/extraction/slot_extractor.py` - 슬롯 기반 추출 모듈
- `services/retrieval/compare_service.py` - 2-pass retrieval, slots 통합
- `tests/test_extraction.py` - 47개 테스트

**권장 반영 전략:**
```bash
git cherry-pick a888f72
```

**반영 후 체크리스트:**
1. `python -m pytest tests/test_extraction.py -v` → 47 PASS
2. `/compare` API → SAMSUNG/MERITZ 3,000만원
3. `./tools/run_demo_eval.sh` → 100% correctness

**효과:**
- 데모/본선 변경사항 명확히 분리
- 본선 반영 시 리스크/장점 분석 제공
- 체리픽 후 검증 체크리스트로 안전한 병합

---

### 39. Step U-4.11: Slot Generalization (coverage type 레지스트리) [기능]

**목표:**
- payout_amount 슬롯의 암 전용 하드코딩 제거
- 2-pass retrieval 로직을 범용화하여 다양한 슬롯 타입 지원
- resolved_coverage_codes를 API top-level로 승격

**구현 내용:**

**1. Coverage Type 레지스트리 (`slot_extractor.py`):**
```python
COVERAGE_CODE_TO_TYPE = {
    "A4200_1": "cancer_diagnosis",
    "A4210": "cancer_diagnosis",
    "A4209": "cancer_diagnosis",
    # ... 추가 담보 타입 확장 가능
}

SLOT_DEFINITIONS_BY_COVERAGE_TYPE = {
    "cancer_diagnosis": CANCER_DIAGNOSIS_SLOTS,
    # ... 추가 타입 정의 가능
}
```

**2. 2-pass Retrieval 범용화 (`compare_service.py`):**
```python
RETRIEVAL_CONFIG = {
    "preview_len": int(os.environ.get("RETRIEVAL_PREVIEW_LEN", "1000")),
    "top_k_pass1": int(os.environ.get("RETRIEVAL_TOP_K_PASS1", "10")),
    "top_k_pass2": int(os.environ.get("RETRIEVAL_TOP_K_PASS2", "5")),
}

SLOT_SEARCH_KEYWORDS = {
    "diagnosis_lump_sum": [...],
    "cancer_diagnosis": [...],
    "surgery_benefit": [...],
    "hospitalization_daily": [...],
}
```

**3. resolved_coverage_codes API 승격:**
- 기존: `debug.resolved_coverage_codes`에만 존재
- 변경: `CompareResponse.resolved_coverage_codes` top-level 필드로 승격
- 하위 호환성: eval_runner가 top-level 우선, debug fallback

**수정된 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `services/extraction/slot_extractor.py` | COVERAGE_CODE_TO_TYPE 매핑, extract_diagnosis_lump_sum_slot 함수 |
| `services/retrieval/compare_service.py` | RETRIEVAL_CONFIG, SLOT_SEARCH_KEYWORDS, resolved_coverage_codes 반환 |
| `api/compare.py` | CompareResponseModel.resolved_coverage_codes 필드 추가 |
| `eval/eval_runner.py` | top-level resolved_coverage_codes 읽기 (debug fallback) |

**API 응답 변경:**
```json
{
  "resolved_coverage_codes": ["A4200_1", "A5200", "A4210"],
  "slots": [...],
  "debug": {
    "resolved_coverage_codes": ["A4200_1", "A5200", "A4210"]
  }
}
```

**테스트 결과:**
```
47 passed (pytest tests/test_extraction.py)
Eval: 100% coverage resolve, 100% slot fill, 100% value correctness
```

**효과:**
- 슬롯 추출 로직이 coverage type별로 분리되어 확장성 향상
- 환경변수로 retrieval 파라미터 조정 가능
- API 응답에서 resolved_coverage_codes 직접 접근 가능
- 하위 호환성 유지 (eval_runner debug fallback)

---

### 40. Step U-4.12: Coverage Type 확장 + YAML 외부화 [기능]

**목표:**
- 암진단비 외 다른 담보군(뇌/심혈관, 수술비)에 대한 슬롯 정의 추가
- 슬롯 정의를 코드에서 분리하여 YAML 기반으로 관리

**구현 내용:**

**1. 새로운 Coverage Type 추가:**
```python
# 뇌/심혈관 진단비
CEREBRO_CARDIOVASCULAR_SLOTS = [
    {"slot_key": "diagnosis_lump_sum_amount", ...},
    {"slot_key": "existence_status", ...},
    {"slot_key": "waiting_period", ...},
]

# 수술비
SURGERY_BENEFIT_SLOTS = [
    {"slot_key": "surgery_amount", ...},     # stub
    {"slot_key": "surgery_count_limit", ...}, # stub
    {"slot_key": "existence_status", ...},
]
```

**2. COVERAGE_CODE_TO_TYPE 확장:**
```python
COVERAGE_CODE_TO_TYPE = {
    # 암진단비
    "A4200_1": "cancer_diagnosis",
    ...
    # 뇌/심혈관 진단비
    "A5200": "cerebro_cardiovascular_diagnosis",
    "A5210": "cerebro_cardiovascular_diagnosis",
    ...
    # 수술비
    "A6100": "surgery_benefit",
    "A6110": "surgery_benefit",
    ...
}
```

**3. YAML 외부화 (`config/slot_definitions.yaml`):**
```yaml
version: "0.2"
coverage_types:
  cancer_diagnosis:
    display_name: "암진단비"
    coverage_codes: [A4200_1, A4210, ...]
    slots:
      - slot_key: diagnosis_lump_sum_amount
        ...
  cerebro_cardiovascular_diagnosis:
    display_name: "뇌/심혈관 진단비"
    ...
  surgery_benefit:
    display_name: "수술비"
    ...
```

**4. YAML 로딩 함수:**
```python
def load_slot_definitions_from_yaml(yaml_path: str | None = None) -> dict | None:
    """YAML에서 슬롯 정의 로드 (외부화)"""

def get_slots_for_coverage_type(coverage_type: str, yaml_path: str | None = None) -> list[dict]:
    """Coverage type에 해당하는 슬롯 정의 반환"""
```

**생성된 파일:**
| 파일 | 설명 |
|------|------|
| `config/slot_definitions.yaml` | 슬롯 정의 외부 설정 파일 |

**수정된 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `services/extraction/slot_extractor.py` | CEREBRO_CARDIOVASCULAR_SLOTS, SURGERY_BENEFIT_SLOTS, YAML 로딩 함수 |

**테스트 결과:**
```
47 passed (pytest tests/test_extraction.py)
Eval: 100% coverage resolve, 100% slot fill, 100% value correctness
```

**효과:**
- 3개 coverage type 지원 (cancer_diagnosis, cerebro_cardiovascular_diagnosis, surgery_benefit)
- 슬롯 정의 외부화로 코드 변경 없이 설정 조정 가능
- stub 추출기로 향후 구현 대비

**다음 단계에서 바로 구현 가능한 항목:**
1. `cerebro_cardiovascular_diagnosis` 슬롯 추출기 구현 (diagnosis_lump_sum 재사용 가능)
2. `surgery_benefit` 전용 추출기 (surgery_amount) 구현
3. Goldset 확장 (뇌졸중, 수술비 테스트 케이스)

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
| `services/retrieval/compare_service.py` | 2-Phase Retrieval 서비스 (Step E) |
| `api/main.py` | FastAPI 앱 (Step E) |
| `api/compare.py` | /compare 라우터 (Step E) |
| `tools/load_coverage_mapping.py` | Excel → coverage_alias 로드 |
| `tools/seed_ontology_codes.py` | Ontology → 신정원 매핑 seed |
| `tools/backfill_chunk_coverage_code.py` | Chunk coverage 백필 |
| `tools/backfill_terms_for_policy.py` | 약관 재태깅 백필 |
| `tools/run_compare_smoke_tests.sh` | /compare 스모크 테스트 (Step E-1) |
| `tests/test_compare_api.py` | /compare pytest 회귀 테스트 (Step E-2) |
| `db/migrations/20251217_add_trgm_indexes.sql` | pg_trgm 인덱스 migration (Step E-3) |
| `tools/benchmark_policy_axis.py` | policy_axis 벤치마크 스크립트 (Step E-3) |
| `services/extraction/__init__.py` | Extraction 모듈 (Step H-1) |
| `services/extraction/amount_extractor.py` | 금액 추출기 (Step H-1) |
| `services/extraction/condition_extractor.py` | 지급조건 스니펫 추출기 (Step H-1) |
| `tests/test_extraction.py` | 추출기 단위 테스트 (Step H-1) |
| `tools/audit_extraction_quality.py` | 추출 품질 audit 스크립트 (Step H-1.5) |
| `services/extraction/llm_schemas.py` | LLM 추출 Pydantic 모델 (Step H-2) |
| `services/extraction/llm_prompts.py` | LLM 프롬프트 템플릿 (Step H-2) |
| `services/extraction/llm_client.py` | LLM 클라이언트 (Fake/Disabled/OpenAI) (Step H-2, H-2.1) |
| `services/extraction/pii_masker.py` | PII 마스킹 유틸리티 (Step H-2.1) |
| `tests/test_llm_refinement.py` | LLM refinement 단위 테스트 (Step H-2) |
| `tests/test_pii_masker.py` | PII 마스킹 단위 테스트 (Step H-2.1) |
| `tools/run_compare_with_llm_toggle.sh` | LLM 토글 스모크 테스트 스크립트 (Step H-2.1) |
| `services/retrieval/plan_selector.py` | Plan 자동 선택 모듈 (Step I) |
| `tools/seed_product_plans.py` | 테스트용 Plan 데이터 seed (Step I) |
| `tests/test_plan_selector.py` | Plan selector 단위 테스트 (Step I) |
| `services/ingestion/plan_detector.py` | Plan 감지 모듈 (Step I-1) |
| `tools/backfill_plan_ids.py` | plan_id 백필 도구 (Step I-1) |
| `tests/test_plan_detector.py` | Plan detector 단위 테스트 (Step I-1) |
| `tools/audit_plan_tagging.py` | Plan 태깅 품질 리포트 (Step J-1) |
| `tests/test_compare_api_plan_cases.py` | Plan 회귀 테스트 (Step J-1, J-2) |
| `data/lotte/*/*.manifest.yaml` | LOTTE 문서 manifest (plan gender) (Step J-2) |
| `data/db/가입설계서/*.manifest.yaml` | DB 가입설계서 manifest (plan age) (Step J-2) |
| `tools/audit_unassigned_plans.py` | 미태깅 원인 분류 스크립트 (Step J-3) |
| `tests/test_compare_api_plan_effects.py` | Plan 효과 E2E 테스트 (Step J-3) |
| `tests/fixtures/retrieval_cases.yaml` | 고정 질의 세트 18개 (Step K) |
| `tests/test_vector_retrieval_quality.py` | Retrieval 품질 회귀 테스트 (Step K) |
| `tools/benchmark_compare_axis.py` | 벤치마크 스크립트 (Step K) |
| `api/document_viewer.py` | PDF 페이지 렌더링 API (Step U-2) |
| `tests/test_document_viewer.py` | Document Viewer API 테스트 (Step U-2) |
| `docker-compose.demo.yml` | 데모용 Docker Compose (Step U-4) |
| `api/Dockerfile` | FastAPI 백엔드 이미지 (Step U-4) |
| `deploy/nginx.conf` | Nginx 리버스 프록시 설정 (Step U-4) |
| `tools/demo_up.sh` | 원클릭 실행 스크립트 (Step U-4, U-4.1) |
| `tools/demo_seed.sh` | 데이터 시딩 스크립트 (Step U-4.1) |
| `README.md` | 데모 실행 가이드 (Step U-4) |
| `eval/goldset_cancer_minimal.csv` | 암진단비 정답셋 4건 (Step U-4.9) |
| `eval/eval_runner.py` | Eval 실행기 (Step U-4.9) |
| `tools/run_demo_eval.sh` | 데모 신뢰성 기준선 스크립트 (Step U-4.9) |
| `docs/demo_vs_main_diff.md` | Demo vs Main 변경사항 분류 (Step U-4.10) |
| `config/slot_definitions.yaml` | 슬롯 정의 외부 설정 파일 (Step U-4.12) |

### UI 파일 (apps/web)
| 파일 | 설명 |
|------|------|
| `Dockerfile` | Next.js 프론트엔드 이미지 (Step U-4) |
| `src/app/page.tsx` | 메인 채팅 페이지 (Step U-ChatUI) |
| `src/components/ChatInput.tsx` | 채팅 입력 컴포넌트 (Step U-ChatUI) |
| `src/components/CompareTable.tsx` | 비교표 컴포넌트 (Step U-ChatUI, U-1, U-2) |
| `src/components/EvidencePanel.tsx` | 근거 자료 패널 (Step U-ChatUI, U-1, U-2) |
| `src/components/PdfPageViewer.tsx` | PDF 뷰어 컴포넌트 (Step U-2) |
| `src/lib/api.ts` | API 유틸리티 (Step U-ChatUI) |
| `src/lib/types.ts` | TypeScript 타입 정의 (Step U-ChatUI) |

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

### 완료된 단계
1. ~~Retrieval API 구현 (FastAPI)~~ ✅ Step E 완료
2. ~~비교조회 API 구현 (quota 기반 병합)~~ ✅ Step E 완료
3. ~~plan_selector 연동 (성별/나이 기반 plan 자동 선택)~~ ✅ Step I, J-3 완료
4. ~~HANWHA 가입설계서 alias 보강~~ ✅ Step D-1에서 불필요 확인
5. ~~Vector search 연동 (pgvector similarity search)~~ ✅ Step K Hybrid 옵션으로 완료
6. ~~프론트엔드 연동~~ ✅ Step U-ChatUI, U-1, U-2 완료
7. ~~Eval Framework 구축~~ ✅ Step U-4.9 완료
8. ~~Demo vs Main 분류 문서화~~ ✅ Step U-4.10 완료

### 다음 작업 후보

**우선순위 높음:**
1. ~~**Main 브랜치 병합**~~ ✅ U-4.11에서 완료
2. ~~**뇌/심혈관 진단비 추출기 구현**~~ ✅ U-4.13에서 완료
3. ~~**수술비 전용 추출기 구현**~~ ✅ U-4.13에서 완료

**우선순위 중간:**
4. **Goldset 확장** - 현재 4건 → 뇌졸중, 수술비 케이스 추가
5. **추가 보험사 데이터 적재** - 현재 SAMSUNG, MERITZ만 chunk 있음
6. **LLM 슬롯 추출 활성화** - 현재 rule-based만 사용 중
7. **UI 개선** - SlotsTable 디자인, diff 시각화

**우선순위 낮음:**
8. **coverage_code 자동 추천 개선** - similarity threshold 조정
9. **Evidence doc_type 매칭** - 현재 0% (API 응답 구조 제한)
10. 사용자 피드백 기반 개선

---

## Step U-4.13: 뇌/심혈관 + 수술비 추출기 구현 (2025-12-19)

### 구현 내용

1. **뇌/심혈관 진단비 슬롯 추출** (`cerebro_cardiovascular_diagnosis`)
   - Coverage codes: A5200 (뇌졸중), A5210 (급성심근경색), A5220 (뇌혈관질환), A5230 (허혈성심장질환)
   - 진단비 일시금 추출: 암진단비와 동일한 `diagnosis_lump_sum` 추출기 재사용
   - 슬롯: `diagnosis_lump_sum_amount`, `existence_status`, `waiting_period`

2. **수술비 슬롯 추출** (`surgery_benefit`)
   - Coverage codes: A6100 (질병수술비), A6110 (상해수술비), A6120 (암수술비), A6130 (1~5종수술비)
   - 신규 추출기:
     - `extract_surgery_amount()`: 수술비 금액 추출 (premium 패턴 제외)
     - `extract_surgery_count_limit()`: 수술 횟수 제한 추출 (연 N회, 통산 N회 등)
   - 슬롯: `surgery_amount`, `surgery_count_limit`, `existence_status`

3. **2-pass Retrieval 키워드 확장**
   - `POLICY_KEYWORD_PATTERNS` 22개로 확장
   - 뇌/심혈관: 뇌졸중, 급성심근경색, 뇌혈관, 허혈성심장
   - 수술비: 수술비, 종수술, 수술급여, 수술보험금

4. **Coverage type별 슬롯 추출 라우팅**
   - `_determine_coverage_type()`: coverage_codes → coverage_type 결정
   - `extract_slots()`: coverage_type별 전용 추출 함수 호출
     - `_extract_cancer_diagnosis_slots()`
     - `_extract_cerebro_cardiovascular_slots()`
     - `_extract_surgery_benefit_slots()`

### 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `services/extraction/amount_extractor.py` | +257 lines: 수술비/횟수제한 추출 로직 |
| `services/extraction/slot_extractor.py` | +288 lines: 다중 coverage_type 슬롯 추출 |
| `services/retrieval/compare_service.py` | +35 lines: 키워드 확장 |

### 검증 결과

```
✅ pytest tests/test_extraction.py: 47 passed
✅ eval/eval_runner.py: 100% value correctness (4/4)
```
