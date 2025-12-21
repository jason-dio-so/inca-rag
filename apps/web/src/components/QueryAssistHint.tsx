"use client";

/**
 * STEP 5: Query Assist Hint Card
 *
 * 질의 입력 후 힌트 카드 표시
 *
 * 핵심 원칙:
 * - Apply 버튼을 눌러야만 query에 반영
 * - 자동 적용 금지
 * - Ignore 버튼으로 무시 가능
 */

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { QueryAssistResponse } from "@/lib/types";

interface QueryAssistHintProps {
  /** Assist 응답 */
  assistResponse: QueryAssistResponse;
  /** 원본 질의 */
  originalQuery: string;
  /** Apply 클릭 시 (정규화된 질의로 검색) */
  onApply: (normalizedQuery: string, keywords: string[]) => void;
  /** Ignore 클릭 시 (원본 질의로 검색) */
  onIgnore: () => void;
  /** 로딩 상태 */
  isLoading?: boolean;
}

export function QueryAssistHint({
  assistResponse,
  originalQuery,
  onApply,
  onIgnore,
  isLoading = false,
}: QueryAssistHintProps) {
  // 정규화된 질의가 원본과 동일하면 힌트 불필요
  const hasNormalization =
    assistResponse.normalized_query.trim().toLowerCase() !==
    originalQuery.trim().toLowerCase();

  // 힌트가 없으면 렌더링 안 함
  const hasHints =
    hasNormalization ||
    assistResponse.detected_subtypes.length > 0 ||
    assistResponse.keywords.length > 0;

  if (!hasHints) {
    return null;
  }

  const handleApply = useCallback(() => {
    onApply(assistResponse.normalized_query, assistResponse.keywords);
  }, [assistResponse.normalized_query, assistResponse.keywords, onApply]);

  return (
    <Card className="border-blue-200 bg-blue-50/50 mb-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <span className="text-blue-600">AI 힌트</span>
          {assistResponse.assist_status.status === "FAILED" && (
            <Badge variant="outline" className="text-amber-600 border-amber-300">
              제한적 힌트
            </Badge>
          )}
          <span className="text-xs text-muted-foreground ml-auto">
            (자동 적용되지 않음)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* 정규화된 질의 */}
        {hasNormalization && (
          <div>
            <div className="text-xs text-muted-foreground mb-1">정규화된 질의</div>
            <div className="text-sm bg-white rounded px-2 py-1 border">
              {assistResponse.normalized_query}
            </div>
          </div>
        )}

        {/* 감지된 Subtype */}
        {assistResponse.detected_subtypes.length > 0 && (
          <div>
            <div className="text-xs text-muted-foreground mb-1">감지된 유형</div>
            <div className="flex flex-wrap gap-1">
              {assistResponse.detected_subtypes.map((subtype) => (
                <Badge key={subtype} variant="secondary" className="text-xs">
                  {subtype === "CIS_CARCINOMA" && "제자리암"}
                  {subtype === "BORDERLINE_TUMOR" && "경계성종양"}
                  {subtype === "SIMILAR_CANCER" && "유사암"}
                  {subtype === "THYROID_CANCER" && "갑상선암"}
                  {subtype === "MINOR_CANCER" && "소액암"}
                  {subtype === "SKIN_CANCER" && "기타피부암"}
                  {!["CIS_CARCINOMA", "BORDERLINE_TUMOR", "SIMILAR_CANCER", "THYROID_CANCER", "MINOR_CANCER", "SKIN_CANCER"].includes(subtype) && subtype}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* 추출된 키워드 */}
        {assistResponse.keywords.length > 0 && (
          <div>
            <div className="text-xs text-muted-foreground mb-1">키워드</div>
            <div className="flex flex-wrap gap-1">
              {assistResponse.keywords.map((keyword) => (
                <Badge key={keyword} variant="outline" className="text-xs">
                  {keyword}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* 감지된 Intent */}
        {assistResponse.detected_intents.length > 0 && (
          <div className="text-xs text-muted-foreground">
            의도:{" "}
            {assistResponse.detected_intents.map((intent) => (
              <span key={intent} className="mr-2">
                {intent === "compare" && "비교"}
                {intent === "lookup" && "조회"}
                {intent === "coverage_lookup" && "담보 조회"}
              </span>
            ))}
          </div>
        )}

        {/* 액션 버튼 */}
        <div className="flex gap-2 pt-2">
          <Button
            size="sm"
            onClick={handleApply}
            disabled={isLoading}
            className="flex-1"
          >
            적용
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onIgnore}
            disabled={isLoading}
          >
            무시
          </Button>
        </div>

        {/* 주의사항 */}
        <div className="text-xs text-muted-foreground italic">
          {assistResponse.notes}
        </div>
      </CardContent>
    </Card>
  );
}
