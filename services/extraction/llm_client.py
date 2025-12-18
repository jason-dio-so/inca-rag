"""
Step H-2: LLM 호출 클라이언트 (추상화)

실제 LLM 호출은 외부 의존이므로 인터페이스로 분리
기본은 Disabled 상태로 테스트가 깨지지 않음

Step H-2.1: OpenAI 클라이언트 + PII 마스킹 + 메트릭
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .llm_schemas import LLMExtractResult
from .llm_prompts import SYSTEM_PROMPT
from .pii_masker import mask_pii


logger = logging.getLogger(__name__)


# 환경변수
def is_llm_enabled() -> bool:
    """LLM 활성화 여부"""
    return os.environ.get("LLM_ENABLED", "0") == "1"


def get_llm_max_calls_per_request() -> int:
    """요청당 최대 LLM 호출 횟수"""
    return int(os.environ.get("LLM_MAX_CALLS_PER_REQUEST", "8"))


def get_llm_provider() -> str:
    """LLM 제공자"""
    return os.environ.get("LLM_PROVIDER", "openai")


def get_llm_model() -> str:
    """LLM 모델"""
    return os.environ.get("LLM_MODEL", "gpt-4o-mini")


def get_llm_timeout_seconds() -> float:
    """LLM 호출 타임아웃 (초)"""
    return float(os.environ.get("LLM_TIMEOUT_SECONDS", "8"))


def get_llm_max_chars_per_call() -> int:
    """LLM 호출당 최대 문자 수"""
    return int(os.environ.get("LLM_MAX_CHARS_PER_CALL", "4000"))


def get_llm_max_retries() -> int:
    """LLM 호출 최대 재시도 횟수"""
    return int(os.environ.get("LLM_MAX_RETRIES", "2"))


@dataclass
class LLMCallMetrics:
    """LLM 호출 메트릭"""
    call_id: str
    coverage_code: str
    insurer_code: str
    start_time: float = 0.0
    end_time: float = 0.0
    latency_ms: float = 0.0
    success: bool = False
    error: str | None = None
    pii_masked_count: int = 0
    input_chars: int = 0
    retry_count: int = 0

    def finish(self, success: bool, error: str | None = None) -> None:
        """호출 완료 처리"""
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error


@runtime_checkable
class LLMClient(Protocol):
    """LLM 클라이언트 프로토콜"""

    async def extract(
        self,
        system_prompt: str,
        user_prompt: str,
        context: dict,
    ) -> LLMExtractResult | None:
        """
        LLM에 추출 요청

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            context: 컨텍스트 정보 (coverage_code, insurer_code 등)

        Returns:
            LLMExtractResult | None (실패 시 None)
        """
        ...


class DisabledLLMClient:
    """LLM 비활성화 클라이언트 (기본)"""

    async def extract(
        self,
        system_prompt: str,
        user_prompt: str,
        context: dict,
    ) -> LLMExtractResult | None:
        """LLM이 비활성화되어 있으면 RuntimeError"""
        raise RuntimeError("LLM is disabled. Set LLM_ENABLED=1 to enable.")


class FakeLLMClient:
    """
    테스트용 Fake LLM 클라이언트

    고정된 응답을 반환하여 테스트 가능
    """

    def __init__(self, responses: dict[str, dict] | None = None):
        """
        Args:
            responses: coverage_code별 고정 응답 (dict)
                       key: coverage_code
                       value: LLMExtractResult에 해당하는 dict
        """
        self.responses = responses or {}
        self.call_count = 0
        self.call_history: list[dict] = []

    async def extract(
        self,
        system_prompt: str,
        user_prompt: str,
        context: dict,
    ) -> LLMExtractResult | None:
        """고정 응답 반환"""
        self.call_count += 1
        self.call_history.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "context": context,
        })

        coverage_code = context.get("coverage_code", "")

        # coverage_code별 고정 응답이 있으면 반환
        if coverage_code in self.responses:
            response_dict = self.responses[coverage_code]
            try:
                return LLMExtractResult.model_validate(response_dict)
            except Exception:
                return None

        # 기본 응답 (unknown)
        return LLMExtractResult(
            coverage_code=coverage_code,
            insurer_code=context.get("insurer_code", "UNKNOWN"),
            doc_type="가입설계서",
            document_id=context.get("document_id", 0),
            page_start=context.get("page_start"),
            chunk_id=context.get("chunk_id", 0),
            amount={
                "label": "unknown",
                "amount_value": None,
                "amount_text": None,
                "unit": None,
                "confidence": "low",
                "span": None,
            },
            condition={
                "snippet": None,
                "matched_terms": [],
                "confidence": "low",
                "span": None,
            },
            notes=None,
        )


class OpenAILLMClient:
    """
    OpenAI API 클라이언트

    - timeout, retry, exponential backoff 지원
    - PII 마스킹 적용
    - 메트릭 수집
    """

    def __init__(
        self,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        max_chars: int | None = None,
    ):
        self.model = model or get_llm_model()
        self.timeout = timeout or get_llm_timeout_seconds()
        self.max_retries = max_retries or get_llm_max_retries()
        self.max_chars = max_chars or get_llm_max_chars_per_call()

        # 메트릭
        self.metrics_history: list[LLMCallMetrics] = []
        self._call_counter = 0

        # OpenAI 클라이언트 (lazy init)
        self._client = None

    def _get_client(self):
        """OpenAI 클라이언트 lazy 초기화"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI()
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                )
        return self._client

    async def extract(
        self,
        system_prompt: str,
        user_prompt: str,
        context: dict,
    ) -> LLMExtractResult | None:
        """
        OpenAI API를 통한 추출

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            context: 컨텍스트 정보

        Returns:
            LLMExtractResult | None
        """
        # 메트릭 초기화
        self._call_counter += 1
        metrics = LLMCallMetrics(
            call_id=f"llm_{self._call_counter}",
            coverage_code=context.get("coverage_code", ""),
            insurer_code=context.get("insurer_code", ""),
            start_time=time.time(),
        )

        # PII 마스킹
        mask_result = mask_pii(user_prompt)
        masked_prompt = mask_result.masked_text
        metrics.pii_masked_count = mask_result.mask_count
        metrics.input_chars = len(masked_prompt)

        if mask_result.mask_count > 0:
            logger.info(
                f"PII masked: {mask_result.mask_count} items "
                f"({mask_result.mask_details})"
            )

        # 문자 수 제한 체크
        if len(masked_prompt) > self.max_chars:
            logger.warning(
                f"Input too long ({len(masked_prompt)} > {self.max_chars}), truncating"
            )
            masked_prompt = masked_prompt[:self.max_chars]

        # 재시도 루프
        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            metrics.retry_count = attempt

            try:
                result = await self._call_openai(
                    system_prompt,
                    masked_prompt,
                    context,
                )

                metrics.finish(success=True)
                self.metrics_history.append(metrics)

                logger.info(
                    f"LLM call success: {metrics.coverage_code} "
                    f"latency={metrics.latency_ms:.0f}ms"
                )
                return result

            except asyncio.TimeoutError:
                last_error = "timeout"
                logger.warning(
                    f"LLM timeout (attempt {attempt + 1}/{self.max_retries + 1})"
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"LLM error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )

            # Exponential backoff
            if attempt < self.max_retries:
                backoff = 2 ** attempt  # 1, 2, 4, ...
                await asyncio.sleep(backoff)

        # 모든 재시도 실패
        metrics.finish(success=False, error=last_error)
        self.metrics_history.append(metrics)

        logger.error(
            f"LLM call failed after {self.max_retries + 1} attempts: {last_error}"
        )
        return None

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        context: dict,
    ) -> LLMExtractResult | None:
        """실제 OpenAI API 호출"""
        client = self._get_client()

        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            ),
            timeout=self.timeout,
        )

        # 응답 파싱
        content = response.choices[0].message.content
        if not content:
            return None

        try:
            data = json.loads(content)
            # context에서 필수 필드 보충
            data.setdefault("coverage_code", context.get("coverage_code", ""))
            data.setdefault("insurer_code", context.get("insurer_code", ""))
            data.setdefault("doc_type", "가입설계서")
            data.setdefault("document_id", context.get("document_id", 0))
            data.setdefault("page_start", context.get("page_start"))
            data.setdefault("chunk_id", context.get("chunk_id", 0))

            return LLMExtractResult.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None

    def get_metrics_summary(self) -> dict:
        """메트릭 요약 반환"""
        if not self.metrics_history:
            return {
                "total_calls": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_latency_ms": 0,
                "avg_latency_ms": 0,
                "total_pii_masked": 0,
            }

        success_count = sum(1 for m in self.metrics_history if m.success)
        failure_count = len(self.metrics_history) - success_count
        total_latency = sum(m.latency_ms for m in self.metrics_history)
        total_pii = sum(m.pii_masked_count for m in self.metrics_history)

        return {
            "total_calls": len(self.metrics_history),
            "success_count": success_count,
            "failure_count": failure_count,
            "total_latency_ms": total_latency,
            "avg_latency_ms": total_latency / len(self.metrics_history),
            "total_pii_masked": total_pii,
        }


def get_llm_client() -> LLMClient:
    """
    환경 설정에 따라 적절한 LLM 클라이언트 반환

    LLM_ENABLED=0 이면 DisabledLLMClient
    LLM_ENABLED=1 이면 OpenAILLMClient (provider에 따라 확장 가능)
    """
    if not is_llm_enabled():
        return DisabledLLMClient()

    provider = get_llm_provider()
    if provider == "openai":
        return OpenAILLMClient()
    else:
        logger.warning(f"Unknown LLM provider: {provider}, using DisabledLLMClient")
        return DisabledLLMClient()


def validate_span_in_text(span_text: str | None, chunk_text: str) -> bool:
    """
    span.text가 chunk_text에 실제로 포함되어 있는지 검증 (환각 방지)

    Args:
        span_text: LLM이 반환한 span 텍스트
        chunk_text: 원본 chunk 텍스트

    Returns:
        포함 여부
    """
    if not span_text:
        return False

    # 공백 정규화 후 비교
    normalized_span = " ".join(span_text.split())
    normalized_chunk = " ".join(chunk_text.split())

    return normalized_span in normalized_chunk
