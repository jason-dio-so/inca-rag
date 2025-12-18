#!/bin/bash
# Step H-2.1: LLM 토글 스모크 테스트
#
# 사용법:
#   # LLM OFF (기본, 테스트 통과 확인)
#   ./tools/run_compare_with_llm_toggle.sh
#
#   # LLM ON (실제 API 호출)
#   LLM_ENABLED=1 OPENAI_API_KEY=sk-xxx ./tools/run_compare_with_llm_toggle.sh
#
# 환경변수:
#   LLM_ENABLED=1              LLM 활성화
#   LLM_PROVIDER=openai        LLM 제공자 (기본: openai)
#   LLM_MODEL=gpt-4o-mini      LLM 모델 (기본: gpt-4o-mini)
#   LLM_TIMEOUT_SECONDS=8      LLM 타임아웃 (기본: 8초)
#   LLM_MAX_CALLS_PER_REQUEST=8  요청당 최대 호출 횟수 (기본: 8)
#   LLM_MAX_CHARS_PER_CALL=4000  호출당 최대 문자 수 (기본: 4000)
#   OPENAI_API_KEY=sk-xxx      OpenAI API 키 (LLM_ENABLED=1 시 필수)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================"
echo "LLM Toggle Smoke Test"
echo "========================================"
echo ""

# 환경변수 출력
echo "환경 설정:"
echo "  LLM_ENABLED=${LLM_ENABLED:-0}"
echo "  LLM_PROVIDER=${LLM_PROVIDER:-openai}"
echo "  LLM_MODEL=${LLM_MODEL:-gpt-4o-mini}"
echo "  LLM_TIMEOUT_SECONDS=${LLM_TIMEOUT_SECONDS:-8}"
echo "  LLM_MAX_CALLS_PER_REQUEST=${LLM_MAX_CALLS_PER_REQUEST:-8}"
echo "  LLM_MAX_CHARS_PER_CALL=${LLM_MAX_CHARS_PER_CALL:-4000}"
if [ "${LLM_ENABLED:-0}" == "1" ]; then
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "  OPENAI_API_KEY=<NOT SET - REQUIRED!>"
        echo ""
        echo "ERROR: LLM_ENABLED=1 requires OPENAI_API_KEY"
        exit 1
    else
        echo "  OPENAI_API_KEY=<set>"
    fi
fi
echo ""

# 1. 단위 테스트 실행
echo "----------------------------------------"
echo "1. 단위 테스트 (LLM OFF 환경)"
echo "----------------------------------------"
LLM_ENABLED=0 python -m pytest tests/test_llm_refinement.py -v --tb=short
echo ""

# 2. PII 마스킹 테스트
echo "----------------------------------------"
echo "2. PII 마스킹 테스트"
echo "----------------------------------------"
python -c "
from services.extraction.pii_masker import mask_pii

test_cases = [
    ('주민번호: 850101-1234567', '주민번호'),
    ('전화: 010-1234-5678', '전화번호'),
    ('이메일: test@example.com', '이메일'),
    ('계좌: 110-123-456789', '계좌번호'),
    ('암진단비 1,000만원 지급', '금액 (마스킹 안됨)'),
]

print('PII 마스킹 테스트:')
for text, desc in test_cases:
    result = mask_pii(text)
    print(f'  [{desc}]')
    print(f'    입력: {text}')
    print(f'    출력: {result.masked_text}')
    print(f'    마스킹 개수: {result.mask_count}')
    print()
"
echo ""

# 3. LLM 클라이언트 테스트
echo "----------------------------------------"
echo "3. LLM 클라이언트 테스트"
echo "----------------------------------------"
if [ "${LLM_ENABLED:-0}" == "1" ]; then
    echo "LLM_ENABLED=1: 실제 OpenAI API 호출 테스트"
    python -c "
import asyncio
from services.extraction.llm_client import get_llm_client, OpenAILLMClient
from services.extraction.llm_prompts import SYSTEM_PROMPT, build_user_prompt

async def test_llm():
    client = get_llm_client()
    print(f'클라이언트 타입: {type(client).__name__}')

    if isinstance(client, OpenAILLMClient):
        # 간단한 테스트 호출
        test_prompt = build_user_prompt(
            insurer_code='SAMSUNG',
            coverage_code='CANCER_DIAGNOSIS',
            document_id=1,
            page_start=1,
            chunk_id=1,
            chunk_text='암진단비 가입금액 1,000만원 (최초 1회한)',
        )

        result = await client.extract(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=test_prompt,
            context={
                'coverage_code': 'CANCER_DIAGNOSIS',
                'insurer_code': 'SAMSUNG',
                'document_id': 1,
                'page_start': 1,
                'chunk_id': 1,
            },
        )

        print(f'LLM 응답: {result}')

        # 메트릭 출력
        metrics = client.get_metrics_summary()
        print(f'메트릭: {metrics}')
    else:
        print('LLM이 비활성화되어 있습니다.')

asyncio.run(test_llm())
"
else
    echo "LLM_ENABLED=0: DisabledLLMClient 확인"
    python -c "
from services.extraction.llm_client import get_llm_client, DisabledLLMClient

client = get_llm_client()
print(f'클라이언트 타입: {type(client).__name__}')
assert isinstance(client, DisabledLLMClient), 'LLM_ENABLED=0이면 DisabledLLMClient여야 함'
print('OK: LLM_ENABLED=0 → DisabledLLMClient')
"
fi
echo ""

# 4. compare_service LLM refinement 테스트
echo "----------------------------------------"
echo "4. LLM Refinement 통합 테스트"
echo "----------------------------------------"
python -c "
import asyncio
from services.extraction.llm_client import FakeLLMClient
from services.retrieval.compare_service import (
    refine_coverage_compare_result_with_llm,
    CoverageCompareRow,
    InsurerCompareCell,
    Evidence,
    AmountInfo,
)

async def test_refinement():
    # 테스트 데이터
    cell = InsurerCompareCell(
        insurer_code='SAMSUNG',
        doc_type_counts={'가입설계서': 1},
        best_evidence=[
            Evidence(
                document_id=1,
                doc_type='가입설계서',
                page_start=1,
                preview='암진단비 1,000만원 지급',
                score=0.9,
                amount=AmountInfo(
                    amount_value=None,
                    amount_text=None,
                    unit=None,
                    confidence='medium',
                    method='regex',
                ),
                condition_snippet=None,
            )
        ],
        resolved_amount=None,
    )

    row = CoverageCompareRow(
        coverage_code='CANCER_DIAGNOSIS',
        coverage_name='암진단비',
        insurers=[cell],
    )

    # FakeLLMClient로 테스트
    fake_llm = FakeLLMClient(responses={
        'CANCER_DIAGNOSIS': {
            'coverage_code': 'CANCER_DIAGNOSIS',
            'insurer_code': 'SAMSUNG',
            'doc_type': '가입설계서',
            'document_id': 1,
            'page_start': 1,
            'chunk_id': 1,
            'amount': {
                'label': 'benefit_amount',
                'amount_value': 10000000,
                'amount_text': '1,000만원',
                'unit': '만원',
                'confidence': 'high',
                'span': {'text': '1,000만원', 'start': 5, 'end': 12},
            },
            'condition': {
                'snippet': None,
                'matched_terms': [],
                'confidence': 'low',
                'span': None,
            },
            'notes': None,
        }
    })

    result, stats = await refine_coverage_compare_result_with_llm(
        [row], '암진단비 얼마', fake_llm
    )

    print(f'LLM 호출 횟수: {stats.total_calls}')
    print(f'업그레이드 횟수: {stats.upgrade_count}')
    print(f'상세 메트릭: {stats.to_debug_dict()}')

    # 검증
    assert stats.total_calls == 1, f'Expected 1 call, got {stats.total_calls}'
    assert stats.upgrade_count == 1, f'Expected 1 upgrade, got {stats.upgrade_count}'

    refined_cell = result[0].insurers[0]
    assert refined_cell.resolved_amount is not None, 'resolved_amount should be set'
    assert refined_cell.resolved_amount.amount_value == 10000000, 'amount_value mismatch'

    print('OK: LLM refinement 테스트 통과')

asyncio.run(test_refinement())
"
echo ""

echo "========================================"
echo "스모크 테스트 완료!"
echo "========================================"
