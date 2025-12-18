"""
Step H-2.1: PII 마스킹 단위 테스트
"""

import pytest

from services.extraction.pii_masker import (
    mask_pii,
    mask_rrn,
    mask_phone,
    mask_email,
    mask_account,
    MaskResult,
)


class TestMaskRRN:
    """주민등록번호 마스킹 테스트"""

    def test_rrn_with_dash(self):
        """하이픈 있는 주민번호"""
        text = "주민번호: 850101-1234567"
        result, count = mask_rrn(text)
        assert count == 1
        assert "[주민번호]" in result
        assert "1234567" not in result

    def test_rrn_without_dash(self):
        """하이픈 없는 주민번호"""
        text = "주민번호: 8501011234567"
        result, count = mask_rrn(text)
        assert count == 1
        assert "[주민번호]" in result

    def test_rrn_with_space(self):
        """공백 있는 주민번호"""
        text = "주민번호: 850101 1234567"
        result, count = mask_rrn(text)
        assert count == 1
        assert "[주민번호]" in result

    def test_rrn_female(self):
        """여성 주민번호 (2로 시작)"""
        text = "주민번호: 900515-2345678"
        result, count = mask_rrn(text)
        assert count == 1
        assert "[주민번호]" in result

    def test_not_rrn_invalid_gender_code(self):
        """성별 코드가 5~9면 주민번호 아님"""
        text = "번호: 850101-5234567"  # 5는 성별코드 아님
        result, count = mask_rrn(text)
        assert count == 0
        assert "[주민번호]" not in result

    def test_rrn_2000s(self):
        """2000년대생 주민번호 (3, 4로 시작)"""
        text = "주민번호: 050320-3123456"
        result, count = mask_rrn(text)
        assert count == 1
        assert "[주민번호]" in result


class TestMaskPhone:
    """전화번호 마스킹 테스트"""

    def test_mobile_with_dash(self):
        """휴대폰번호 (하이픈)"""
        text = "연락처: 010-1234-5678"
        result, count = mask_phone(text)
        assert count == 1
        assert "[전화번호]" in result

    def test_mobile_without_dash(self):
        """휴대폰번호 (하이픈 없음)"""
        text = "연락처: 01012345678"
        result, count = mask_phone(text)
        assert count == 1
        assert "[전화번호]" in result

    def test_landline_seoul(self):
        """서울 지역번호"""
        text = "전화: 02-123-4567"
        result, count = mask_phone(text)
        assert count == 1
        assert "[전화번호]" in result

    def test_landline_other(self):
        """기타 지역번호"""
        text = "전화: 031-1234-5678"
        result, count = mask_phone(text)
        assert count == 1
        assert "[전화번호]" in result

    def test_multiple_phones(self):
        """복수 전화번호"""
        text = "연락처: 010-1111-2222, 010-3333-4444"
        result, count = mask_phone(text)
        assert count == 2
        assert result.count("[전화번호]") == 2


class TestMaskEmail:
    """이메일 마스킹 테스트"""

    def test_basic_email(self):
        """기본 이메일"""
        text = "이메일: test@example.com"
        result, count = mask_email(text)
        assert count == 1
        assert "[이메일]" in result
        assert "test@example.com" not in result

    def test_email_with_plus(self):
        """+ 기호 포함 이메일"""
        text = "이메일: user+tag@example.com"
        result, count = mask_email(text)
        assert count == 1
        assert "[이메일]" in result

    def test_email_subdomain(self):
        """서브도메인 이메일"""
        text = "연락처: admin@mail.company.co.kr"
        result, count = mask_email(text)
        assert count == 1
        assert "[이메일]" in result


class TestMaskAccount:
    """계좌번호 마스킹 테스트"""

    def test_account_10_digits(self):
        """10자리 계좌번호"""
        text = "계좌: 110-123-456789"
        result, count = mask_account(text)
        assert count == 1
        assert "[계좌번호]" in result

    def test_account_12_digits(self):
        """12자리 계좌번호"""
        text = "계좌번호: 123-456-789012"
        result, count = mask_account(text)
        assert count == 1
        assert "[계좌번호]" in result

    def test_not_account_short(self):
        """9자리 이하는 계좌번호 아님"""
        text = "번호: 123-456-789"  # 9자리
        result, count = mask_account(text)
        assert count == 0
        assert "[계좌번호]" not in result

    def test_amount_not_masked(self):
        """금액은 계좌번호로 마스킹되지 않아야 함"""
        text = "암진단비 1,000만원"
        result, count = mask_account(text)
        assert count == 0
        assert "1,000만원" in result


class TestMaskPII:
    """통합 PII 마스킹 테스트"""

    def test_empty_text(self):
        """빈 텍스트"""
        result = mask_pii("")
        assert result.masked_text == ""
        assert result.mask_count == 0

    def test_no_pii(self):
        """PII 없는 텍스트"""
        text = "암진단비 1,000만원 지급합니다."
        result = mask_pii(text)
        assert result.masked_text == text
        assert result.mask_count == 0

    def test_mixed_pii(self):
        """여러 종류 PII 혼합"""
        text = "이름: 홍길동, 주민번호: 850101-1234567, 전화: 010-1234-5678, 이메일: hong@test.com"
        result = mask_pii(text)

        assert "[주민번호]" in result.masked_text
        assert "[전화번호]" in result.masked_text
        assert "[이메일]" in result.masked_text
        assert result.mask_count >= 3
        assert "rrn" in result.mask_details
        assert "phone" in result.mask_details
        assert "email" in result.mask_details

    def test_insurance_text_preserved(self):
        """보험 관련 텍스트는 보존"""
        text = "암진단비 1,000만원, 수술비 500만원, 입원일당 5만원"
        result = mask_pii(text)

        # 금액은 마스킹되지 않아야 함
        assert "1,000만원" in result.masked_text
        assert "500만원" in result.masked_text
        assert "5만원" in result.masked_text
        assert result.mask_count == 0

    def test_mask_result_dataclass(self):
        """MaskResult 구조 확인"""
        result = mask_pii("전화: 010-1234-5678")
        assert isinstance(result, MaskResult)
        assert hasattr(result, "masked_text")
        assert hasattr(result, "mask_count")
        assert hasattr(result, "mask_details")


class TestRealWorldCases:
    """실제 보험 문서 유사 케이스 테스트"""

    def test_enrollment_form_text(self):
        """가입설계서 유사 텍스트"""
        text = """
        피보험자 정보
        성명: 홍길동
        주민등록번호: 850101-1234567
        연락처: 010-9876-5432

        보장내용
        암진단비: 3,000만원
        뇌출혈진단비: 2,000만원
        """
        result = mask_pii(text)

        # PII는 마스킹
        assert "850101-1234567" not in result.masked_text
        assert "010-9876-5432" not in result.masked_text
        assert "[주민번호]" in result.masked_text
        assert "[전화번호]" in result.masked_text

        # 금액은 보존
        assert "3,000만원" in result.masked_text
        assert "2,000만원" in result.masked_text

    def test_policy_text_no_pii(self):
        """약관 텍스트 (PII 없음)"""
        text = """
        제1조(보험금의 지급사유)
        피보험자가 보험기간 중 암으로 진단확정되었을 때
        암진단비 1,000만원을 지급합니다.
        """
        result = mask_pii(text)

        # 변경 없이 그대로
        assert result.mask_count == 0
        assert "1,000만원" in result.masked_text
