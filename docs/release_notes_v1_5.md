# V1.5 Release Notes — Subtype Anchor Map & Safe Resolution

**릴리즈 일시**: 2025-12-23
**커밋**: `e9ae71d` (V1.5-HOTFIX 포함)

---

## 개요

V1.5는 Subtype-only 질의(경계성종양, 제자리암 등)에 대한 UX 개선을 제공합니다.
v1 로직을 깨지 않으면서 안전한 anchor 후보를 제시하여 사용자가 올바른 담보를 선택하도록 유도합니다.

---

## 핵심 변경 사항

### 1. SAFE_RESOLVED 상태 추가

- 기존 상태: `RESOLVED`, `UNRESOLVED`, `INVALID`
- 신규 상태: `SAFE_RESOLVED`
- 조건: subtype-only 질의 + allowed_anchor 1개 + evidence >= 1

### 2. 허용 Subtype 범위 (2개만)

| Subtype ID | 키워드 | allowed_anchor |
|------------|--------|----------------|
| `borderline_tumor` | 경계성종양, 경계성 종양, 경계성 | A4210 (유사암진단비) |
| `carcinoma_in_situ` | 제자리암, 상피내암, 제자리 암, 상피내 암 | A4210 (유사암진단비) |

### 3. 질병명 SAFE_RESOLVED 금지

다음 질병명/암종명은 SAFE_RESOLVED가 발생하지 않습니다:

- 갑상선암, 대장암, 폐암, 유방암, 전립선암
- 소액암, 기타피부암, 대장점막내암
- 유사암 (담보명으로 취급)

### 4. anchor_exclusion_keywords

다음 키워드가 질의에 포함되면 subtype-only로 판정하지 않습니다:

- 암진단비, 유사암진단비, 재진단암진단비
- 암수술비, 다빈치, 로봇수술
- 진단비, 유사암

### 5. explanation_context_keywords

다음 키워드가 포함되면 정보 질의로 판단하여 SAFE_RESOLVED하지 않습니다:

- 제외, 않는, 아닌, 안되
- 뜻, 이란, 무엇, 설명, 정의, 경우

---

## 경계 봉인 선언

### v1 비파괴 원칙 유지

- 기존 RESOLVED/UNRESOLVED/INVALID 상태 흐름 완전 유지
- 기존 coverage resolution 로직 변경 없음
- locked_coverage_codes 동작 변경 없음

### SAFE_RESOLVED 범위 제한

- **허용**: 경계성종양, 제자리암 (2개 subtype만)
- **금지**: 질병명, 암종명, 담보명, 설명/조건 문맥

### 전 보험사 검증 완료

8개 보험사 기준 전수 검증:
- SAMSUNG, MERITZ, LOTTE, KB, DB, HANWHA, HEUNGKUK, HYUNDAI

---

## 설정 파일

### config/subtype_anchor_map.yaml

```yaml
subtypes:
  borderline_tumor:
    keywords:
      - 경계성종양
      - 경계성 종양
      - 경계성
    allowed_anchors:
      - A4210
    anchor_basis: "경계성종양은 유사암 범주에 포함됨"
    domain: CANCER

  carcinoma_in_situ:
    keywords:
      - 제자리암
      - 상피내암
      - 제자리 암
      - 상피내 암
    allowed_anchors:
      - A4210
    anchor_basis: "제자리암은 유사암 범주에 포함됨"
    domain: CANCER

safe_resolution:
  enabled: true
  min_evidence_count: 1

anchor_exclusion_keywords:
  - 암진단비
  - 유사암진단비
  - 유사암
  - 진단비
  # ...

explanation_context_keywords:
  - 제외
  - 무엇
  - 설명
  # ...
```

---

## 관련 커밋

| 커밋 | 설명 |
|------|------|
| `68db005` | V1.5-PRECHECK: 대표 3사 오매칭 방지 |
| `f5c7039` | V1.5-HOTFIX: 질병명 SAFE_RESOLVED 금지 |
| `e9ae71d` | config/ 바인드 마운트 추가 |

---

## 검증 결과

### 질병명 SAFE_RESOLVED 금지

| 질의 | status | SAFE_RESOLVED |
|------|--------|---------------|
| 갑상선암 | RESOLVED | ❌ |
| 대장암 | UNRESOLVED | ❌ |
| 폐암 | INVALID | ❌ |
| 유방암 | UNRESOLVED | ❌ |
| 전립선암 | UNRESOLVED | ❌ |

### subtype-only 허용 범위

| 질의 | status | code |
|------|--------|------|
| 경계성종양 | SAFE_RESOLVED | A4210 |
| 제자리암 | SAFE_RESOLVED | A4210 |
| 암진단비 경계성종양 포함 | UNRESOLVED | - |
| 경계성종양이란 무엇 | UNRESOLVED | - |

---

## 다음 버전 예정

- v1.6: Subtype 다중 선택 UX 개선
- v1.7: anchor 후보 신뢰도 기반 정렬

---

*Generated: 2025-12-23*
