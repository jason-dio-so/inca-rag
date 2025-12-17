# 보험 약관 비교 RAG 시스템

## 프로젝트 목적
보험사(insurer) + 상품(product) + 플랜(plan) 단위로 약관/사업방법서/상품요약서/가입설계서를 구조화하고, 비교조회(coverage comparison)를 정확하게 수행하는 시스템

---

## 1. 기술 스택 / 전제
- Backend: FastAPI (Python)
- DB: Postgres + pgvector
- Vector Search + Metadata Filter 병행
- **보험사 영문 명칭은 `carrier`가 아니라 `insurer`를 사용한다 (중요)**
- IDE는 VS Code, 코드 실행은 로컬 Docker 환경

---

## 2. 도메인 모델 (핵심 개념)

### (1) insurer
- 보험사 (예: 삼성화재, 롯데손보, DB손보)

### (2) product
- 보험 상품 (보험사별로 관리)
- 같은 상품이라도 version(예: 2511) 존재

### (3) product_plan (매우 중요)
- 같은 상품 내의 플랜/변형
- 예:
  - 남/여
  - 연령대 (40세 이하 / 41세 이상)
  - 종(1종/3종/4종), 형(1형/2형)
- **plan_id가 NULL이면 "공통 문서"**

### (4) document
- 약관 / 사업방법서 / 상품요약서 / 가입설계서
- sha256으로 동일 문서 중복 방지

### (5) chunk
- 문서를 잘라 만든 최소 검색 단위
- pgvector embedding 포함
- JSONB meta에 coverage_code(담보 표준코드) 포함

---

## 3. 핵심 설계 원칙

### A. Plan 자동 선택
- 질의에서 성별/나이를 추출
- 가능한 경우 plan_id 자동 선택
- 검색은 항상: **plan 우선 → 공통(plan_id IS NULL) fallback**

### B. 비교조회 전략
- 단일조회: insurer + product 기준
- 비교조회: 여러 insurer+product를 받아 타겟별로 검색 후 병합
- **타겟별 쏠림 방지를 위해 quota 기반 병합 사용**

### C. 담보 비교는 keyword가 아니라 coverage_code 기준
- 예:
  - `CIS_CARCINOMA` = 제자리암
  - `BORDERLINE_TUMOR` = 경계성종양
- `chunk.meta.entities.coverage_code`에 사전 주입

---

## 4. 현재 준비된 상태
- DB schema.sql (Postgres + pgvector) 초안 있음
- FastAPI retrieval/search, compare-targets 설계 완료
- plan_selector 로직(질의 → gender/age 추출) 있음
- 임베딩은 현재 더미 → 실제 임베딩으로 교체 예정

---

## 5. 쉬운요약서 처리 규칙 (고정)

### 규칙 1. doc_type 고정
- 파일명에 `쉬운요약서`, `쉬운 요약서`, `easy`가 포함되어도 **doc_type은 항상 `상품요약서`**

### 규칙 2. subtype으로만 구분
```yaml
# 쉬운요약서
doc_type: 상품요약서
document:
  meta:
    subtype: easy

# 일반 상품요약서
doc_type: 상품요약서
document:
  meta:
    subtype: standard
```

### 규칙 3. 폴더 구조
- 쉬운요약서 PDF는 반드시 `data/<INSURER>/상품요약서/` 아래
- `data/<INSURER>/쉬운요약서/` 폴더는 금지

### 규칙 4. retrieval/비교조회 전제
- `WHERE doc_type = '상품요약서'`를 기준으로 동작
- 쉬운요약서를 doc_type으로 분리하면 안 됨

### 규칙 5. 적용 범위
- 삼성뿐 아니라 모든 보험사의 easy summary에 동일 적용

---

## 6. 개발 규칙
- 기존 설계를 임의로 단순화하거나 바꾸지 말 것
- 보험 도메인 특성을 고려하여 구현
- 불확실한 부분은 반드시 질문 후 진행
