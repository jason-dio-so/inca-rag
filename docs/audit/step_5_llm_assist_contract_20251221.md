# STEP 5: LLM Assist Contract Audit

## 개요

STEP 5는 LLM을 "보조(Assist)" 역할로만 도입하는 단계입니다.
기존 규칙/DB 기반 시스템을 유지하면서, 질의 정규화와 비판단 요약 기능을 추가합니다.

## 날짜

2025-12-21

## 핵심 원칙 (Guardrails)

### 1. LLM 허용 역할
- 질의 정규화 (JSON)
- intent / subtype / keyword 힌트
- evidence 문구의 **비판단 요약**
- UNRESOLVED / fallback 이유 설명

### 2. LLM 금지 역할
- coverage_code 결정 또는 추천
- 지급 가능/불가능 판단
- 금액 비교, "어디가 더 유리"
- 최종 비교 결론 문장 생성
- 근거 없는 일반론/추론

### 3. 비침투 원칙
- `/compare` API는 **LLM 없이도 100% 동일하게 동작**
- LLM 실패/타임아웃 시: compare 결과 정상, assist 결과만 실패 상태
- LLM 결과는 **참고 정보**일 뿐

## 구현 범위

### Backend

#### 새로운 모듈: `services/llm/`
- `__init__.py`: 모듈 진입점
- `schemas.py`: Pydantic 스키마 (Request/Response)
- `guardrails.py`: 금지어 탐지, 출력 검증
- `client.py`: LLM provider wrapper (OpenAI)
- `query_assist.py`: Query Assist 로직
- `evidence_summary.py`: Evidence Summary 로직

#### 새로운 API: `api/assist.py`
- `POST /assist/query`: 질의 정규화/힌트
- `POST /assist/summary`: 비판단 요약

### Frontend

#### 새로운 컴포넌트
- `QueryAssistHint.tsx`: AI 힌트 카드 (Apply/Ignore 버튼)
- `EvidenceSummaryPanel.tsx`: Evidence 요약 패널

#### 수정된 컴포넌트
- `ChatPanel.tsx`: Query Assist 통합 (Sparkles 버튼)
- `EvidencePanel.tsx`: Evidence Summary 통합
- `lib/api.ts`: Assist API 함수 추가
- `lib/types.ts`: Assist 타입 추가

## API 스키마

### Query Assist Request
```json
{
  "query": "경계성 종양과 제자리암 비교",
  "insurers": ["SAMSUNG", "MERITZ"],
  "context": {
    "has_anchor": false,
    "locked_coverage_codes": null
  }
}
```

### Query Assist Response
```json
{
  "normalized_query": "암진단비 (제자리암, 경계성 종양) 비교",
  "detected_intents": ["compare", "coverage_lookup"],
  "detected_subtypes": ["CIS_CARCINOMA", "BORDERLINE_TUMOR"],
  "keywords": ["암진단비", "제자리암", "경계성종양"],
  "confidence": 0.8,
  "notes": "판단/결론 금지. 정규화 힌트만 제공.",
  "assist_status": {"status": "SUCCESS"}
}
```

### Evidence Summary Request
```json
{
  "evidence": [
    {
      "insurer_code": "SAMSUNG",
      "doc_type": "약관",
      "page": 12,
      "excerpt": "제자리암은 약관 정의상..."
    }
  ],
  "task": "summarize_without_judgement"
}
```

### Evidence Summary Response
```json
{
  "summary_bullets": [
    "제자리암은 약관 정의상 특정 조건에서 보장 대상에 포함됨.",
    "경계성 종양은 별도 정의 조항에서 보장 범위가 제한됨."
  ],
  "limitations": [
    "본 요약은 발췌된 근거에만 기반하며 지급 여부를 판단하지 않음."
  ],
  "assist_status": {"status": "SUCCESS"}
}
```

## 금지어 패턴

```python
FORBIDDEN_PATTERNS = [
    # 지급 판단
    r"지급된다", r"지급됩니다", r"지급 가능", r"지급 불가",

    # 유불리 판단
    r"유리하다", r"불리하다", r"더 좋", r"더 낫",

    # 결론/추천
    r"결론적으로", r"따라서", r"추천", r"권장",

    # coverage_code 확정
    r"담보 코드는", r"coverage_code", r"A\d{4}_\d",
]
```

## 테스트 결과

### Query Assist (규칙 기반)
```
Input: "경계성 종양과 제자리암 비교"
Output:
  - normalized_query: "경계성 종양과 제자리암 비교"
  - detected_intents: ["compare", "coverage_lookup"]
  - detected_subtypes: ["CIS_CARCINOMA", "BORDERLINE_TUMOR"]
  - keywords: ["제자리암", "경계성종양"]
  - confidence: 0.5
  - status: SUCCESS
```

### Evidence Summary (규칙 기반)
```
Input: 2개의 약관 발췌
Output:
  - 2개의 요약 bullets
  - 1개의 limitation ("본 요약은 발췌된 근거에만 기반...")
  - status: SUCCESS
```

### Guardrails 테스트
```
Input: "이 담보는 지급됩니다. 삼성이 유리합니다."
Output: violations = ["지급됩니다", "유리합니다"]
Status: BLOCKED
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| ASSIST_LLM_ENABLED | 0 | Assist LLM 활성화 (0=규칙기반) |
| ASSIST_LLM_PROVIDER | openai | LLM 제공자 |
| ASSIST_LLM_MODEL | gpt-4o-mini | LLM 모델 |
| ASSIST_LLM_TIMEOUT | 10 | 타임아웃 (초) |
| ASSIST_LLM_MAX_RETRIES | 1 | 최대 재시도 횟수 |

## UI 동작

### Query Assist 플로우
1. 사용자 질의 입력
2. Sparkles(✨) 버튼 클릭 → `/assist/query` 호출
3. 힌트 카드 표시 (정규화된 질의, 키워드, subtype 등)
4. **Apply 클릭** → 정규화된 질의로 `/compare` 호출
5. **Ignore 클릭** → 원본 질의로 `/compare` 호출
6. 자동 적용 **금지**

### Evidence Summary 플로우
1. `/compare` 결과에서 Evidence 수집
2. Evidence 탭 열람 시 `/assist/summary` 호출
3. 비판단 요약 패널 표시 (⚠️ 라벨 포함)
4. 항상 원문 evidence와 함께 노출

## 변경 파일 목록

### 신규 생성
- `services/llm/__init__.py`
- `services/llm/schemas.py`
- `services/llm/guardrails.py`
- `services/llm/client.py`
- `services/llm/query_assist.py`
- `services/llm/evidence_summary.py`
- `api/assist.py`
- `apps/web/src/components/QueryAssistHint.tsx`
- `apps/web/src/components/EvidenceSummaryPanel.tsx`

### 수정
- `api/main.py`: assist 라우터 등록
- `apps/web/src/lib/types.ts`: Assist 타입 추가
- `apps/web/src/lib/api.ts`: Assist API 함수 추가
- `apps/web/src/components/ChatPanel.tsx`: Query Assist 통합
- `apps/web/src/components/EvidencePanel.tsx`: Evidence Summary 통합

## 결론

STEP 5 LLM Assist 구현이 완료되었습니다.

- ✅ Query Assist API 구현 (`/assist/query`)
- ✅ Evidence Summary API 구현 (`/assist/summary`)
- ✅ Guardrails (금지어 탐지, 출력 검증)
- ✅ Soft-fail (LLM 실패 시 규칙 기반 fallback)
- ✅ Frontend UI (힌트 카드, 요약 패널)
- ✅ 비침투 원칙 준수 (`/compare` 불변)
- ✅ 자동 적용 금지 (Apply 버튼 필수)
