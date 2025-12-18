"""
LLM Usage Trace - Track extraction method and LLM usage

U-4.8 prerequisite: Add tracing across the extraction pipeline
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .llm_client import is_llm_enabled, get_llm_model, is_cost_guard_enabled


LLMReason = Literal["flag_off", "ambiguity_high", "parse_fail", "cost_guard", "not_needed"]
ExtractionMethod = Literal["rule", "llm", "hybrid"]


@dataclass
class LLMTrace:
    """LLM 사용 추적 정보"""
    method: ExtractionMethod
    llm_used: bool
    llm_reason: LLMReason | None = None
    model: str | None = None

    @classmethod
    def rule_only(cls, reason: LLMReason = "flag_off") -> "LLMTrace":
        """Rule-based extraction only (LLM not used)"""
        return cls(
            method="rule",
            llm_used=False,
            llm_reason=reason,
            model=None,
        )

    @classmethod
    def llm_used_trace(cls, model: str | None = None) -> "LLMTrace":
        """LLM was used for extraction"""
        return cls(
            method="llm",
            llm_used=True,
            llm_reason=None,
            model=model or get_llm_model(),
        )

    @classmethod
    def hybrid_trace(cls, model: str | None = None) -> "LLMTrace":
        """Hybrid extraction (rule + LLM)"""
        return cls(
            method="hybrid",
            llm_used=True,
            llm_reason=None,
            model=model or get_llm_model(),
        )

    @classmethod
    def from_llm_flag(cls) -> "LLMTrace":
        """Create trace based on current LLM flag and cost guard status"""
        if not is_llm_enabled():
            return cls.rule_only(reason="flag_off")
        if is_cost_guard_enabled():
            return cls.rule_only(reason="cost_guard")
        return cls.llm_used_trace()

    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        result = {
            "method": self.method,
            "llm_used": self.llm_used,
        }
        if self.llm_reason:
            result["llm_reason"] = self.llm_reason
        if self.model:
            result["model"] = self.model
        return result
