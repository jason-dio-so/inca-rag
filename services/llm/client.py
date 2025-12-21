"""
STEP 5: LLM Assist Client

LLM provider wrapper with timeout, retry, soft-fail

핵심 원칙:
- LLM 실패/타임아웃 시에도 시스템 정상 동작
- Soft-fail: assist 결과만 실패 상태로 반환
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# 환경 설정
# =============================================================================

def is_assist_llm_enabled() -> bool:
    """Assist LLM 활성화 여부"""
    return os.environ.get("ASSIST_LLM_ENABLED", "0") == "1"


def get_assist_llm_provider() -> str:
    """Assist LLM 제공자"""
    return os.environ.get("ASSIST_LLM_PROVIDER", "openai")


def get_assist_llm_model() -> str:
    """Assist LLM 모델"""
    return os.environ.get("ASSIST_LLM_MODEL", "gpt-4o-mini")


def get_assist_llm_timeout() -> float:
    """Assist LLM 타임아웃 (초)"""
    return float(os.environ.get("ASSIST_LLM_TIMEOUT", "10"))


def get_assist_llm_max_retries() -> int:
    """Assist LLM 최대 재시도 횟수"""
    return int(os.environ.get("ASSIST_LLM_MAX_RETRIES", "1"))


# =============================================================================
# Metrics
# =============================================================================

@dataclass
class AssistLLMMetrics:
    """Assist LLM 호출 메트릭"""
    call_id: str
    endpoint: str  # "query_assist" or "evidence_summary"
    start_time: float = 0.0
    end_time: float = 0.0
    latency_ms: float = 0.0
    success: bool = False
    error: str | None = None
    retry_count: int = 0

    def finish(self, success: bool, error: str | None = None) -> None:
        """호출 완료 처리"""
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error


# =============================================================================
# LLM Client
# =============================================================================

@dataclass
class AssistLLMResponse:
    """LLM 응답"""
    success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


class AssistLLMClient:
    """
    Assist LLM 클라이언트

    특징:
    - Soft-fail: 실패해도 시스템 정상 동작
    - Timeout, Retry 지원
    - JSON 응답 파싱
    """

    def __init__(
        self,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        self.model = model or get_assist_llm_model()
        self.timeout = timeout or get_assist_llm_timeout()
        self.max_retries = max_retries or get_assist_llm_max_retries()
        self.metrics_history: list[AssistLLMMetrics] = []
        self._call_counter = 0
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

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        endpoint: str,
    ) -> AssistLLMResponse:
        """
        LLM 호출

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            endpoint: 엔드포인트 이름 ("query_assist" or "evidence_summary")

        Returns:
            AssistLLMResponse
        """
        # LLM 비활성화 상태 확인
        if not is_assist_llm_enabled():
            logger.info(f"Assist LLM disabled, using rule-based fallback for {endpoint}")
            return AssistLLMResponse(
                success=False,
                error_code="DISABLED",
                error_message="Assist LLM is disabled (ASSIST_LLM_ENABLED=0)",
            )

        # 메트릭 초기화
        self._call_counter += 1
        metrics = AssistLLMMetrics(
            call_id=f"assist_{self._call_counter}",
            endpoint=endpoint,
            start_time=time.time(),
        )

        last_error: str | None = None

        # 재시도 루프
        for attempt in range(self.max_retries + 1):
            metrics.retry_count = attempt

            try:
                result = await self._call_openai(system_prompt, user_prompt)

                metrics.finish(success=True)
                self.metrics_history.append(metrics)

                logger.info(
                    f"Assist LLM call success: {endpoint} "
                    f"latency={metrics.latency_ms:.0f}ms"
                )
                return AssistLLMResponse(success=True, data=result)

            except asyncio.TimeoutError:
                last_error = "timeout"
                logger.warning(
                    f"Assist LLM timeout (attempt {attempt + 1}/{self.max_retries + 1})"
                )
            except json.JSONDecodeError as e:
                last_error = f"json_parse_error: {str(e)}"
                logger.warning(f"Assist LLM JSON parse error: {e}")
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Assist LLM error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )

            # Exponential backoff
            if attempt < self.max_retries:
                backoff = 2 ** attempt
                await asyncio.sleep(backoff)

        # 모든 재시도 실패 - Soft-fail
        metrics.finish(success=False, error=last_error)
        self.metrics_history.append(metrics)

        logger.error(
            f"Assist LLM call failed after {self.max_retries + 1} attempts: {last_error}"
        )

        return AssistLLMResponse(
            success=False,
            error_code="LLM_FAILED",
            error_message=f"LLM call failed: {last_error}",
        )

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
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

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        return json.loads(content)


# 싱글톤 인스턴스
_assist_client: AssistLLMClient | None = None


def get_assist_llm_client() -> AssistLLMClient:
    """Assist LLM 클라이언트 인스턴스 반환"""
    global _assist_client
    if _assist_client is None:
        _assist_client = AssistLLMClient()
    return _assist_client
