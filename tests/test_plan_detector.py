"""
Step I-1: Plan Detector 테스트

plan_detector 모듈의 성별/나이 감지 및 plan 매칭 테스트 (20+ tests)
"""

import pytest
from unittest.mock import MagicMock, patch

from services.ingestion.plan_detector import (
    detect_gender,
    detect_age_range,
    detect_from_path,
    detect_from_meta,
    detect_plan_info,
    find_matching_plan_id,
    detect_plan_id,
    DetectedPlanInfo,
    PlanDetectorResult,
    MALE_PATTERNS,
    FEMALE_PATTERNS,
)


# =============================================================================
# detect_gender Tests
# =============================================================================

class TestDetectGender:
    """detect_gender 함수 테스트"""

    def test_male_korean_basic(self):
        """'남성' 패턴 감지"""
        assert detect_gender("남성플랜") == "M"
        assert detect_gender("남자형") == "M"

    def test_male_korean_isolated(self):
        """단독 '남' 감지"""
        assert detect_gender("(남)") == "M"
        assert detect_gender("_남_") == "M"
        assert detect_gender("-남-") == "M"

    def test_male_korean_type(self):
        """'남형', 'M형' 패턴"""
        assert detect_gender("남형플랜") == "M"
        assert detect_gender("M형") == "M"
        assert detect_gender("남성형") == "M"

    def test_male_english(self):
        """영문 male 패턴"""
        assert detect_gender("male plan") == "M"
        assert detect_gender("MALE") == "M"
        assert detect_gender("(male)") == "M"

    def test_female_korean_basic(self):
        """'여성' 패턴 감지"""
        assert detect_gender("여성플랜") == "F"
        assert detect_gender("여자형") == "F"

    def test_female_korean_isolated(self):
        """단독 '여' 감지"""
        assert detect_gender("(여)") == "F"
        assert detect_gender("_여_") == "F"
        assert detect_gender("-여-") == "F"

    def test_female_korean_type(self):
        """'여형', 'F형' 패턴"""
        assert detect_gender("여형플랜") == "F"
        assert detect_gender("F형") == "F"
        assert detect_gender("여성형") == "F"

    def test_female_english(self):
        """영문 female 패턴"""
        assert detect_gender("female plan") == "F"
        assert detect_gender("FEMALE") == "F"
        assert detect_gender("(female)") == "F"

    def test_no_gender(self):
        """성별 정보 없음"""
        assert detect_gender("일반플랜") is None
        assert detect_gender("종합보험") is None
        assert detect_gender("") is None

    def test_none_input(self):
        """None 입력"""
        assert detect_gender(None) is None

    def test_male_priority_over_female(self):
        """남성이 먼저 매칭"""
        # 남성 패턴이 먼저 체크되므로 남성 반환
        assert detect_gender("남성_여성") == "M"


# =============================================================================
# detect_age_range Tests
# =============================================================================

class TestDetectAgeRange:
    """detect_age_range 함수 테스트"""

    def test_age_max_pattern(self):
        """'XX세 이하' 패턴"""
        assert detect_age_range("40세이하") == (None, 40)
        assert detect_age_range("40세 이하") == (None, 40)

    def test_age_min_pattern(self):
        """'XX세 이상' 패턴"""
        assert detect_age_range("41세이상") == (41, None)
        assert detect_age_range("41세 이상") == (41, None)

    def test_age_range_pattern(self):
        """'XX-YY세' 범위 패턴"""
        assert detect_age_range("20-40세") == (20, 40)
        assert detect_age_range("20~40세") == (20, 40)
        assert detect_age_range("30-39세") == (30, 39)

    def test_exact_age_pattern(self):
        """'만XX세' 패턴"""
        assert detect_age_range("만40세") == (40, 40)
        assert detect_age_range("만 40세") == (40, 40)

    def test_decade_pattern(self):
        """'XX대' 패턴"""
        assert detect_age_range("30대") == (30, 39)
        assert detect_age_range("40대") == (40, 49)
        assert detect_age_range("50대") == (50, 59)

    def test_age_under_pattern(self):
        """'XX세 미만' 패턴"""
        assert detect_age_range("40세미만") == (None, 39)
        assert detect_age_range("40세 미만") == (None, 39)

    def test_age_over_pattern(self):
        """'XX세 초과' 패턴"""
        assert detect_age_range("40세초과") == (41, None)
        assert detect_age_range("40세 초과") == (41, None)

    def test_no_age(self):
        """나이 정보 없음"""
        assert detect_age_range("일반플랜") == (None, None)
        assert detect_age_range("") == (None, None)

    def test_none_input(self):
        """None 입력"""
        assert detect_age_range(None) == (None, None)


# =============================================================================
# detect_from_path Tests
# =============================================================================

class TestDetectFromPath:
    """detect_from_path 함수 테스트"""

    def test_detect_from_filename(self):
        """파일명에서 감지"""
        result = detect_from_path("/data/SAMSUNG/남성-40세이하.pdf")
        assert result.gender == "M"
        assert result.age_max == 40
        assert result.detection_source == "filename"

    def test_detect_from_dirname(self):
        """폴더명에서 감지"""
        result = detect_from_path("/data/SAMSUNG/여성플랜/document.pdf")
        assert result.gender == "F"
        assert result.detection_source == "dirname"

    def test_filename_priority(self):
        """파일명이 폴더명보다 우선"""
        result = detect_from_path("/data/여성플랜/남성-40세이하.pdf")
        assert result.gender == "M"
        assert result.detection_source == "filename"

    def test_no_detection(self):
        """감지 정보 없음"""
        result = detect_from_path("/data/SAMSUNG/general.pdf")
        assert result.gender is None
        assert result.age_min is None
        assert result.age_max is None
        assert result.detection_source is None

    def test_empty_path(self):
        """빈 경로"""
        result = detect_from_path("")
        assert result.gender is None

    def test_none_path(self):
        """None 경로"""
        result = detect_from_path(None)
        assert result.gender is None


# =============================================================================
# detect_from_meta Tests
# =============================================================================

class TestDetectFromMeta:
    """detect_from_meta 함수 테스트"""

    def test_detect_from_gender_field(self):
        """meta.gender 필드에서 감지"""
        result = detect_from_meta({"gender": "M", "age_min": 20, "age_max": 40})
        assert result.gender == "M"
        assert result.age_min == 20
        assert result.age_max == 40
        assert result.detection_source == "meta_field"

    def test_detect_from_title(self):
        """meta.title에서 감지"""
        result = detect_from_meta({"title": "여성 41세이상 플랜"})
        assert result.gender == "F"
        assert result.age_min == 41
        assert result.detection_source == "meta_title"

    def test_no_detection(self):
        """감지 정보 없음"""
        result = detect_from_meta({"title": "일반 플랜"})
        assert result.gender is None

    def test_none_meta(self):
        """None 메타"""
        result = detect_from_meta(None)
        assert result.gender is None

    def test_empty_meta(self):
        """빈 메타"""
        result = detect_from_meta({})
        assert result.gender is None


# =============================================================================
# detect_plan_info Tests
# =============================================================================

class TestDetectPlanInfo:
    """detect_plan_info 함수 테스트 (통합)"""

    def test_meta_priority(self):
        """meta가 최우선"""
        result = detect_plan_info(
            source_path="/data/남성플랜/test.pdf",
            doc_title="여성플랜",
            meta={"gender": "F", "age_min": 30},
        )
        assert result.gender == "F"
        assert result.detection_source == "meta_field"

    def test_doc_title_second(self):
        """doc_title이 두 번째"""
        result = detect_plan_info(
            source_path="/data/남성플랜/test.pdf",
            doc_title="여성-40세이하",
            meta={},
        )
        assert result.gender == "F"
        assert result.age_max == 40
        assert result.detection_source == "doc_title"

    def test_path_last(self):
        """source_path가 마지막"""
        result = detect_plan_info(
            source_path="/data/남성-41세이상/test.pdf",
            doc_title=None,
            meta=None,
        )
        assert result.gender == "M"
        assert result.age_min == 41
        assert result.detection_source == "dirname"


# =============================================================================
# find_matching_plan_id Tests (with mock)
# =============================================================================

def _make_mock_cursor(query_results: dict):
    """Mock cursor 생성"""
    cursor = MagicMock()
    results_queue = []

    def execute(query, params=None):
        for key, rows in query_results.items():
            if key in query:
                results_queue.clear()
                results_queue.extend(rows)
                return
        results_queue.clear()

    def fetchone():
        return results_queue[0] if results_queue else None

    cursor.execute = execute
    cursor.fetchone = fetchone
    return cursor


def _make_mock_conn(cursor):
    """Mock connection 생성"""
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn


class TestFindMatchingPlanId:
    """find_matching_plan_id 함수 테스트"""

    def test_no_info_returns_none(self):
        """성별/나이 정보 없으면 None"""
        conn = MagicMock()
        result = find_matching_plan_id(
            conn,
            "SAMSUNG",
            DetectedPlanInfo()
        )
        assert result is None

    def test_no_product_returns_none(self):
        """product 없으면 None"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [],
        })
        conn = _make_mock_conn(cursor)

        result = find_matching_plan_id(
            conn,
            "UNKNOWN",
            DetectedPlanInfo(gender="M", age_min=30)
        )
        assert result is None

    def test_returns_matching_plan(self):
        """매칭되는 plan 반환"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
            "FROM product_plan": [{"plan_id": 101, "plan_name": "남성플랜", "gender": "M", "age_min": 0, "age_max": 99}],
        })
        conn = _make_mock_conn(cursor)

        result = find_matching_plan_id(
            conn,
            "SAMSUNG",
            DetectedPlanInfo(gender="M", age_min=30, age_max=40)
        )
        assert result == 101


# =============================================================================
# detect_plan_id Tests (통합)
# =============================================================================

class TestDetectPlanId:
    """detect_plan_id 함수 테스트 (통합)"""

    def test_no_detection_returns_none(self):
        """감지 정보 없으면 plan_id=None"""
        conn = MagicMock()
        result = detect_plan_id(
            conn,
            "SAMSUNG",
            "/data/general.pdf",
            None,
            None,
        )
        assert result.plan_id is None
        assert result.reason == "no_plan_info_detected"

    def test_detection_with_match(self):
        """감지 후 매칭 성공"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
            "FROM product_plan": [{"plan_id": 101, "plan_name": "남성-40세이하", "gender": "M", "age_min": 0, "age_max": 40}],
        })
        conn = _make_mock_conn(cursor)

        result = detect_plan_id(
            conn,
            "SAMSUNG",
            "/data/남성-40세이하.pdf",
            None,
            None,
        )
        assert result.plan_id == 101
        assert "gender=M" in result.reason
        assert result.detected_info.gender == "M"

    def test_detection_no_match(self):
        """감지 후 매칭 실패"""
        cursor = _make_mock_cursor({
            "SELECT p.product_id": [{"product_id": 1}],
            "FROM product_plan": [],  # 매칭 없음
        })
        conn = _make_mock_conn(cursor)

        result = detect_plan_id(
            conn,
            "SAMSUNG",
            "/data/남성-200세이상.pdf",  # 극단적인 나이
            None,
            None,
        )
        assert result.plan_id is None
        assert "no_matching_plan" in result.reason


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_complex_filename(self):
        """복잡한 파일명"""
        result = detect_from_path("/data/SAMSUNG/상품요약서/삼성화재_암보험_남성_40세이하_v2511.pdf")
        assert result.gender == "M"
        assert result.age_max == 40

    def test_unicode_path(self):
        """유니코드 경로"""
        result = detect_from_path("/데이터/삼성화재/여성플랜/약관.pdf")
        assert result.gender == "F"

    def test_mixed_patterns(self):
        """혼합 패턴"""
        result = detect_from_path("/data/남성_30대_plan.pdf")
        assert result.gender == "M"
        assert result.age_min == 30
        assert result.age_max == 39

    def test_path_with_spaces(self):
        """공백이 있는 경로"""
        result = detect_from_path("/data/SAMSUNG/남성 40세 이하 플랜.pdf")
        assert result.gender == "M"
        assert result.age_max == 40


# =============================================================================
# Pattern Coverage Tests
# =============================================================================

class TestPatternCoverage:
    """패턴 커버리지 테스트"""

    @pytest.mark.parametrize("text,expected", [
        ("남성", "M"),
        ("남자", "M"),
        ("(남)", "M"),
        ("_남_", "M"),
        ("-남-", "M"),
        ("남형", "M"),
        ("male", "M"),
        ("M형", "M"),
        ("남성형", "M"),
    ])
    def test_all_male_patterns(self, text, expected):
        """모든 남성 패턴"""
        assert detect_gender(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("여성", "F"),
        ("여자", "F"),
        ("(여)", "F"),
        ("_여_", "F"),
        ("-여-", "F"),
        ("여형", "F"),
        ("female", "F"),
        ("F형", "F"),
        ("여성형", "F"),
    ])
    def test_all_female_patterns(self, text, expected):
        """모든 여성 패턴"""
        assert detect_gender(text) == expected

    @pytest.mark.parametrize("text,expected_min,expected_max", [
        ("40세이하", None, 40),
        ("41세이상", 41, None),
        ("20-40세", 20, 40),
        ("만40세", 40, 40),
        ("30대", 30, 39),
        ("40세미만", None, 39),
        ("40세초과", 41, None),
    ])
    def test_all_age_patterns(self, text, expected_min, expected_max):
        """모든 나이 패턴"""
        age_min, age_max = detect_age_range(text)
        assert age_min == expected_min
        assert age_max == expected_max
