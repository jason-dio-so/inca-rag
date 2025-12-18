"""
Insurance Comparison RAG API

Main FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.compare import router as compare_router
from api.document_viewer import router as document_viewer_router

app = FastAPI(
    title="Insurance Comparison RAG API",
    description="보험 약관 비교 RAG 시스템 API",
    version="0.1.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(compare_router)
app.include_router(document_viewer_router)


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """API 정보"""
    return {
        "name": "Insurance Comparison RAG API",
        "version": "0.1.0",
        "endpoints": [
            {"path": "/compare", "method": "POST", "description": "2-Phase Retrieval 비교 검색"},
            {"path": "/documents/{id}/page/{page}", "method": "GET", "description": "PDF 페이지 이미지"},
            {"path": "/documents/{id}/info", "method": "GET", "description": "문서 정보 조회"},
            {"path": "/health", "method": "GET", "description": "헬스 체크"},
        ],
    }
