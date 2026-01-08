# Demo 환경 시작 가이드

## 날짜
2025-12-21

## 개요
보험 약관 비교 RAG 시스템 Demo 환경 시작 절차

---

## 사전 요구사항

- Docker Desktop 설치 및 실행 중
- 프로젝트 루트 디렉토리 (`inca-rag/`)

---

## 시작 절차

### 1. Docker 컨테이너 시작

```bash
docker compose -f docker-compose.demo.yml up -d
```

### 2. 서비스 상태 확인

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**정상 상태 출력:**
```
NAMES             STATUS                    PORTS
inca_demo_api     Up (healthy)              0.0.0.0:8000->8000/tcp
inca_demo_nginx   Up                        0.0.0.0:80->80/tcp
inca_demo_web     Up                        0.0.0.0:3000->3000/tcp
inca_demo_db      Up (healthy)              0.0.0.0:5432->5432/tcp
```

### 3. API 헬스체크

```bash
curl -s http://localhost:8000/health
```

**정상 응답:**
```json
{"status":"healthy"}
```

### 4. 브라우저에서 접속

```bash
open http://localhost
```

또는 브라우저에서 직접 접속:
- **Web UI**: http://localhost (Nginx 프록시)
- **API 직접**: http://localhost:8000
- **Web 직접**: http://localhost:3000

---

## 서비스 구성

| 컨테이너 | 역할 | 포트 |
|----------|------|------|
| inca_demo_db | PostgreSQL + pgvector | 5432 |
| inca_demo_api | FastAPI Backend | 8000 |
| inca_demo_web | Next.js Frontend | 3000 |
| inca_demo_nginx | Reverse Proxy | 80 |

---

## 종료 절차

```bash
docker compose -f docker-compose.demo.yml down
```

데이터 볼륨 포함 완전 삭제:
```bash
docker compose -f docker-compose.demo.yml down -v
```

---

## 트러블슈팅

### 컨테이너가 시작되지 않는 경우

```bash
# 로그 확인
docker compose -f docker-compose.demo.yml logs

# 특정 서비스 로그
docker compose -f docker-compose.demo.yml logs api
```

### 포트 충돌

```bash
# 80, 3000, 5432, 8000 포트 사용 중인 프로세스 확인
lsof -i :80
lsof -i :8000
```

### 컨테이너 재빌드

```bash
docker compose -f docker-compose.demo.yml build --no-cache
docker compose -f docker-compose.demo.yml up -d
```

---

## 검증 완료

- 2025-12-21: 정상 가동 확인
