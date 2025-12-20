"""
STEP 4.1: Subtype Extractor Tests

다중 Subtype 비교 기능 검증
"""

import pytest


class TestSubtypeExtraction:
    """Subtype 추출 테스트"""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """각 테스트 전에 캐시 리셋"""
        import services.extraction.subtype_extractor as se
        se.reset_subtype_cache()
        yield

    def test_extract_single_subtype(self):
        """단일 subtype 추출 테스트"""
        from services.extraction.subtype_extractor import extract_subtypes_from_query

        result = extract_subtypes_from_query("경계성 종양 보장 여부")
        assert len(result) == 1
        assert result[0].code == "BORDERLINE_TUMOR"
        assert result[0].name == "경계성 종양"

    def test_extract_multi_subtype(self):
        """복수 subtype 추출 테스트"""
        from services.extraction.subtype_extractor import extract_subtypes_from_query

        result = extract_subtypes_from_query("경계성 종양과 제자리암 차이")
        assert len(result) == 2
        codes = {r.code for r in result}
        assert "BORDERLINE_TUMOR" in codes
        assert "CIS_CARCINOMA" in codes

    def test_is_multi_subtype_query(self):
        """복수 subtype 질의 판별 테스트"""
        from services.extraction.subtype_extractor import is_multi_subtype_query

        assert is_multi_subtype_query("경계성 종양과 제자리암 비교") is True
        assert is_multi_subtype_query("경계성 종양 보장") is False
        assert is_multi_subtype_query("암진단비 알려줘") is False

    def test_alias_matching(self):
        """Alias 매칭 테스트"""
        from services.extraction.subtype_extractor import extract_subtypes_from_query

        # 상피내암 → CIS_CARCINOMA
        result = extract_subtypes_from_query("상피내암 보장되나요")
        assert len(result) == 1
        assert result[0].code == "CIS_CARCINOMA"

    def test_get_subtype_definition(self):
        """Subtype 정의 조회 테스트"""
        from services.extraction.subtype_extractor import get_subtype_definition

        defn = get_subtype_definition("BORDERLINE_TUMOR")
        assert defn is not None
        assert defn.name == "경계성 종양"
        assert defn.domain == "CANCER"
        assert "경계성 종양" in defn.aliases

    def test_get_subtypes_by_domain(self):
        """도메인별 subtype 조회 테스트"""
        from services.extraction.subtype_extractor import get_subtypes_by_domain

        cancer_subtypes = get_subtypes_by_domain("CANCER")
        assert len(cancer_subtypes) >= 3  # BORDERLINE_TUMOR, CIS_CARCINOMA, SIMILAR_CANCER
        codes = {s.code for s in cancer_subtypes}
        assert "BORDERLINE_TUMOR" in codes


class TestConfigLoading:
    """설정 파일 로드 테스트 (헌법 준수 검증)"""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """각 테스트 전에 캐시 리셋"""
        import services.extraction.subtype_extractor as se
        se.reset_subtype_cache()
        yield

    def test_config_file_exists(self):
        """설정 파일 존재 확인"""
        from services.extraction.subtype_extractor import _get_config_path

        path = _get_config_path()
        assert path.exists(), f"Config file not found: {path}"

    def test_subtypes_loaded_from_yaml(self):
        """Subtype 정의가 YAML에서 로드되는지 확인"""
        from services.extraction.subtype_extractor import _get_subtype_definitions

        definitions = _get_subtype_definitions()
        assert len(definitions) > 0
        assert "BORDERLINE_TUMOR" in definitions
        assert "CIS_CARCINOMA" in definitions
