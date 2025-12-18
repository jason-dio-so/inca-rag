"""
Condition Extractor - Rule-based extraction of insurance payment conditions

지급조건 관련 스니펫을 규칙 기반으로 추출
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# 지급조건 관련 키워드
CONDITION_KEYWORDS = [
    "진단",
    "진단확정",
    "확정",
    "최초",
    "1회",
    "면책",
    "감액",
    "대기",
    "유사암",
    "경계성",
    "제자리암",
    "상피내암",
    "90일",
    "180일",
    "가입일",
    "보장개시",
    "지급사유",
    "지급한도",
    "갑상선",
    "기타피부암",
]

# 문장 분리 패턴
SENTENCE_DELIMITERS = r"[.\n;]"

# 최대 스니펫 길이
MAX_SNIPPET_LENGTH = 120


@dataclass
class ConditionExtract:
    """지급조건 추출 결과"""
    snippet: str | None
    matched_terms: list[str] = field(default_factory=list)


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리"""
    # 기본 분리
    sentences = re.split(SENTENCE_DELIMITERS, text)

    # 빈 문장 제거 및 정리
    result = []
    for s in sentences:
        s = s.strip()
        if s and len(s) > 5:  # 너무 짧은 건 제외
            result.append(s)

    return result


def _count_keywords(sentence: str) -> tuple[int, list[str]]:
    """문장에 포함된 키워드 수와 목록 반환"""
    matched = []
    for keyword in CONDITION_KEYWORDS:
        if keyword in sentence:
            matched.append(keyword)
    return len(matched), matched


def _truncate_snippet(text: str, max_length: int = MAX_SNIPPET_LENGTH) -> str:
    """스니펫을 최대 길이로 자름"""
    if len(text) <= max_length:
        return text

    # 단어 경계에서 자르기
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.7:  # 70% 이상 위치에 공백이 있으면
        truncated = truncated[:last_space]

    return truncated + "..."


def extract_condition_snippet(text: str) -> ConditionExtract:
    """
    지급조건 관련 1줄 스니펫을 추출

    규칙:
    - 키워드가 포함된 문장을 우선
    - 가장 키워드 많이 포함한 문장 1개 선택
    - 120자 초과 시 자름

    Args:
        text: 추출 대상 텍스트

    Returns:
        ConditionExtract: snippet과 matched_terms
    """
    if not text or len(text.strip()) == 0:
        return ConditionExtract(snippet=None, matched_terms=[])

    # 문장 분리
    sentences = _split_sentences(text)

    if not sentences:
        return ConditionExtract(snippet=None, matched_terms=[])

    # 각 문장별 키워드 카운트
    scored_sentences: list[tuple[int, list[str], str]] = []
    for sentence in sentences:
        count, matched = _count_keywords(sentence)
        if count > 0:
            scored_sentences.append((count, matched, sentence))

    if not scored_sentences:
        # 키워드 없으면 None 반환
        return ConditionExtract(snippet=None, matched_terms=[])

    # 키워드 가장 많이 포함한 문장 선택
    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    best_count, best_matched, best_sentence = scored_sentences[0]

    # 스니펫 길이 제한
    snippet = _truncate_snippet(best_sentence)

    return ConditionExtract(
        snippet=snippet,
        matched_terms=best_matched,
    )
