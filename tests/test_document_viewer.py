"""
Step U-2 / U-2.5: Document Viewer API 테스트

GET /documents/{document_id}/page/{page} 엔드포인트 검증
GET /documents/{document_id}/page/{page}/spans 엔드포인트 검증
"""

from __future__ import annotations

import os

import pytest
import requests

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")


class TestDocumentViewerAPI:
    """Document Viewer API 테스트"""

    def test_get_page_success(self):
        """정상: 200 + content-type image/png"""
        # document_id=1 (첫 번째 문서), page=1
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1",
            params={"scale": 2.0},
            timeout=30,
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.headers.get("content-type") == "image/png"
        assert len(resp.content) > 1000, "PNG should have substantial content"

    def test_page_out_of_range(self):
        """페이지 범위 초과: 404"""
        # 매우 큰 페이지 번호
        resp = requests.get(
            f"{API_BASE}/documents/1/page/9999",
            timeout=30,
        )

        assert resp.status_code == 404

    def test_document_not_found(self):
        """document_id 없음: 404"""
        # 존재하지 않는 document_id
        resp = requests.get(
            f"{API_BASE}/documents/999999/page/1",
            timeout=30,
        )

        assert resp.status_code == 404

    def test_scale_clamp_min(self):
        """scale 최소값 클램핑 (1.0 미만)"""
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1",
            params={"scale": 0.5},  # 최소 1.0 이하
            timeout=30,
        )

        # FastAPI Query validation이 400 또는 422를 반환
        assert resp.status_code in [400, 422]

    def test_scale_clamp_max(self):
        """scale 최대값 클램핑 (4.0 초과)"""
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1",
            params={"scale": 5.0},  # 최대 4.0 초과
            timeout=30,
        )

        # FastAPI Query validation이 400 또는 422를 반환
        assert resp.status_code in [400, 422]

    def test_default_scale(self):
        """scale 미지정 시 기본값 2.0 사용"""
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1",
            timeout=30,
        )

        # scale 미지정이어도 정상 동작
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "image/png"

    def test_different_pages(self):
        """다른 페이지 요청"""
        # page 1
        resp1 = requests.get(f"{API_BASE}/documents/1/page/1", timeout=30)
        # page 2 (있다면)
        resp2 = requests.get(f"{API_BASE}/documents/1/page/2", timeout=30)

        assert resp1.status_code == 200
        # page 2는 있을 수도 있고 없을 수도 있음
        assert resp2.status_code in [200, 404]


class TestDocumentInfoAPI:
    """Document Info API 테스트"""

    def test_get_info_success(self):
        """문서 정보 조회 성공"""
        resp = requests.get(
            f"{API_BASE}/documents/1/info",
            timeout=30,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "document_id" in data
        assert "page_count" in data
        assert "source_path" in data
        assert data["page_count"] >= 1

    def test_get_info_not_found(self):
        """존재하지 않는 문서 정보 조회"""
        resp = requests.get(
            f"{API_BASE}/documents/999999/info",
            timeout=30,
        )

        assert resp.status_code == 404


class TestSpansAPI:
    """Spans API 테스트 (Step U-2.5)"""

    def test_spans_success(self):
        """정상: hits 배열 반환 (빈 배열도 가능)"""
        # 첫 번째 문서의 첫 페이지에서 검색
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1/spans",
            params={"q": "보험"},  # 보험 문서이므로 "보험" 키워드 존재 가능
            timeout=30,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "document_id" in data
        assert "page" in data
        assert "hits" in data
        assert isinstance(data["hits"], list)

    def test_spans_with_hits(self):
        """hits가 있는 경우 bbox 포함 확인"""
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1/spans",
            params={"q": "보험"},
            timeout=30,
        )

        assert resp.status_code == 200
        data = resp.json()

        # hits가 있으면 bbox 구조 확인
        if len(data["hits"]) > 0:
            hit = data["hits"][0]
            assert "bbox" in hit
            assert "score" in hit
            assert "text" in hit
            assert len(hit["bbox"]) == 4  # [x0, y0, x1, y1]
            assert hit["score"] >= 0.0 and hit["score"] <= 1.0

    def test_spans_no_match(self):
        """매칭 없음: hits=[] (200 OK)"""
        # 존재하지 않을 가능성 높은 텍스트
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1/spans",
            params={"q": "xyzzy_nonexistent_text_12345"},
            timeout=30,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["hits"] == []

    def test_spans_document_not_found(self):
        """document_id 없음: 404"""
        resp = requests.get(
            f"{API_BASE}/documents/999999/page/1/spans",
            params={"q": "test"},
            timeout=30,
        )

        assert resp.status_code == 404

    def test_spans_page_out_of_range(self):
        """페이지 범위 초과: 404"""
        resp = requests.get(
            f"{API_BASE}/documents/1/page/9999/spans",
            params={"q": "test"},
            timeout=30,
        )

        assert resp.status_code == 404

    def test_spans_query_required(self):
        """q 파라미터 필수: 422"""
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1/spans",
            timeout=30,
        )

        assert resp.status_code == 422

    def test_spans_max_hits(self):
        """max_hits 파라미터 동작 확인"""
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1/spans",
            params={"q": "보험", "max_hits": 2},
            timeout=30,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["hits"]) <= 2

    def test_spans_long_query_truncated(self):
        """긴 쿼리는 잘려서 처리 (200 OK)"""
        long_query = "보험" * 200  # 400자 이상
        resp = requests.get(
            f"{API_BASE}/documents/1/page/1/spans",
            params={"q": long_query},
            timeout=30,
        )

        # 서버에서 200자로 잘라서 처리
        assert resp.status_code == 200
