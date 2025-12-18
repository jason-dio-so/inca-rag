# Insurance Coverage Comparison Web UI

ChatGPT 유사 인터페이스로 보험 담보 비교를 수행하는 PoC 웹 UI입니다.

## 요구사항

- Node.js 18+
- FastAPI 백엔드가 `http://localhost:8000`에서 실행 중이어야 함

## 실행 방법

```bash
# 프로젝트 디렉토리로 이동
cd apps/web

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

브라우저에서 http://localhost:3000 접속

## 환경 변수

`.env.local` 파일:
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## 화면 구성

### 좌측 패널: ChatPanel
- 사용자 메시지 (오른쪽 정렬, 진한 배경)
- AI 응답 (왼쪽 정렬, 옅은 배경)
- Advanced 옵션:
  - 보험사 선택 (8개사)
  - 나이/성별
  - top_k_per_insurer (슬라이더)
  - coverage_codes (쉼표 구분)
  - policy_keywords (쉼표 구분)

### 우측 패널: ResultsPanel (4개 탭)
- **Compare**: 담보별 비교표 (coverage_compare_result)
- **Diff**: 차이점 요약 (diff_summary)
- **Evidence**: 비교 근거 (compare_axis, 약관 제외)
- **Policy(약관)**: 약관 근거 (policy_axis, 약관만)

### A2 정책
- Compare/Evidence 탭: 약관(doc_type='약관') 절대 미표시
- Policy 탭: 약관만 표시

## 테스트용 입력값

### 예시 1: 경계성 종양 비교
```
보험사: SAMSUNG, MERITZ
질문: 경계성 종양 암진단비
coverage_codes: A4200_1
```

### 예시 2: 암진단비 8개사 비교
```
보험사: SAMSUNG, LOTTE, DB, KB, MERITZ, HANWHA, HYUNDAI, HEUNGKUK
질문: 암진단비
나이: 40
성별: 남(M)
```

## curl 테스트

```bash
# 2사 비교
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{
    "insurers": ["SAMSUNG", "MERITZ"],
    "query": "경계성 종양 암진단비",
    "coverage_codes": ["A4200_1"]
  }'

# 8사 비교 (나이/성별 포함)
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{
    "insurers": ["SAMSUNG", "LOTTE", "DB", "KB", "MERITZ", "HANWHA", "HYUNDAI", "HEUNGKUK"],
    "query": "암진단비",
    "age": 40,
    "gender": "M"
  }'
```

## 파일 구조

```
apps/web/
├── src/
│   ├── app/
│   │   └── page.tsx          # 메인 레이아웃 + 상태
│   ├── components/
│   │   ├── ChatPanel.tsx     # 채팅 패널
│   │   ├── ResultsPanel.tsx  # 결과 패널 (4탭)
│   │   ├── CompareTable.tsx  # 비교표
│   │   ├── DiffSummary.tsx   # 차이점 요약
│   │   ├── EvidencePanel.tsx # 근거 패널
│   │   └── ui/               # shadcn/ui 컴포넌트
│   └── lib/
│       ├── api.ts            # API 클라이언트
│       ├── types.ts          # TypeScript 타입
│       └── utils.ts          # 유틸리티
├── .env.local                # 환경 변수
└── README.md                 # 이 파일
```
