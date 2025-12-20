"""
Query Normalization Tests

헌법 준수 검증:
- normalize_query_for_coverage()가 설정 파일에서 규칙을 로드하는지 확인
- 보험사명/의도표현/조사가 올바르게 제거되는지 확인
"""

import pytest


class TestNormalizeQueryForCoverage:
    """normalize_query_for_coverage() 함수 테스트"""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """각 테스트 전에 캐시 리셋"""
        import services.retrieval.compare_service as cs
        cs._INSURER_ALIASES = None
        cs._NORMALIZATION_RULES = None
        yield

    def test_insurer_name_removal_basic(self):
        """기본 보험사명 제거 테스트"""
        from services.retrieval.compare_service import normalize_query_for_coverage

        # 삼성 제거
        assert normalize_query_for_coverage("삼성 암진단비") == "암진단비"

    def test_insurer_name_removal_multiple(self):
        """복수 보험사명 제거 테스트"""
        from services.retrieval.compare_service import normalize_query_for_coverage

        # 삼성과 현대 모두 제거, 조사 "과"도 제거
        result = normalize_query_for_coverage("삼성과 현대 다빈치 수술비를 비교해줘")
        assert result == "다빈치수술비"

    def test_intent_suffix_removal(self):
        """의도 표현 suffix 제거 테스트"""
        from services.retrieval.compare_service import normalize_query_for_coverage

        # "알려줘" 제거
        assert normalize_query_for_coverage("메리츠 뇌졸중진단비 알려줘") == "뇌졸중진단비"

        # "비교해줘" 제거
        assert normalize_query_for_coverage("암진단비 비교해줘") == "암진단비"

    def test_whitespace_removal(self):
        """공백 제거 테스트"""
        from services.retrieval.compare_service import normalize_query_for_coverage

        assert normalize_query_for_coverage("다빈치 수술비") == "다빈치수술비"

    def test_trailing_particle_removal(self):
        """끝 조사 제거 테스트"""
        from services.retrieval.compare_service import normalize_query_for_coverage

        # "를" 제거 (비교 제거 후 남은 조사)
        result = normalize_query_for_coverage("다빈치 수술비를 비교")
        assert result == "다빈치수술비"

    def test_same_result_with_or_without_insurer(self):
        """보험사명 유무에 따른 결과 일치 테스트 (핵심 회귀 테스트)"""
        from services.retrieval.compare_service import normalize_query_for_coverage

        # 이 두 질의는 동일한 정규화 결과를 가져야 함
        with_insurer = normalize_query_for_coverage("삼성과 현대 다빈치 수술비를 비교해줘")
        without_insurer = normalize_query_for_coverage("다빈치 수술비를 비교해줘")

        assert with_insurer == without_insurer == "다빈치수술비"


class TestConfigLoading:
    """설정 파일 로드 테스트 (헌법 준수 검증)"""

    def test_insurer_alias_loaded_from_yaml(self):
        """보험사 alias가 YAML에서 로드되는지 확인"""
        import services.retrieval.compare_service as cs
        cs._INSURER_ALIASES = None

        aliases = cs._load_insurer_aliases()

        # 최소한 일부 alias가 로드되어야 함
        assert len(aliases) > 0
        # 삼성, 현대 등 기본 alias 포함 확인
        assert "삼성" in aliases
        assert "현대" in aliases

    def test_normalization_rules_loaded_from_yaml(self):
        """정규화 규칙이 YAML에서 로드되는지 확인"""
        import services.retrieval.compare_service as cs
        cs._NORMALIZATION_RULES = None

        rules = cs._load_normalization_rules()

        # 필수 키 존재 확인
        assert "intent_suffixes" in rules
        assert "trailing_particles_pattern" in rules
        assert len(rules["intent_suffixes"]) > 0

    def test_no_hardcoded_fallback(self):
        """하드코딩 fallback이 없는지 확인 (헌법 준수)"""
        import inspect
        import services.retrieval.compare_service as cs

        # _load_insurer_aliases 소스 코드에 하드코딩 리스트가 없어야 함
        source = inspect.getsource(cs._load_insurer_aliases)
        # 긴 리스트 형태의 하드코딩이 없어야 함
        assert "메리츠손해보험" not in source
        assert "현대손해보험" not in source
