"""
Coverage 정규화 함수

로더/익스트랙터에서 동일한 정규화 규칙 적용을 위한 공유 모듈
"""

from __future__ import annotations

import re


def normalize_coverage_name(raw_name: str) -> str:
    """
    담보명 정규화 (검색용)

    규칙:
    1. 양끝 공백 제거
    2. 연속 공백 → 단일 공백
    3. 괄호(), 대괄호[] 내용 유지하되 공백만 정리
    4. 특수문자 ·, ,, ., -, _ → 공백으로 치환
    5. 영문 lower()
    6. 최종 공백 trim
    """
    if not raw_name:
        return ""

    s = raw_name

    # 1. 양끝 공백 제거
    s = s.strip()

    # 4. 특수문자 → 공백 (괄호 제외)
    # ·(middle dot), ,(comma), .(period), -(dash), _(underscore)
    s = re.sub(r"[·,.\-_]", " ", s)

    # 5. 영문 lower
    s = s.lower()

    # 2. 연속 공백 → 단일 공백
    s = re.sub(r"\s+", " ", s)

    # 3. 괄호 앞뒤 공백 정리
    s = re.sub(r"\s*\(\s*", "(", s)
    s = re.sub(r"\s*\)\s*", ")", s)
    s = re.sub(r"\s*\[\s*", "[", s)
    s = re.sub(r"\s*\]\s*", "]", s)

    # 6. 최종 trim
    s = s.strip()

    return s


def normalize_content_for_matching(content: str) -> str:
    """
    content를 매칭용으로 정규화

    coverage_name과 동일한 규칙 적용
    """
    return normalize_coverage_name(content)
