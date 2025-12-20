# API Sync Audit Report - 2025-12-20

## 1. 목적

STEP 4.2 DB 복구 안정화 후, API가 정상적으로 coverage 추천을 반환하는지 검증.

---

## 2. 컨테이너 코드 동기화 방식

### 확인 결과

- **방식**: 이미지 빌드 방식 (코드 볼륨 마운트 없음)
- **근거**: `docker-compose.demo.yml`의 api 서비스에 소스 코드 마운트 없음
  - `./data:/app/data:ro` (데이터만 마운트)
  - `api_page_cache:/app/artifacts/page_cache` (캐시만 마운트)
- **파일 일치 확인**: 컨테이너 내부 파일 라인 수 = 로컬 파일 라인 수 (2026 lines)

### 표준 재빌드 명령

```bash
docker compose -f docker-compose.demo.yml build api && \
docker compose -f docker-compose.demo.yml up -d api
```

---

## 3. 테스트 시나리오 결과

| 시나리오 | 질의 | 기대 결과 | 실제 결과 | 상태 |
|----------|------|-----------|-----------|------|
| A | "다빈치 수술비 비교" | UNRESOLVED + 후보>=1 | UNRESOLVED + 3개 | PASS |
| B | "삼성과 현대 다빈치 수술비를 비교해줘" | UNRESOLVED/RESOLVED + 후보>=1 | UNRESOLVED + 3개 | PASS |
| C | "경계성 종양 보장 비교" | RESOLVED/UNRESOLVED + 후보>=1 | UNRESOLVED + 2개 | PASS |
| D | "피자 추천" | INVALID | INVALID + 0개 | PASS |

---

## 4. DB 조회 vs API 응답 비교

### 시나리오 A: "다빈치 수술비 비교" (SAMSUNG, HYUNDAI)

**DB 직접 조회 (similarity >= 0.1)**:
| insurer_code | coverage_code | raw_name_norm | sim |
|--------------|---------------|---------------|-----|
| SAMSUNG | A9630_1 | [갱신형]특정암 다빈치로봇 수술비(1년 감액) | 0.1923 |
| SAMSUNG | A9630_1 | [갱신형]암(특정암 제외)다빈치로봇 수술비(1년 감액) | 0.1613 |
| SAMSUNG | A5298_001 | 갑상선암 수술비 | 0.1429 |
| SAMSUNG | A5298_001 | 제자리암 수술비 | 0.1429 |
| ... | ... | ... | ... |

**API 응답 (coverage_resolution.suggested_coverages)**:
```json
[
  {"coverage_code": "A9630_1", "coverage_name": "다빈치로봇암수술비", "similarity": 0.1923},
  {"coverage_code": "A5298_001", "coverage_name": "유사암수술비", "similarity": 0.1429},
  {"coverage_code": "A5200", "coverage_name": "암수술비(유사암 제외)", "similarity": 0.1111}
]
```

**결론**: DB 조회 결과와 API 응답이 일치함.

---

### 시나리오 C: "경계성 종양 보장 비교" (SAMSUNG, MERITZ)

**DB 직접 조회 (similarity >= 0.1)**:
| insurer_code | coverage_code | raw_name_norm | sim |
|--------------|---------------|---------------|-----|
| SAMSUNG | A5298_001 | 경계성종양 수술비 | 0.3846 |
| SAMSUNG | A4210 | 유사암 진단비(경계성종양)(1년50%) | 0.2273 |

**API 응답 (coverage_resolution.suggested_coverages)**:
```json
[
  {"coverage_code": "A5298_001", "coverage_name": "유사암수술비", "similarity": 0.3846},
  {"coverage_code": "A4210", "coverage_name": "유사암진단비", "similarity": 0.2273}
]
```

**결론**: DB 조회 결과와 API 응답이 일치함.

---

## 5. Resolution State 로직 확인

### 현재 임계값 설정

```yaml
thresholds:
  confident: 0.5      # RESOLVED 판정 임계값
  suggest: 0.2        # 추천 표시 임계값
  minimum: 0.1        # DB 조회 최소 임계값
```

### 상태 분류 로직

1. **INVALID**: candidates == 0 (후보 없음)
2. **RESOLVED**:
   - (candidates == 1 && similarity >= 0.5) OR
   - (best_similarity >= 0.5 && gap >= 0.15) OR
   - (best_similarity >= 0.9)
3. **UNRESOLVED**: candidates >= 1 but not confident (사용자 선택 필요)

---

## 6. 초기 오진 원인

초기 테스트에서 `suggested_coverages=0`으로 잘못 판단한 원인:

- **잘못된 필드 확인**: 최상위 `suggested_coverages` 필드 확인 (존재하지 않음)
- **올바른 필드**: `coverage_resolution.suggested_coverages` (정상 데이터 존재)

`CompareResponseModel`에는 최상위 `suggested_coverages` 필드가 없으며,
`coverage_resolution: CoverageResolutionResponse` 내에 `suggested_coverages`가 포함됨.

---

## 7. 결론

- **DB 동기화**: STEP 4.2로 coverage_standard 28개, coverage_alias 264개 정상 적재
- **API 동기화**: 컨테이너 코드와 로컬 코드 일치 (2026 lines)
- **추천 기능**: `coverage_resolution.suggested_coverages`로 정상 제공
- **코드 수정 불필요**: API는 설계대로 정상 작동 중

---

## 8. 표준 운영 절차

### DB 초기화 + Coverage 적재

```bash
./tools/reset_db_option_a_plus.sh
```

### API 컨테이너 재빌드

```bash
docker compose -f docker-compose.demo.yml build api && \
docker compose -f docker-compose.demo.yml up -d api
```

### 검증

```bash
curl -s http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"query": "다빈치 수술비 비교", "insurers": ["SAMSUNG", "HYUNDAI"]}' \
  | jq '.coverage_resolution.suggested_coverages | length'
# 기대 결과: 3 이상
```
