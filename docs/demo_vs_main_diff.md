# Demo vs Main 변경사항 분류

> 작성일: 2025-12-19
> 기준 커밋: `a888f72` (Add comparison slots and fix amount extraction)

---

## 1. 공통 반영해야 하는 변경 (Main/Dev 병합 대상)

### 1.1 Core Extraction Logic

| 파일 | 변경 내용 | 중요도 |
|------|----------|--------|
| `services/extraction/amount_extractor.py` | LUMP_SUM 키워드 추가, premium-negative 거리 비교 로직, 진단비 일시금 전용 추출 | **Critical** |
| `services/extraction/slot_extractor.py` | 신규 - 슬롯 기반 추출 모듈 (payout_amount, existence_status 등) | **Critical** |
| `services/extraction/llm_trace.py` | 신규 - LLM 사용 추적 데이터클래스 | Medium |

**변경 이유:**
- Samsung 3,000만원 금액 추출 버그 수정 (was "미확인")
- 보험료(premium) vs 진단비(payout) 구분 정확도 향상
- confidence 우선순위 (high > medium within same doc_type)

### 1.2 Retrieval Service

| 파일 | 변경 내용 | 중요도 |
|------|----------|--------|
| `services/retrieval/compare_service.py` | 2-pass amount-bearing retrieval, slots 통합, preview 1000자 확대 | **Critical** |

**변경 이유:**
- 1차 검색에서 금액을 못 찾을 경우 fallback 검색 추가
- 슬롯 기반 비교 결과 제공

### 1.3 API Layer

| 파일 | 변경 내용 | 중요도 |
|------|----------|--------|
| `api/compare.py` | slots 필드 추가, CompareResponse 확장 | High |
| `api/main.py` | (minor) 라우터 변경 없음 | Low |

### 1.4 Database

| 파일 | 변경 내용 | 중요도 |
|------|----------|--------|
| `db/migrations/20251218_add_comparison_slots.sql` | slot_definition 테이블 (optional) | Low |

### 1.5 Tests

| 파일 | 변경 내용 | 중요도 |
|------|----------|--------|
| `tests/test_extraction.py` | 47개 테스트 (금액 추출, confidence priority, lump-sum) | **Critical** |

### 1.6 UI Components

| 파일 | 변경 내용 | 중요도 |
|------|----------|--------|
| `apps/web/src/components/SlotsTable.tsx` | 신규 - 슬롯 비교 테이블 UI | High |
| `apps/web/src/components/EvidencePanel.tsx` | 확장 - 슬롯 근거 표시 | Medium |
| `apps/web/src/lib/types.ts` | 슬롯 타입 정의 추가 | Medium |

---

## 2. 데모 전용으로 남길 변경 (Main 병합 불필요)

| 파일 | 역할 | 이유 |
|------|------|------|
| `docker-compose.demo.yml` | 데모 환경 Docker 구성 | 프로덕션과 다른 설정 |
| `tools/run_demo_eval.sh` | 데모 신뢰성 기준선 스크립트 | 데모 검증 전용 |
| `eval/goldset_cancer_minimal.csv` | 데모용 정답셋 (4건) | 데모 검증 전용 |
| `eval/eval_runner.py` | 데모 평가 실행기 | 데모 검증 전용 |
| `eval/goldset_u48_slots.csv` | U-48 슬롯 테스트셋 | 데모 검증 전용 |
| `tools/audit_slots.py` | 슬롯 완성도 검증 | 데모/개발 검증용 |
| `tools/demo_*.sh` | 데모 전용 스크립트들 | 데모 환경 전용 |
| `tools/run_u48_eval.sh` | U-48 평가 스크립트 | 데모 검증 전용 |
| `tools/run_llm_trace_smoke.sh` | LLM 추적 스모크 테스트 | 개발 검증용 |

---

## 3. 리스크/장점 분석

### 3.1 공통 반영 시 장점

1. **금액 추출 정확도 향상**: premium vs payout 구분 개선
2. **슬롯 기반 비교**: 구조화된 비교 결과 제공
3. **47개 테스트**: regression 방지

### 3.2 공통 반영 시 리스크

1. **기존 동작 변경**: amount_extractor의 LUMP_SUM 로직이 다른 담보군에 영향 가능
   - **완화**: 47개 테스트로 regression 검증
2. **API 응답 변경**: slots 필드 추가
   - **완화**: 추가 필드이므로 하위 호환성 유지

### 3.3 데모 전용 유지 시 장점

1. **프로덕션 안정성**: 데모 검증 스크립트가 프로덕션에 영향 없음
2. **유연성**: 데모 환경 독립적 변경 가능

### 3.4 데모 전용 유지 시 리스크

1. **낮음**: 데모 스크립트는 core 로직과 분리됨

---

## 4. 본선 반영 전략

### 4.1 권장 전략: 전체 커밋 체리픽

```bash
# main 브랜치에서
git cherry-pick a888f72
```

**이유**: 커밋 `a888f72`는 이미 잘 구성되어 있고, 테스트가 포함되어 있음.

### 4.2 대안: PR 기반 병합

```bash
# feature 브랜치 생성
git checkout -b feature/comparison-slots main
git cherry-pick a888f72

# PR 생성
gh pr create --title "feat: Add comparison slots and fix amount extraction" \
  --body "Cherry-pick from demo branch (a888f72)"
```

---

## 5. 반영 후 체크리스트

### 5.1 테스트 검증

```bash
# 1. 기존 테스트 통과 확인
python -m pytest tests/test_extraction.py -v

# 2. API 동작 확인
curl -s http://localhost:8000/compare -H "Content-Type: application/json" -d '{
  "query": "암진단비(유사암제외)",
  "insurers": ["SAMSUNG", "MERITZ"]
}' | jq '.slots[] | select(.slot_key == "payout_amount") | .insurers[].value'
# 기대: "3,000만원" x2
```

### 5.2 Demo 재현 확인

```bash
# 데모 환경에서 동일하게 동작하는지 확인
./tools/run_demo_eval.sh

# 기대 결과:
# - Slot fill rate: 100%
# - Value correctness: 100%
```

### 5.3 Regression 체크 항목

| 항목 | 확인 방법 | 기대 결과 |
|------|----------|----------|
| Samsung 암진단비 금액 | API 호출 | 3,000만원 |
| Meritz 암진단비 금액 | API 호출 | 3,000만원 |
| 47 extraction tests | pytest | PASS |
| slot fill rate | audit_slots.py | 100% |

---

## 6. 결론

| 분류 | 파일 수 | 권장 조치 |
|------|--------|----------|
| 공통 반영 | 12개 | `a888f72` 체리픽 |
| 데모 전용 | 9개 | 현재 상태 유지 |

**핵심**: `a888f72` 커밋은 그대로 main에 병합 가능. 데모 전용 파일들은 별도 관리.
