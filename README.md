# 보험 약관 비교 RAG 시스템

보험사별 약관/사업방법서/상품요약서/가입설계서를 기반으로 담보 비교 검색을 수행하는 RAG 시스템입니다.

## 데모 실행 (One-Command)

```bash
# 1. 저장소 클론
git clone https://github.com/jason-dio-so/inca-rag.git
cd inca-rag

# 2. 데모 실행 (DB + API + Web + Nginx)
./tools/demo_up.sh
```

> **데모 정책**: 데모 환경에서는 **삼성/메리츠 전체 PDF**를 자동 적재(ingest)합니다. 스모크 테스트는 2개 수행됩니다:
> - **Smoke A (안정성)**: 양쪽 근거 보장 시나리오 (A6200/A5100)
> - **Smoke B (고객 시나리오)**: 경계성종양 암진단비 (A4200_1/A4210)

### 접속 URL

| 서비스 | URL |
|--------|-----|
| **Web UI** | http://localhost |
| **API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |
| **DB (PostgreSQL)** | localhost:5432 |

### 데모 시나리오

#### Smoke A: 안정성 (양쪽 근거 보장)
```bash
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"query":"암입원일당 질병수술비","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A6200","A5100"]}'
```

#### Smoke B: 고객 시나리오 (경계성종양 암진단비)
```bash
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"query":"경계성종양 암진단비","insurers":["SAMSUNG","MERITZ"],"coverage_codes":["A4200_1","A4210"]}'
```

### 컨테이너 관리

```bash
# 로그 확인
docker compose -f docker-compose.demo.yml logs -f

# 종료
docker compose -f docker-compose.demo.yml down

# 볼륨까지 삭제 후 재시작
./tools/demo_up.sh --clean

# 이미지 재빌드
./tools/demo_up.sh --build
```

---

## 기술 스택

| 구성요소 | 기술 |
|----------|------|
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js 16 + TypeScript + Tailwind CSS |
| Database | PostgreSQL 16 + pgvector |
| Vector Search | pgvector HNSW 인덱스 |
| PDF Rendering | PyMuPDF (fitz) |
| Reverse Proxy | Nginx |

## 주요 기능

- **담보 비교 검색** (`/compare`): 2-Phase Retrieval (coverage_code 기반 + 약관 검색)
- **A2 정책**: 약관은 비교 계산에서 제외, 정의 확인용으로만 사용
- **Plan 자동 선택**: 나이/성별에 따른 플랜 자동 선택
- **Evidence PDF Viewer**: 근거 원문 PDF 페이지 보기 + 하이라이트

## 프로젝트 구조

```
inca-rag/
├── api/                    # FastAPI 백엔드
│   ├── main.py
│   ├── compare.py
│   ├── document_viewer.py
│   └── Dockerfile
├── apps/web/               # Next.js 프론트엔드
│   ├── src/
│   └── Dockerfile
├── services/               # 비즈니스 로직
│   ├── ingestion/          # 문서 적재 파이프라인
│   ├── retrieval/          # 검색 서비스
│   └── extraction/         # 금액/조건 추출
├── data/                   # PDF 문서 데이터
├── db/                     # DB 스키마
├── deploy/                 # 배포 설정
│   └── nginx.conf
├── tools/                  # 유틸리티 스크립트
│   └── demo_up.sh
├── docker-compose.demo.yml # 데모 배포용 Compose
└── docker-compose.yml      # 개발용 Compose (DB only)
```

## 라이선스

Private - All Rights Reserved
