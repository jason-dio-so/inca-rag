"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { copyToClipboard, formatEvidenceRef } from "@/lib/api";
import {
  ChevronLeft,
  ChevronRight,
  Copy,
  Check,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface PdfPageViewerProps {
  documentId: number | string;
  initialPage: number;
  docType?: string;
  highlightQuery?: string; // Step U-2.5: 하이라이트할 텍스트
  onClose: () => void;
}

interface DocumentInfo {
  document_id: number;
  page_count: number;
  source_path: string;
}

interface SpanHit {
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  score: number;
  text: string;
}

interface SpansResponse {
  document_id: number;
  page: number;
  hits: SpanHit[];
}

const SCALE_OPTIONS = [1, 2, 3] as const;
type ScaleOption = (typeof SCALE_OPTIONS)[number];

// PDF 기본 좌표계 기준 (72 DPI)
const PDF_BASE_DPI = 72;

export function PdfPageViewer({
  documentId,
  initialPage,
  docType,
  highlightQuery,
  onClose,
}: PdfPageViewerProps) {
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [scale, setScale] = useState<ScaleOption>(2);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [docInfo, setDocInfo] = useState<DocumentInfo | null>(null);

  // Highlight 관련 상태
  const [highlights, setHighlights] = useState<SpanHit[]>([]);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // 문서 정보 조회
  useEffect(() => {
    const fetchInfo = async () => {
      try {
        const resp = await fetch(`${API_BASE}/documents/${documentId}/info`);
        if (resp.ok) {
          const data = await resp.json();
          setDocInfo(data);
        }
      } catch {
        // 정보 조회 실패해도 뷰어는 동작
      }
    };
    fetchInfo();
  }, [documentId]);

  // Highlight spans 조회 (Step U-2.5)
  useEffect(() => {
    if (!highlightQuery) {
      setHighlights([]);
      return;
    }

    const fetchSpans = async () => {
      try {
        // 쿼리 앞 120자만 사용
        const query = highlightQuery.slice(0, 120);
        const params = new URLSearchParams({
          q: query,
          max_hits: "5",
        });

        const resp = await fetch(
          `${API_BASE}/documents/${documentId}/page/${currentPage}/spans?${params}`
        );

        if (resp.ok) {
          const data: SpansResponse = await resp.json();
          setHighlights(data.hits);
        } else {
          setHighlights([]);
        }
      } catch {
        // 하이라이트 실패는 조용히 무시
        setHighlights([]);
      }
    };

    // 이미지 로드 후 약간의 딜레이를 두고 하이라이트 조회
    const timer = setTimeout(fetchSpans, 100);
    return () => clearTimeout(timer);
  }, [documentId, currentPage, highlightQuery]);

  const imageUrl = `${API_BASE}/documents/${documentId}/page/${currentPage}?scale=${scale}`;

  const handleCopy = async () => {
    const ref = formatEvidenceRef(String(documentId), currentPage);
    const success = await copyToClipboard(ref);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const goToPrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage((p) => p - 1);
      setIsLoading(true);
      setError(null);
      setHighlights([]);
    }
  };

  const goToNextPage = () => {
    const maxPage = docInfo?.page_count ?? 9999;
    if (currentPage < maxPage) {
      setCurrentPage((p) => p + 1);
      setIsLoading(true);
      setError(null);
      setHighlights([]);
    }
  };

  const cycleScale = () => {
    const currentIndex = SCALE_OPTIONS.indexOf(scale);
    const nextIndex = (currentIndex + 1) % SCALE_OPTIONS.length;
    setScale(SCALE_OPTIONS[nextIndex]);
    setIsLoading(true);
  };

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    setIsLoading(false);
    setError(null);

    // 이미지 실제 크기 저장 (하이라이트 좌표 계산용)
    const img = e.currentTarget;
    setImageSize({
      width: img.naturalWidth,
      height: img.naturalHeight,
    });
  };

  const handleImageError = () => {
    setIsLoading(false);
    setError("페이지를 불러올 수 없습니다");
  };

  // ESC 키로 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowLeft") {
        goToPrevPage();
      } else if (e.key === "ArrowRight") {
        goToNextPage();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentPage, docInfo]);

  // PDF bbox를 이미지 픽셀 좌표로 변환
  const bboxToStyle = (bbox: [number, number, number, number]) => {
    if (!imageSize) return null;

    // PDF bbox는 72 DPI 기준
    // 렌더링된 이미지는 scale 배율 적용
    // imageSize는 실제 렌더링된 이미지 크기
    const [x0, y0, x1, y1] = bbox;

    // scale 배율 적용 (API에서 scale 적용된 이미지 반환)
    const left = x0 * scale;
    const top = y0 * scale;
    const width = (x1 - x0) * scale;
    const height = (y1 - y0) * scale;

    return {
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      height: `${height}px`,
    };
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex flex-col">
      {/* Header */}
      <div className="bg-background border-b px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          {/* Document Info */}
          <div className="flex items-center gap-2">
            {docType && (
              <Badge variant="secondary" className="text-xs">
                {docType}
              </Badge>
            )}
            <span className="font-mono text-sm">
              {documentId}:{currentPage}
            </span>
            {docInfo && (
              <span className="text-xs text-muted-foreground">
                / {docInfo.page_count} pages
              </span>
            )}
          </div>

          {/* Copy Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="gap-1"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 text-green-500" />
                <span className="text-xs">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                <span className="text-xs">Copy ref</span>
              </>
            )}
          </Button>

          {/* Highlight Indicator */}
          {highlights.length > 0 && (
            <Badge variant="outline" className="text-xs bg-yellow-100 text-yellow-800 border-yellow-300">
              {highlights.length}개 하이라이트
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Scale Toggle */}
          <Button
            variant="outline"
            size="sm"
            onClick={cycleScale}
            className="gap-1"
          >
            <ZoomIn className="h-4 w-4" />
            <span className="text-xs">{scale}x</span>
          </Button>

          {/* Page Navigation */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={goToPrevPage}
              disabled={currentPage <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm px-2 min-w-[60px] text-center">
              {currentPage}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={goToNextPage}
              disabled={docInfo ? currentPage >= docInfo.page_count : false}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          {/* Close Button */}
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Image Container */}
      <div className="flex-1 overflow-auto flex items-start justify-center p-4">
        {error ? (
          <div className="text-center text-destructive py-12">
            <p className="text-lg">{error}</p>
            <p className="text-sm mt-2 text-muted-foreground">
              document_id: {documentId}, page: {currentPage}
            </p>
          </div>
        ) : (
          <div className="relative inline-block">
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-muted/50 z-10">
                <Skeleton className="w-[600px] h-[800px]" />
              </div>
            )}

            {/* PDF Image */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={imgRef}
              src={imageUrl}
              alt={`Page ${currentPage}`}
              onLoad={handleImageLoad}
              onError={handleImageError}
              className={`max-w-full shadow-lg ${isLoading ? "opacity-0" : "opacity-100"} transition-opacity`}
              style={{ maxHeight: "calc(100vh - 100px)" }}
            />

            {/* Highlight Overlay (Step U-2.5) */}
            {!isLoading && highlights.length > 0 && imageSize && (
              <div className="absolute inset-0 pointer-events-none">
                {highlights.map((hit, idx) => {
                  const style = bboxToStyle(hit.bbox);
                  if (!style) return null;

                  return (
                    <div
                      key={idx}
                      className="absolute bg-yellow-300/40 border-2 border-yellow-500 rounded-sm animate-pulse"
                      style={style}
                      title={hit.text}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Hint */}
      <div className="bg-background/80 backdrop-blur border-t px-4 py-2 text-center text-xs text-muted-foreground shrink-0">
        <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px]">←</kbd>{" "}
        <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px]">→</kbd>{" "}
        페이지 이동 |{" "}
        <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px]">ESC</kbd>{" "}
        닫기
        {highlightQuery && (
          <span className="ml-2 text-yellow-600">| 하이라이트: best-effort</span>
        )}
      </div>
    </div>
  );
}
