"""
Coverage Extractor

chunk content에서 coverage_code를 추출하는 모듈

doc_type별 정책:
- 약관: 헤더/조문명 패턴("제X조(담보명)")에서만 추출 (오탐 방지)
- 가입설계서/상품요약서/사업방법서: 본문 전체에서 추출

우선순위 (약관 제외):
1. doc_type='가입설계서' → insurer_id + source_doc_type='가입설계서' 범위
2. insurer_id 범위 (source_doc_type 무시)
3. ontology fallback → 신정원 표준코드로 리매핑

match_source 종류:
- 'mapping': coverage_alias에서 직접 매칭
- 'clause_header': 약관 조문 헤더에서 추출
- 'fallback_remap': ontology 매칭 후 신정원 코드로 리매핑 성공
- 'fallback_unmapped': ontology 매칭되었으나 리매핑 실패 (coverage_code=None)

tag_source 종류 (약관 전용):
- 'clause_header': 조문 헤더에서 추출

confidence 종류:
- 'high': 조문 헤더 패턴 매칭
- 'medium': DB alias 매칭
- 'low': ontology fallback
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .coverage_ontology import COVERAGE_ONTOLOGY, CoverageCode
from .normalize import normalize_content_for_matching, normalize_coverage_name


def get_db_url() -> str:
    """환경변수에서 DB URL 가져오기"""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/inca_rag",
    )


@dataclass
class CoverageMatch:
    """Coverage 매칭 결과"""

    code: str | None           # 신정원 표준코드 (리매핑 실패 시 None)
    name: str | None           # coverage_name (리매핑 실패 시 None)
    alias_hit: str             # 매칭된 텍스트
    position: int              # 텍스트 내 위치
    match_source: str          # 'mapping' | 'clause_header' | 'fallback_remap' | 'fallback_unmapped'
    ontology_code: str | None = None  # fallback 시 원래 ontology 코드
    tag_source: str | None = None     # 약관 전용: 'clause_header'
    confidence: str = "medium"        # 'high' | 'medium' | 'low'


@dataclass
class AliasEntry:
    """DB alias 엔트리"""

    raw_name_norm: str
    coverage_code: str
    coverage_name: str
    source_doc_type: str


@dataclass
class OntologyRemapResult:
    """Ontology → 신정원 코드 리매핑 결과"""

    coverage_code: str | None
    coverage_name: str | None
    success: bool


class CoverageExtractor:
    """Coverage Code 추출기"""

    def __init__(self, db_url: str | None = None, use_db: bool = True):
        """
        Args:
            db_url: DB URL (None이면 환경변수 사용)
            use_db: DB 매핑 사용 여부 (False면 ontology만 사용)
        """
        self._db_url = db_url or get_db_url()
        self._use_db = use_db
        self._conn: psycopg.Connection | None = None

        # DB 매핑 캐시: insurer_id -> list[AliasEntry]
        self._alias_cache: dict[int, list[AliasEntry]] = {}
        self._alias_cache_loaded = False

        # Ontology → 신정원 코드 리매핑 캐시
        self._ontology_remap_cache: dict[str, OntologyRemapResult] = {}
        self._ontology_remap_loaded = False

        # Ontology 패턴 (fallback용)
        self._ontology_patterns: list[tuple[re.Pattern, CoverageCode, str]] = []
        self._build_ontology_patterns()

        # 약관 조문 헤더 패턴
        self._clause_header_patterns = self._build_clause_header_patterns()

    def _build_ontology_patterns(self) -> None:
        """Ontology 기반 정규식 패턴 빌드"""
        all_aliases: list[tuple[str, CoverageCode]] = []

        for cov in COVERAGE_ONTOLOGY:
            for alias in cov.aliases:
                all_aliases.append((alias, cov))

        # 길이 내림차순 정렬 (더 긴 alias 우선 매칭)
        all_aliases.sort(key=lambda x: len(x[0]), reverse=True)

        for alias, cov in all_aliases:
            pattern = re.compile(re.escape(alias), re.IGNORECASE)
            self._ontology_patterns.append((pattern, cov, alias))

    def _build_clause_header_patterns(self) -> list[re.Pattern]:
        """
        약관 조문 헤더 패턴 빌드

        패턴 목록:
        - 제X조(담보명) : "제1조(보험금의 지급사유)"
        - 제X조의Y(담보명) : "제1조의2(특별약관의 적용)"
        - [담보명] : "[갑상선암 진단비]"
        - <담보명> : "<암 진단비 특약>"
        - X. 담보명 특별약관 : "1. 암진단비 특별약관"
        - X-Y. 담보명 특별약관 : "1-2. 갑상선암 진단비 특별약관"
        """
        return [
            # 제X조(담보명) 또는 제X조의Y(담보명)
            re.compile(r"제\s*\d+\s*조(?:의\s*\d+)?\s*\(([^)]+)\)", re.MULTILINE),
            # [담보명] - 줄 시작 또는 공백 뒤
            re.compile(r"(?:^|\s)\[([^\]]{2,50})\]", re.MULTILINE),
            # <담보명> - 줄 시작 또는 공백 뒤
            re.compile(r"(?:^|\s)<([^>]{2,50})>", re.MULTILINE),
            # X. 담보명 특별약관 또는 X-Y. 담보명 특별약관
            re.compile(r"(?:^|\n)\s*\d+(?:-\d+)*\.\s*([^\n]{2,50}?(?:특별약관|특약))", re.MULTILINE),
            # X-Y-Z. 담보명 (담보 목록에서)
            re.compile(r"(?:^|\n)\s*\d+(?:-\d+)+\.\s*([^\n]{2,50}?)(?:\s|$)", re.MULTILINE),
        ]

    def _extract_from_clause_header(
        self,
        content: str,
        insurer_id: int | None,
    ) -> CoverageMatch | None:
        """
        약관 조문 헤더에서 coverage 추출 (약관 전용)

        헤더 패턴에서 담보명 추출 → DB alias/ontology 매칭

        Args:
            content: chunk 텍스트
            insurer_id: 보험사 ID

        Returns:
            CoverageMatch 또는 None
        """
        if not content:
            return None

        # 헤더에서 담보명 후보 추출
        header_candidates: list[tuple[str, int]] = []  # (담보명, position)

        for pattern in self._clause_header_patterns:
            for match in pattern.finditer(content):
                candidate = match.group(1).strip()
                if candidate and len(candidate) >= 2:
                    header_candidates.append((candidate, match.start()))

        if not header_candidates:
            return None

        # 위치순 정렬 (문서 앞쪽 우선)
        header_candidates.sort(key=lambda x: x[1])

        # 각 후보에 대해 DB alias 매칭 시도
        if insurer_id:
            self._load_alias_cache(insurer_id)
            aliases = self._alias_cache.get(insurer_id, [])
        else:
            self._load_all_aliases()
            aliases = []
            for alias_list in self._alias_cache.values():
                aliases.extend(alias_list)

        for candidate, position in header_candidates:
            candidate_norm = normalize_content_for_matching(candidate)
            if not candidate_norm:
                continue

            # DB alias 매칭
            for entry in aliases:
                # 양방향 포함 관계 체크 (alias가 candidate에 포함되거나, candidate가 alias에 포함)
                if entry.raw_name_norm in candidate_norm or candidate_norm in entry.raw_name_norm:
                    return CoverageMatch(
                        code=entry.coverage_code,
                        name=entry.coverage_name,
                        alias_hit=candidate,
                        position=position,
                        match_source="clause_header",
                        ontology_code=None,
                        tag_source="clause_header",
                        confidence="high",
                    )

            # Ontology 매칭 (DB 매칭 실패 시)
            for pattern, cov, alias in self._ontology_patterns:
                if pattern.search(candidate):
                    remap_result = self._remap_ontology_code(cov.code)
                    if remap_result.success:
                        return CoverageMatch(
                            code=remap_result.coverage_code,
                            name=remap_result.coverage_name,
                            alias_hit=candidate,
                            position=position,
                            match_source="clause_header",
                            ontology_code=cov.code,
                            tag_source="clause_header",
                            confidence="high",
                        )

        return None

    def _get_db_connection(self) -> psycopg.Connection | None:
        """DB 연결 (lazy)"""
        if not self._use_db:
            return None

        if self._conn is None:
            try:
                self._conn = psycopg.connect(self._db_url, row_factory=dict_row)
            except Exception:
                self._use_db = False
                return None

        return self._conn

    def _load_ontology_remap_cache(self) -> None:
        """coverage_standard.meta.ontology_codes에서 리매핑 캐시 로드"""
        if self._ontology_remap_loaded:
            return

        conn = self._get_db_connection()
        if not conn:
            self._ontology_remap_loaded = True
            return

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT coverage_code, coverage_name, meta->'ontology_codes' AS ontology_codes
                    FROM coverage_standard
                    WHERE meta->'ontology_codes' IS NOT NULL
                    """
                )
                rows = cur.fetchall()

                for row in rows:
                    ontology_codes = row["ontology_codes"]
                    if ontology_codes:
                        for ont_code in ontology_codes:
                            self._ontology_remap_cache[ont_code] = OntologyRemapResult(
                                coverage_code=row["coverage_code"],
                                coverage_name=row["coverage_name"],
                                success=True,
                            )

                self._ontology_remap_loaded = True
        except Exception:
            self._ontology_remap_loaded = True

    def _remap_ontology_code(self, ontology_code: str) -> OntologyRemapResult:
        """
        ontology_code를 신정원 표준코드로 리매핑

        Returns:
            OntologyRemapResult (success=False면 리매핑 실패)
        """
        self._load_ontology_remap_cache()

        if ontology_code in self._ontology_remap_cache:
            return self._ontology_remap_cache[ontology_code]

        # 캐시에 없으면 DB에서 직접 조회 (캐시 로드 후 추가된 경우 대비)
        conn = self._get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT coverage_code, coverage_name
                        FROM coverage_standard
                        WHERE (meta->'ontology_codes') ? %s
                        LIMIT 1
                        """,
                        (ontology_code,),
                    )
                    row = cur.fetchone()
                    if row:
                        result = OntologyRemapResult(
                            coverage_code=row["coverage_code"],
                            coverage_name=row["coverage_name"],
                            success=True,
                        )
                        self._ontology_remap_cache[ontology_code] = result
                        return result
            except Exception:
                pass

        # 리매핑 실패
        result = OntologyRemapResult(
            coverage_code=None,
            coverage_name=None,
            success=False,
        )
        self._ontology_remap_cache[ontology_code] = result
        return result

    def _load_alias_cache(self, insurer_id: int) -> None:
        """특정 insurer의 alias 캐시 로드"""
        if insurer_id in self._alias_cache:
            return

        conn = self._get_db_connection()
        if not conn:
            self._alias_cache[insurer_id] = []
            return

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ca.raw_name_norm, ca.coverage_code, cs.coverage_name, ca.source_doc_type
                    FROM coverage_alias ca
                    JOIN coverage_standard cs ON ca.coverage_code = cs.coverage_code
                    WHERE ca.insurer_id = %s
                    ORDER BY LENGTH(ca.raw_name_norm) DESC
                    """,
                    (insurer_id,),
                )
                rows = cur.fetchall()

                self._alias_cache[insurer_id] = [
                    AliasEntry(
                        raw_name_norm=row["raw_name_norm"],
                        coverage_code=row["coverage_code"],
                        coverage_name=row["coverage_name"],
                        source_doc_type=row["source_doc_type"],
                    )
                    for row in rows
                ]
        except Exception:
            self._alias_cache[insurer_id] = []

    def _load_all_aliases(self) -> None:
        """전체 alias 캐시 로드 (insurer 불특정 시)"""
        if self._alias_cache_loaded:
            return

        conn = self._get_db_connection()
        if not conn:
            self._alias_cache_loaded = True
            return

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ca.insurer_id, ca.raw_name_norm, ca.coverage_code,
                           cs.coverage_name, ca.source_doc_type
                    FROM coverage_alias ca
                    JOIN coverage_standard cs ON ca.coverage_code = cs.coverage_code
                    ORDER BY LENGTH(ca.raw_name_norm) DESC
                    """
                )
                rows = cur.fetchall()

                for row in rows:
                    insurer_id = row["insurer_id"]
                    if insurer_id not in self._alias_cache:
                        self._alias_cache[insurer_id] = []
                    self._alias_cache[insurer_id].append(
                        AliasEntry(
                            raw_name_norm=row["raw_name_norm"],
                            coverage_code=row["coverage_code"],
                            coverage_name=row["coverage_name"],
                            source_doc_type=row["source_doc_type"],
                        )
                    )

                self._alias_cache_loaded = True
        except Exception:
            self._alias_cache_loaded = True

    def _match_from_aliases(
        self,
        content_norm: str,
        aliases: list[AliasEntry],
        filter_doc_type: str | None = None,
    ) -> CoverageMatch | None:
        """
        alias 리스트에서 매칭 시도

        Args:
            content_norm: 정규화된 content
            aliases: alias 목록 (길이 내림차순 정렬 권장)
            filter_doc_type: 특정 doc_type만 필터 (None이면 전체)

        Returns:
            CoverageMatch 또는 None
        """
        for entry in aliases:
            # doc_type 필터
            if filter_doc_type and entry.source_doc_type != filter_doc_type:
                continue

            # substring 매칭
            idx = content_norm.find(entry.raw_name_norm)
            if idx >= 0:
                return CoverageMatch(
                    code=entry.coverage_code,
                    name=entry.coverage_name,
                    alias_hit=entry.raw_name_norm,
                    position=idx,
                    match_source="mapping",
                    ontology_code=None,
                    confidence="medium",
                )

        return None

    def _extract_from_mapping(
        self,
        content: str,
        insurer_id: int | None,
        doc_type: str | None,
    ) -> CoverageMatch | None:
        """
        DB 매핑에서 coverage 추출

        우선순위:
        1. doc_type='가입설계서' → insurer_id + source_doc_type='가입설계서'
        2. insurer_id 범위 (source_doc_type 무시)

        Args:
            content: 검색할 텍스트
            insurer_id: 보험사 ID (None이면 전체 검색)
            doc_type: 문서 유형

        Returns:
            CoverageMatch 또는 None
        """
        if not self._use_db:
            return None

        # content 정규화 (동일한 규칙 적용)
        content_norm = normalize_content_for_matching(content)
        if not content_norm:
            return None

        if insurer_id:
            self._load_alias_cache(insurer_id)
            aliases = self._alias_cache.get(insurer_id, [])

            # 1순위: doc_type='가입설계서' → source_doc_type='가입설계서'만
            if doc_type == "가입설계서":
                match = self._match_from_aliases(
                    content_norm, aliases, filter_doc_type="가입설계서"
                )
                if match:
                    return match

            # 2순위: insurer_id 범위 (source_doc_type 무시)
            match = self._match_from_aliases(content_norm, aliases)
            if match:
                return match

        else:
            # insurer_id 없으면 전체 검색
            self._load_all_aliases()

            # 전체 alias 통합 (길이순 정렬)
            all_aliases: list[AliasEntry] = []
            for alias_list in self._alias_cache.values():
                all_aliases.extend(alias_list)
            all_aliases.sort(key=lambda x: len(x.raw_name_norm), reverse=True)

            match = self._match_from_aliases(content_norm, all_aliases)
            if match:
                return match

        return None

    def _extract_from_ontology(self, content: str) -> CoverageMatch | None:
        """
        Ontology에서 coverage 추출 후 신정원 코드로 리매핑 시도

        Returns:
            CoverageMatch:
            - 리매핑 성공: code=신정원코드, match_source='fallback_remap'
            - 리매핑 실패: code=None, match_source='fallback_unmapped'
        """
        if not content:
            return None

        best_match: tuple[CoverageCode, str, int] | None = None  # (cov, alias, position)

        for pattern, cov, alias in self._ontology_patterns:
            match = pattern.search(content)
            if match:
                position = match.start()

                if best_match is None or position < best_match[2]:
                    best_match = (cov, alias, position)
                    if position == 0:
                        break

        if best_match is None:
            return None

        cov, alias_hit, position = best_match
        ontology_code = cov.code

        # 신정원 코드로 리매핑 시도
        remap_result = self._remap_ontology_code(ontology_code)

        if remap_result.success:
            return CoverageMatch(
                code=remap_result.coverage_code,
                name=remap_result.coverage_name,
                alias_hit=alias_hit,
                position=position,
                match_source="fallback_remap",
                ontology_code=ontology_code,
                confidence="low",
            )
        else:
            # 리매핑 실패: coverage_code=None으로 설정 (표준코드 체계 오염 방지)
            return CoverageMatch(
                code=None,
                name=None,
                alias_hit=alias_hit,
                position=position,
                match_source="fallback_unmapped",
                ontology_code=ontology_code,
                confidence="low",
            )

    def extract(
        self,
        content: str,
        insurer_id: int | None = None,
        doc_type: str | None = None,
    ) -> CoverageMatch | None:
        """
        content에서 coverage_code 추출

        doc_type별 정책:
        - 약관: 헤더/조문명 패턴에서만 추출 (오탐 방지)
        - 그 외: 본문 전체에서 추출

        우선순위 (약관 제외):
        1. doc_type='가입설계서' → insurer_id + source_doc_type='가입설계서'
        2. insurer_id 범위 (source_doc_type 무시)
        3. ontology fallback → 신정원 코드 리매핑

        Args:
            content: 검색할 텍스트
            insurer_id: 보험사 ID (BIGINT, 있으면 해당 보험사 매핑 우선)
            doc_type: 문서 유형 (약관일 때 헤더만 매칭)

        Returns:
            CoverageMatch 또는 None
        """
        if not content:
            return None

        # 약관: 헤더/조문명 패턴에서만 추출 (오탐 방지)
        if doc_type == "약관":
            return self._extract_from_clause_header(content, insurer_id)

        # 약관 외 문서: 기존 로직
        # 1~2순위: DB 매핑
        match = self._extract_from_mapping(content, insurer_id, doc_type)
        if match:
            return match

        # 3순위: Ontology fallback + 리매핑
        return self._extract_from_ontology(content)

    def extract_all(
        self,
        content: str,
        insurer_id: int | None = None,
        doc_type: str | None = None,
    ) -> list[CoverageMatch]:
        """
        content에서 모든 coverage_code 추출 (중복 코드 제거)
        """
        if not content:
            return []

        matches: dict[str, CoverageMatch] = {}
        content_norm = normalize_content_for_matching(content)

        # DB 매핑
        if insurer_id:
            self._load_alias_cache(insurer_id)
            aliases = self._alias_cache.get(insurer_id, [])
        else:
            self._load_all_aliases()
            aliases = []
            for alias_list in self._alias_cache.values():
                aliases.extend(alias_list)
            aliases.sort(key=lambda x: len(x.raw_name_norm), reverse=True)

        for entry in aliases:
            if entry.coverage_code in matches:
                continue
            idx = content_norm.find(entry.raw_name_norm)
            if idx >= 0:
                matches[entry.coverage_code] = CoverageMatch(
                    code=entry.coverage_code,
                    name=entry.coverage_name,
                    alias_hit=entry.raw_name_norm,
                    position=idx,
                    match_source="mapping",
                    ontology_code=None,
                    confidence="medium",
                )

        # Ontology fallback + 리매핑
        for pattern, cov, alias in self._ontology_patterns:
            match = pattern.search(content)
            if match:
                ontology_code = cov.code
                remap_result = self._remap_ontology_code(ontology_code)

                if remap_result.success:
                    if remap_result.coverage_code not in matches:
                        matches[remap_result.coverage_code] = CoverageMatch(
                            code=remap_result.coverage_code,
                            name=remap_result.coverage_name,
                            alias_hit=alias,
                            position=match.start(),
                            match_source="fallback_remap",
                            ontology_code=ontology_code,
                            confidence="low",
                        )

        return sorted(matches.values(), key=lambda x: x.position)

    def to_meta_entities(self, match: CoverageMatch | None) -> dict[str, Any]:
        """
        CoverageMatch를 meta.entities 형식으로 변환

        Returns:
            {
                "coverage_code": str | None,  # 신정원 코드 (리매핑 실패 시 None)
                "coverage_name": str | None,
                "alias_hit": str,
                "match_source": str,
                "ontology_code": str | None,  # fallback 시 원래 ontology 코드
                "tag_source": str | None,     # 약관 전용: 'clause_header'
                "confidence": str,            # 'high' | 'medium' | 'low'
            }
        """
        if match is None:
            return {}

        result: dict[str, Any] = {
            "alias_hit": match.alias_hit,
            "match_source": match.match_source,
            "confidence": match.confidence,
        }

        # coverage_code는 신정원 코드만 저장 (None이면 저장 안 함)
        if match.code is not None:
            result["coverage_code"] = match.code
        if match.name is not None:
            result["coverage_name"] = match.name

        # ontology_code는 fallback 시에만 저장
        if match.ontology_code is not None:
            result["ontology_code"] = match.ontology_code

        # tag_source는 약관 헤더 매칭 시에만 저장
        if match.tag_source is not None:
            result["tag_source"] = match.tag_source

        return result

    def close(self) -> None:
        """DB 연결 종료"""
        if self._conn:
            self._conn.close()
            self._conn = None


# 싱글톤 인스턴스
_extractor: CoverageExtractor | None = None


def get_extractor(use_db: bool = True) -> CoverageExtractor:
    """CoverageExtractor 싱글톤 반환"""
    global _extractor
    if _extractor is None:
        _extractor = CoverageExtractor(use_db=use_db)
    return _extractor


def reset_extractor() -> None:
    """싱글톤 초기화 (테스트/캐시 갱신용)"""
    global _extractor
    if _extractor is not None:
        _extractor.close()
        _extractor = None


def extract_coverage(
    content: str,
    insurer_id: int | None = None,
    doc_type: str | None = None,
) -> dict[str, Any]:
    """
    편의 함수: content에서 coverage 추출하여 meta.entities 형식 반환

    Args:
        content: 검색할 텍스트
        insurer_id: 보험사 ID (BIGINT)
        doc_type: 문서 유형

    Returns:
        {} 또는 {
            "coverage_code": str | None,
            "coverage_name": str | None,
            "alias_hit": str,
            "match_source": str,
            "ontology_code": str | None,
        }
    """
    extractor = get_extractor()
    match = extractor.extract(content, insurer_id, doc_type)
    return extractor.to_meta_entities(match)
