# INCA-RAG 프로젝트 재개 가이드

## 현재 상태 (2025-12-18)

### 완료된 작업
- [x] 금액 미확인 버그 수정 (Samsung/Meritz "3,000만원" 정상 출력)
- [x] Git 커밋: `a888f72` - slot extraction, 2-pass retrieval, confidence priority
- [x] coverage_alias 테이블 264개 매핑 적재 완료
- [x] 47개 extraction 테스트 통과
- [x] audit_slots.py 100% slot fill rate

### 미커밋 파일 (필요시 확인)
```
status.md, docs/, eval/, ontology/, ops/
```

---

## 재접속 시 체크리스트

### 1. Docker 상태 확인
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep inca
```

### 2. 컨테이너가 내려가 있으면 시작
```bash
docker compose -f docker-compose.demo.yml up -d
```

### 3. API 동작 확인
```bash
curl -s http://localhost:8000/compare -H "Content-Type: application/json" -d '{
  "query": "암진단비(유사암제외)",
  "insurers": ["SAMSUNG", "MERITZ"],
  "age": 40,
  "gender": "F"
}' | jq '.slots[] | select(.slot_key == "payout_amount") | .insurers'
```

**기대 결과:** SAMSUNG, MERITZ 모두 "3,000만원"

### 4. 테스트 실행
```bash
python -m pytest tests/test_extraction.py -v
python tools/audit_slots.py
```

---

## 핵심 파일 위치

| 파일 | 역할 |
|------|------|
| `services/extraction/slot_extractor.py` | 슬롯 추출 (payout_amount 등) |
| `services/extraction/amount_extractor.py` | 금액 추출 로직 |
| `services/retrieval/compare_service.py` | coverage 추천, 2-pass retrieval |
| `data/담보명mapping자료.xlsx` | 담보명 매핑 원본 |
| `tools/audit_slots.py` | 슬롯 완성도 검증 |

---

## DB 접속

```bash
docker exec -it inca_demo_db psql -U postgres -d inca_rag
```

**주요 테이블:**
- `insurer` - 8개 보험사
- `coverage_alias` - 담보명 → coverage_code 매핑 (264건)
- `coverage_standard` - 표준 coverage_code
- `chunk` - 문서 청크 + embedding

---

## 다음 작업 후보

1. **추가 보험사 데이터 적재** - 현재 SAMSUNG, MERITZ만 chunk 있음
2. **LLM 슬롯 추출 활성화** - 현재 rule-based만 사용 중
3. **UI 개선** - SlotsTable 디자인, diff 시각화
4. **coverage_code 자동 추천 개선** - similarity threshold 조정

---

## 빠른 빌드 & 재시작

```bash
# API만 재빌드
docker compose -f docker-compose.demo.yml build api --no-cache && \
docker compose -f docker-compose.demo.yml up -d api

# 전체 재빌드
docker compose -f docker-compose.demo.yml build --no-cache && \
docker compose -f docker-compose.demo.yml up -d
```

---

## 문제 발생 시

### API 로그 확인
```bash
docker logs inca_demo_api --tail 50
```

### DB 연결 확인
```bash
docker exec inca_demo_db pg_isready -U postgres
```

### 컨테이너 재시작
```bash
docker compose -f docker-compose.demo.yml restart api
```
