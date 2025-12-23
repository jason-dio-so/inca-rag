# 디버깅 레포트: "삼성생명의 경계성종양 암진단시 담보가 얼마야" 질의 분석

## 1. 문제 상황

### 1.1 원본 질의
```
"삼성생명의 경계성종양 암진단시 담보가 얼마야"
```

### 1.2 기대 결과
- 삼성화재의 경계성종양 진단비 담보 금액: **600만원**
- 담보: 유사암 진단비(경계성종양)(1년50%)

### 1.3 실제 결과
```json
{
  "resolution_state": "UNRESOLVED",
  "resolved_coverage_code": null,
  "message": "입력하신 담보명과 정확히 일치하는 항목이 없습니다. 아래 담보 중 하나를 선택해 주세요:"
}
```

---

## 2. 디버깅 과정

### 2.1 Step 1: Docker 환경 확인

**명령어:**
```bash
docker ps --format "{{.Names}}"
```

**결과:**
```
inca_demo_nginx
inca_demo_web
inca_demo_api
inca_demo_db
```

**결론:** Demo 환경 정상 가동 중

---

### 2.2 Step 2: API 응답 분석

**명령어:**
```bash
curl -s 'http://localhost:8000/compare' \
  -H 'Content-Type: application/json' \
  -d '{"query":"삼성생명의 경계성종양 암진단시 담보가 얼마야","insurers":[]}'
```

**핵심 debug 정보:**
```json
{
  "coverage_resolution": {
    "status": "UNRESOLVED",
    "best_similarity": 0.2381,
    "best_code": "A5298_001",
    "reason": "candidates_not_confident"
  },
  "recommended_coverage_details": [
    {
      "coverage_code": "A5298_001",
      "coverage_name": "유사암수술비",
      "raw_name": "경계성종양 수술비",
      "similarity": 0.2381
    },
    {
      "coverage_code": "A4210",
      "coverage_name": "유사암진단비",
      "raw_name": "유사암 진단비(경계성종양)(1년50%)",
      "similarity": 0.1667
    }
  ]
}
```

**문제 식별:**
- `best_similarity = 0.2381` < `confident_threshold = 0.5`
- "경계성종양 암진단"이라는 쿼리에 대해 similarity가 너무 낮음
- "경계성종양 수술비"가 "경계성종양 진단비"보다 높은 점수를 받음

---

### 2.3 Step 3: DB에서 coverage_alias 직접 조회

**명령어:**
```bash
docker exec inca_demo_db psql -U postgres -d inca_rag -c "
SELECT ca.raw_name, ca.coverage_code, cs.coverage_name
FROM coverage_alias ca
JOIN insurer i ON ca.insurer_id = i.insurer_id
LEFT JOIN coverage_standard cs ON cs.coverage_code = ca.coverage_code
WHERE i.insurer_code = 'SAMSUNG'
  AND ca.raw_name ILIKE '%경계성%'
ORDER BY ca.coverage_code;
"
```

**결과:**
| raw_name | coverage_code | coverage_name |
|----------|---------------|---------------|
| 경계성종양 수술비 | A5298_001 | 유사암수술비 |
| 유사암 진단비(경계성종양)(1년50%) | A4210 | 유사암진단비 |

**발견:**
- "경계성종양 암진단비"라는 직접적인 alias가 **존재하지 않음**
- 사용자가 말하는 "경계성종양 암진단시 담보"는 실제로 "유사암 진단비(경계성종양)"를 의미
- pg_trgm similarity 계산 시 "경계성종양암진단" vs "유사암 진단비(경계성종양)(1년50%)"는 낮은 점수

---

### 2.4 Step 4: 암진단비 전체 alias 확인

**명령어:**
```bash
docker exec inca_demo_db psql -U postgres -d inca_rag -c "
SELECT ca.raw_name, ca.coverage_code, cs.coverage_name
FROM coverage_alias ca
JOIN insurer i ON ca.insurer_id = i.insurer_id
LEFT JOIN coverage_standard cs ON cs.coverage_code = ca.coverage_code
WHERE i.insurer_code = 'SAMSUNG'
  AND (ca.raw_name ILIKE '%암진단%' OR ca.coverage_code LIKE 'A42%')
ORDER BY ca.coverage_code;
"
```

**결과:**
| raw_name | coverage_code | coverage_name |
|----------|---------------|---------------|
| 암진단비(유사암제외) | A4200_1 | 암진단비(유사암제외) |
| 유사암 진단비(대장점막내암)(1년50%) | A4210 | 유사암진단비 |
| 유사암 진단비(제자리암)(1년50%) | A4210 | 유사암진단비 |
| 유사암 진단비(갑상선암)(1년50%) | A4210 | 유사암진단비 |
| 유사암 진단비(기타피부암)(1년50%) | A4210 | 유사암진단비 |
| 유사암 진단비(경계성종양)(1년50%) | A4210 | 유사암진단비 |
| 신재진단암(기타피부암 및 갑상선암 포함) 진단비(1년주기,5회한) | A4299_1 | 재진단암진단비 |

**핵심 발견:**
- 삼성화재에서 "경계성종양"은 **유사암의 하위 유형**
- 담보 구조: `암진단비(유사암제외)` + `유사암 진단비(경계성종양)`
- 경계성종양은 A4210 (유사암진단비)에 매핑됨

---

### 2.5 Step 5: 정확한 담보명으로 테스트

**테스트 1: "삼성 암진단비(유사암제외)"**
```bash
curl -s 'http://localhost:8000/compare' \
  -H 'Content-Type: application/json' \
  -d '{"query":"삼성 암진단비(유사암제외)","insurers":["SAMSUNG"]}'
```

**결과:**
```json
{
  "resolution_state": "RESOLVED",
  "resolved_coverage_code": "A4200_1",
  "comparison_mode": "SUBTYPE",
  "amount_value": 30000000  // 3,000만원
}
```

**테스트 2: 슬롯 추출 확인**
```json
{
  "slots": [
    {"slot_key": "existence_status", "value": "있음"},
    {"slot_key": "subtype_borderline_covered", "value": "Unknown"},
    {"slot_key": "subtype_similar_cancer_covered", "value": "Y"},
    {"slot_key": "partial_payment_rule", "value": "1년이내 50%"}
  ]
}
```

**발견:**
- 암진단비(유사암제외): 3,000만원 ✓
- subtype_borderline_covered가 "Unknown"으로 나옴 → 슬롯 추출 로직 개선 필요

---

### 2.6 Step 6: Chunk 데이터 직접 확인

**명령어:**
```bash
docker exec inca_demo_db psql -U postgres -d inca_rag -c "
SELECT LEFT(content, 500), page_start, doc_type
FROM chunk c
JOIN insurer i ON c.insurer_id = i.insurer_id
WHERE i.insurer_code = 'SAMSUNG'
  AND content ILIKE '%경계성종양%'
ORDER BY page_start
LIMIT 3;
"
```

**결과 (page 5, 가입설계서):**
```
유사암 진단비(경계성종양)(1년50%) 보험기간 중 경계성종양으로 진단 확정된 경우
가입금액 지급(각각 최초 1회한)
※ 최초 보험가입후 1년 미만에 보험금 지급사유가 발생한 경우 50% 감액 지급
600만원
```

**핵심 정보 추출:**
- **담보명**: 유사암 진단비(경계성종양)(1년50%)
- **금액**: 600만원
- **조건**: 1년 미만 시 50% 감액

---

## 3. 문제 원인 분석

### 3.1 Coverage Resolution 실패 원인

| 원인 | 상세 |
|------|------|
| **Alias 불일치** | 사용자: "경계성종양 암진단" vs DB: "유사암 진단비(경계성종양)" |
| **Similarity 부족** | 0.2381 < 0.5 (confident threshold) |
| **도메인 혼동** | "경계성종양 수술비"가 "경계성종양 진단비"보다 높은 점수 |

### 3.2 시스템 설계 한계

1. **Subtype-only 질의 처리**
   - "경계성종양"만으로는 상위 담보(암진단비 vs 유사암진단비)를 확정할 수 없음
   - 설계 의도: 사용자에게 명확한 선택을 요청

2. **담보 구조의 복잡성**
   ```
   암 관련 담보 구조:
   ├── 암진단비(유사암제외) [A4200_1] - 3,000만원
   └── 유사암진단비 [A4210]
       ├── 기타피부암 - 600만원
       ├── 갑상선암 - 600만원
       ├── 대장점막내암 - 600만원
       ├── 제자리암 - 600만원
       └── 경계성종양 - 600만원 ← 사용자가 원하는 정보
   ```

---

## 4. 해결 방법

### 4.1 방법 1: 정확한 담보명 사용 (권장)

**쿼리:**
```
"삼성 암진단비(유사암제외)"
또는
"삼성 유사암진단비"
```

**결과:**
- RESOLVED 상태
- 암진단비: 3,000만원
- 유사암 진단비(경계성종양): 600만원 (evidence에서 확인)

### 4.2 방법 2: Anchor 기반 후속 질의

**Step 1:** 먼저 "삼성 암진단비"로 조회하여 Anchor 생성
**Step 2:** 후속 질의 "경계성종양 금액"으로 subtype 슬롯 확인

### 4.3 방법 3: locked_coverage_codes 사용 (API 직접 호출 시)

```bash
curl -s 'http://localhost:8000/compare' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "경계성종양 보장금액",
    "insurers": ["SAMSUNG"],
    "locked_coverage_codes": ["A4210"]
  }'
```

---

## 5. 시스템 개선 제안

### 5.1 단기 개선

| 항목 | 내용 |
|------|------|
| **Alias 추가** | "경계성종양 진단비" → A4210 매핑 추가 |
| **Subtype 인식 강화** | "경계성종양", "제자리암" 키워드 시 자동으로 암 도메인 인식 |
| **사용자 안내 개선** | UNRESOLVED 시 더 구체적인 suggested_coverages 제공 |

### 5.2 장기 개선

| 항목 | 내용 |
|------|------|
| **의도 추론 강화** | "경계성종양 암진단" → 암 domain + borderline subtype 자동 추론 |
| **Slot 추출 개선** | subtype_borderline_covered 슬롯에서 금액까지 추출 |
| **UI 개선** | 경계성종양 선택 시 관련 금액 즉시 표시 |

---

## 6. 정답 확인

### 6.1 삼성화재 경계성종양 암진단 담보 정보

| 항목 | 값 |
|------|-----|
| **담보명** | 유사암 진단비(경계성종양)(1년50%) |
| **coverage_code** | A4210 |
| **가입금액** | 600만원 |
| **1년 미만 지급률** | 50% (300만원) |
| **1년 이후 지급률** | 100% (600만원) |
| **지급 조건** | 경계성종양으로 진단 확정 시 (최초 1회한) |

### 6.2 관련 담보 전체

| 담보명 | 금액 | coverage_code |
|--------|------|---------------|
| 암 진단비(유사암 제외) | 3,000만원 | A4200_1 |
| 유사암 진단비(기타피부암) | 600만원 | A4210 |
| 유사암 진단비(갑상선암) | 600만원 | A4210 |
| 유사암 진단비(대장점막내암) | 600만원 | A4210 |
| 유사암 진단비(제자리암) | 600만원 | A4210 |
| 유사암 진단비(경계성종양) | 600만원 | A4210 |

---

## 7. 디버깅 요약

### 7.1 디버깅 흐름

```
질의 입력
    ↓
API 응답 확인 (UNRESOLVED)
    ↓
debug.coverage_resolution 분석 (similarity 0.2381 < 0.5)
    ↓
DB 직접 조회 (coverage_alias 테이블)
    ↓
Alias 불일치 발견 ("경계성종양 암진단" vs "유사암 진단비(경계성종양)")
    ↓
정확한 담보명으로 재테스트 (RESOLVED)
    ↓
Chunk 데이터에서 금액 확인 (600만원)
    ↓
정답 도출 완료
```

### 7.2 사용된 도구

| 도구 | 용도 |
|------|------|
| `curl` | API 호출 |
| `docker exec psql` | DB 직접 조회 |
| `python -m json.tool` | JSON 포맷팅 |
| `grep` | 응답 필터링 |

### 7.3 핵심 테이블

| 테이블 | 역할 |
|--------|------|
| `coverage_alias` | 담보명 → coverage_code 매핑 |
| `coverage_standard` | 신정원 표준 담보 정보 |
| `chunk` | 문서 청크 (금액/조건 정보) |
| `insurer` | 보험사 정보 |

---

## 8. 결론

**질의**: "삼성생명의 경계성종양 암진단시 담보가 얼마야"

**정답**: **600만원** (유사암 진단비(경계성종양)(1년50%))
- 1년 미만: 50% 감액 → 300만원
- 1년 이후: 100% → 600만원

**UNRESOLVED 원인**:
- 사용자 질의 "경계성종양 암진단"과 DB alias "유사암 진단비(경계성종양)"의 similarity 부족
- Subtype-only 질의로 인한 상위 담보 미확정

**해결 방법**:
- 정확한 담보명 "암진단비(유사암제외)" 또는 "유사암진단비" 사용
- 또는 coverage_alias에 "경계성종양 진단비" alias 추가

---

*레포트 생성일: 2025-12-23*
*시스템 버전: recovery/step-3.7-delta-beta*
