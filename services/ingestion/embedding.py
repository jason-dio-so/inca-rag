"""
Embedding Provider

임베딩 생성 모듈
기본: 더미 임베딩 (랜덤 벡터)
인터페이스를 통해 OpenAI, HuggingFace 등으로 교체 가능
"""

from __future__ import annotations

import os
import random
from abc import ABC, abstractmethod
from typing import Any


def get_embed_dim() -> int:
    """환경변수에서 임베딩 차원 가져오기"""
    return int(os.environ.get("EMBED_DIM", "1536"))


class EmbeddingProvider(ABC):
    """임베딩 제공자 인터페이스"""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """임베딩 벡터 차원"""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """단일 텍스트 임베딩"""
        pass

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """배치 텍스트 임베딩"""
        pass


class DummyEmbeddingProvider(EmbeddingProvider):
    """
    더미 임베딩 제공자
    테스트/개발용 랜덤 벡터 생성
    """

    def __init__(self, dimension: int | None = None, seed: int | None = None):
        """
        Args:
            dimension: 벡터 차원 (기본: EMBED_DIM 환경변수 또는 1536)
            seed: 랜덤 시드 (재현성)
        """
        self._dimension = dimension or get_embed_dim()
        self._seed = seed
        if seed is not None:
            random.seed(seed)

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """랜덤 벡터 생성 (텍스트 해시 기반 시드로 일관성 유지)"""
        # 같은 텍스트면 같은 벡터
        text_seed = hash(text) % (2**32)
        rng = random.Random(text_seed)
        return [rng.gauss(0, 1) for _ in range(self._dimension)]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """배치 임베딩"""
        return [self.embed_text(text) for text in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI 임베딩 제공자
    text-embedding-3-small 또는 text-embedding-ada-002 사용
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        dimension: int | None = None,
    ):
        """
        Args:
            model: OpenAI 모델명
            api_key: API 키 (기본: OPENAI_API_KEY 환경변수)
            dimension: 출력 차원 (text-embedding-3-* 전용)
        """
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._dimension = dimension or get_embed_dim()
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai 패키지가 필요합니다: pip install openai")
        return self._client

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "input": texts,
        }

        # text-embedding-3-* 모델은 dimensions 파라미터 지원
        if "text-embedding-3" in self._model:
            kwargs["dimensions"] = self._dimension

        response = client.embeddings.create(**kwargs)
        return [item.embedding for item in response.data]


# 기본 제공자
_default_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """기본 임베딩 제공자 반환"""
    global _default_provider
    if _default_provider is None:
        # 기본: 더미 제공자
        _default_provider = DummyEmbeddingProvider()
    return _default_provider


def set_embedding_provider(provider: EmbeddingProvider) -> None:
    """기본 임베딩 제공자 설정"""
    global _default_provider
    _default_provider = provider


def embed_text(text: str) -> list[float]:
    """편의 함수: 단일 텍스트 임베딩"""
    return get_embedding_provider().embed_text(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """편의 함수: 배치 텍스트 임베딩"""
    return get_embedding_provider().embed_texts(texts)


def create_provider(
    provider_type: str = "dummy",
    **kwargs: Any,
) -> EmbeddingProvider:
    """
    임베딩 제공자 팩토리

    Args:
        provider_type: "dummy" | "openai"
        **kwargs: 제공자별 추가 인자

    Returns:
        EmbeddingProvider
    """
    if provider_type == "dummy":
        return DummyEmbeddingProvider(**kwargs)
    elif provider_type == "openai":
        return OpenAIEmbeddingProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
