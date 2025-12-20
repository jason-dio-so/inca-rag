# INCA-RAG 프로젝트 재개 가이드

## 현재 상태 (2025-12-20)

### 최근 완료된 작업
- [x] **STEP 3.9: Anchor Persistence** - 담보 고정 기능 (A/B/C/D 시나리오 검증 완료)
- [x] **STEP 4.0: Diff Summary & Evidence Priority** - 요약 문구 및 P1/P2/P3 우선순위
- [x] **BUGFIX: normalize_query_for_coverage** - 보험사명 제거 버그 수정 + 헌법 준수 리팩터링
- [x] **STEP 4.1: 다중 Subtype 비교** - 경계성 종양/제자리암 정의·조건 중심 비교
  - `config/rules/subtype_slots.yaml` - Subtype 정의 (7개)
  - `services/extraction/subtype_extractor.py` - Subtype 추출 서비스
  - `apps/web/src/components/SubtypeComparePanel.tsx` - 비교 테이블 UI
  - Git 커밋: `00c3fb3`

### 현재 브랜치
```
recovery/step-3.7-delta-beta (origin보다 9 commits 앞섬)
```

### 테스트 상태
```
- tests/test_query_normalization.py: 9 passed
- tests/test_subtype_extractor.py: 8 passed
```

---

## 재접속 시 체크리스트

### 1. Docker Desktop 실행
**반드시 Docker Desktop 앱을 먼저 실행!**

### 2. Docker 상태 확인
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep inca
```

### 3. 컨테이너가 내려가 있으면 시작
```bash
docker compose -f docker-compose.demo.yml up -d
```

### 4. Backend 시작 (Docker 없이 로컬 실행 시)
```bash
cd /Users/cheollee/inca-rag
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Frontend 시작
```bash
cd /Users/cheollee/inca-rag/apps/web
pnpm dev
```

### 6. API 동작 확인
```bash
curl -s http://localhost:8000/health
# 기대: {"status":"healthy"}
```

### 7. 다중 Subtype 비교 테스트 (STEP 4.1)
```bash
curl -s http://localhost:8000/compare -H "Content-Type: application/json" -d '{
  "query": "경계성 종양과 제자리암 차이",
  "insurers": ["SAMSUNG", "MERITZ"]
}' | jq '.subtype_comparison'
```
**기대:** `is_multi_subtype: true`, `subtypes: ["BORDERLINE_TUMOR", "CIS_CARCINOMA"]`

---

## STEP 4.1 테스트 시나리오

### 시나리오 A: 단일 Subtype (Subtype 탭 미표시)
```
질의: "경계성 종양 보장"
기대: Subtype 탭 없음, 일반 비교 결과만 표시
```

### 시나리오 B: 다중 Subtype (Subtype 탭 표시)
```
질의: "경계성 종양과 제자리암 차이"
기대: Subtype 탭 표시, 정의·보장 여부·조건 비교 테이블
```

---

## 핵심 파일 위치

| 파일 | 역할 |
|------|------|
| `config/rules/subtype_slots.yaml` | **Subtype 정의 SSOT** (STEP 4.1) |
| `services/extraction/subtype_extractor.py` | **Subtype 추출 서비스** (STEP 4.1) |
| `apps/web/src/components/SubtypeComparePanel.tsx` | **Subtype 비교 UI** (STEP 4.1) |
| `config/rules/query_normalization.yaml` | 질의 정규화 규칙 |
| `services/retrieval/compare_service.py` | coverage 추천, 2-pass retrieval |
| `apps/web/src/app/page.tsx` | 메인 페이지 (lockedCoverage 상태) |
| `apps/web/src/components/ChatPanel.tsx` | 채팅 UI (담보 잠금 표시) |
| `apps/web/src/components/ResultsPanel.tsx` | 결과 패널 (Subtype 탭 연동) |

---

## 테스트 실행

```bash
# Query Normalization 테스트
python -m pytest tests/test_query_normalization.py -v

# Subtype Extractor 테스트
python -m pytest tests/test_subtype_extractor.py -v

# 전체 테스트
python -m pytest tests/ -v --tb=short
```

---

## DB 접속

```bash
docker exec -it inca_demo_db psql -U postgres -d inca_rag
```

**주요 테이블:**
- `insurer` - 8개 보험사
- `coverage_alias` - 담보명 → coverage_code 매핑
- `chunk` - 문서 청크 + embedding

---

## 다음 작업 후보

### 우선순위 높음
1. **STEP 4.1 UI 테스트** - 다중 Subtype 비교 화면 검증
2. **Main 브랜치 병합** - recovery/step-3.7-delta-beta → main

### 우선순위 중간
3. **Subtype 비교 정밀도 향상** - evidence에서 정의/조건 추출 개선
4. **추가 Subtype 지원** - 현재 7개 → 더 많은 질병 하위 개념

---

## 빠른 재시작

```bash
# 포트 정리 후 전체 재시작
lsof -ti:3000,8000 | xargs kill -9 2>/dev/null

# Backend
cd /Users/cheollee/inca-rag && uvicorn api.main:app --port 8000 --reload &

# Frontend
cd /Users/cheollee/inca-rag/apps/web && pnpm dev &
```

---

## 문제 발생 시

### PostgreSQL 연결 오류
```
connection to server at "127.0.0.1", port 5432 failed
```
→ Docker Desktop 실행 후 `docker compose -f docker-compose.demo.yml up -d`

### API import 오류
```
ModuleNotFoundError: No module named 'api'
```
→ 프로젝트 루트에서 `uvicorn api.main:app` 실행 (api 디렉토리에서 실행 X)

### 포트 사용 중
```bash
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```
