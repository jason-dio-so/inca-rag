"use client";

/**
 * STEP 5: Evidence Summary Panel
 *
 * Evidence 탭 내부에 표시되는 비판단 요약 섹션
 *
 * 핵심 원칙:
 * - "비판단 요약(근거 기반)" 라벨 필수
 * - 원문 evidence 링크/페이지와 함께 노출
 * - 항상 원문이 우선
 */

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { evidenceSummary } from "@/lib/api";
import { EvidenceSummaryResponse, EvidenceItem } from "@/lib/types";

interface EvidenceSummaryPanelProps {
  /** Evidence 항목들 */
  evidenceItems: EvidenceItem[];
  /** 로딩 중 표시 */
  isLoading?: boolean;
}

export function EvidenceSummaryPanel({
  evidenceItems,
  isLoading = false,
}: EvidenceSummaryPanelProps) {
  const [summaryResponse, setSummaryResponse] = useState<EvidenceSummaryResponse | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Evidence가 변경되면 요약 요청
  useEffect(() => {
    if (evidenceItems.length === 0) {
      setSummaryResponse(null);
      return;
    }

    // 이미 로딩 중이면 스킵
    if (isFetching) return;

    const fetchSummary = async () => {
      setIsFetching(true);
      setFetchError(null);

      try {
        const response = await evidenceSummary({
          evidence: evidenceItems,
          task: "summarize_without_judgement",
        });

        if (response) {
          setSummaryResponse(response);
        } else {
          // soft-fail: 에러 메시지 표시
          setFetchError("요약을 불러오지 못했습니다.");
        }
      } catch (error) {
        console.warn("Evidence summary error:", error);
        setFetchError("요약 처리 중 오류가 발생했습니다.");
      } finally {
        setIsFetching(false);
      }
    };

    // 디바운스 (300ms)
    const timeoutId = setTimeout(fetchSummary, 300);
    return () => clearTimeout(timeoutId);
  }, [evidenceItems]);

  // 로딩 중
  if (isLoading || isFetching) {
    return (
      <Card className="border-amber-200 bg-amber-50/30 mb-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <span className="text-amber-700">비판단 요약</span>
            <Skeleton className="h-4 w-16" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/6" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Evidence가 없거나 요약이 없으면 렌더링 안 함
  if (evidenceItems.length === 0 || !summaryResponse) {
    return null;
  }

  // 에러 발생 시
  if (fetchError) {
    return (
      <Card className="border-gray-200 bg-gray-50/30 mb-4">
        <CardContent className="py-3">
          <div className="text-sm text-muted-foreground">{fetchError}</div>
        </CardContent>
      </Card>
    );
  }

  const { summary_bullets, limitations, assist_status } = summaryResponse;

  return (
    <Card className="border-amber-200 bg-amber-50/30 mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <span className="text-amber-700">비판단 요약 (근거 기반)</span>
          {assist_status.status === "FAILED" && (
            <Badge variant="outline" className="text-red-600 border-red-300 text-xs">
              일부 오류
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 요약 Bullets */}
        <ul className="space-y-2 text-sm">
          {summary_bullets.map((bullet, index) => (
            <li key={index} className="flex items-start gap-2">
              <span className="text-amber-600 mt-1">•</span>
              <span>{bullet}</span>
            </li>
          ))}
        </ul>

        {/* 제한 사항 */}
        {limitations.length > 0 && (
          <div className="pt-2 border-t border-amber-200">
            <div className="text-xs text-muted-foreground italic space-y-1">
              {limitations.map((limitation, index) => (
                <div key={index} className="flex items-start gap-1">
                  <span>⚠️</span>
                  <span>{limitation}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
