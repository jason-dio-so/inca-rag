"""
Step H-2.1: PII 마스킹 유틸리티

LLM 호출 전 개인정보 마스킹
- 주민등록번호
- 전화번호
- 계좌번호
- 이메일
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# 마스킹 패턴 정의
PATTERNS = {
    # 주민등록번호: 6자리-7자리 (하이픈 있거나 없거나)
    "rrn": re.compile(
        r"\b(\d{6})[-\s]?(\d{7})\b"
    ),
    # 전화번호: 010-1234-5678, 02-123-4567, 031-1234-5678 등
    "phone": re.compile(
        r"\b(01[016789]|02|0[3-9]\d)[-.\s]?(\d{3,4})[-.\s]?(\d{4})\b"
    ),
    # 계좌번호: 10~16자리 숫자 (하이픈으로 구분될 수 있음)
    "account": re.compile(
        r"\b(\d{2,6})[-\s]?(\d{2,6})[-\s]?(\d{2,6})[-\s]?(\d{0,6})\b"
    ),
    # 이메일
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    ),
}

# 마스킹 대체 문자열
MASK_TOKENS = {
    "rrn": "[주민번호]",
    "phone": "[전화번호]",
    "account": "[계좌번호]",
    "email": "[이메일]",
}


@dataclass
class MaskResult:
    """마스킹 결과"""
    masked_text: str
    mask_count: int
    mask_details: dict[str, int]  # 타입별 마스킹 횟수


def mask_rrn(text: str) -> tuple[str, int]:
    """주민등록번호 마스킹"""
    count = 0

    def replace(match: re.Match) -> str:
        nonlocal count
        # 뒷자리 첫 번째가 1-4이면 주민번호로 판단 (성별 코드)
        back = match.group(2)
        if back and back[0] in "1234":
            count += 1
            return MASK_TOKENS["rrn"]
        return match.group(0)

    masked = PATTERNS["rrn"].sub(replace, text)
    return masked, count


def mask_phone(text: str) -> tuple[str, int]:
    """전화번호 마스킹"""
    count = len(PATTERNS["phone"].findall(text))
    masked = PATTERNS["phone"].sub(MASK_TOKENS["phone"], text)
    return masked, count


def mask_account(text: str) -> tuple[str, int]:
    """
    계좌번호 마스킹

    계좌번호는 보험금액과 혼동될 수 있으므로 보수적으로 적용:
    - 총 10자리 이상일 때만 마스킹
    - 금액 패턴(만원, 원, 억 등 단위 뒤따름)은 제외
    """
    count = 0

    def replace(match: re.Match) -> str:
        nonlocal count
        full_match = match.group(0)

        # 전체 숫자만 추출
        digits_only = re.sub(r"[-\s]", "", full_match)

        # 10자리 미만이면 계좌번호가 아님
        if len(digits_only) < 10:
            return full_match

        # 16자리 초과면 계좌번호가 아님
        if len(digits_only) > 16:
            return full_match

        count += 1
        return MASK_TOKENS["account"]

    masked = PATTERNS["account"].sub(replace, text)
    return masked, count


def mask_email(text: str) -> tuple[str, int]:
    """이메일 마스킹"""
    count = len(PATTERNS["email"].findall(text))
    masked = PATTERNS["email"].sub(MASK_TOKENS["email"], text)
    return masked, count


def mask_pii(text: str) -> MaskResult:
    """
    모든 PII 마스킹 적용

    Args:
        text: 원본 텍스트

    Returns:
        MaskResult: 마스킹된 텍스트와 통계
    """
    if not text:
        return MaskResult(
            masked_text="",
            mask_count=0,
            mask_details={},
        )

    masked = text
    details: dict[str, int] = {}
    total_count = 0

    # 주민번호 마스킹 (가장 먼저 - 전화번호와 겹칠 수 있음)
    masked, rrn_count = mask_rrn(masked)
    if rrn_count > 0:
        details["rrn"] = rrn_count
        total_count += rrn_count

    # 이메일 마스킹
    masked, email_count = mask_email(masked)
    if email_count > 0:
        details["email"] = email_count
        total_count += email_count

    # 전화번호 마스킹
    masked, phone_count = mask_phone(masked)
    if phone_count > 0:
        details["phone"] = phone_count
        total_count += phone_count

    # 계좌번호 마스킹 (가장 마지막 - 금액과 혼동 가능)
    masked, account_count = mask_account(masked)
    if account_count > 0:
        details["account"] = account_count
        total_count += account_count

    return MaskResult(
        masked_text=masked,
        mask_count=total_count,
        mask_details=details,
    )
