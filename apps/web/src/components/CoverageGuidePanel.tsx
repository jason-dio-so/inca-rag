"use client";

/**
 * STEP 3.7-γ: Coverage Guide Panel
 *
 * 담보 미확정(AMBIGUOUS / NOT_FOUND) 상태에서 표시되는 상태 안내 패널
 *
 * 원칙:
 * - 이 컴포넌트는 ChatMessage가 아님
 * - 항상 단 하나만 존재 (마지막 질의 기준으로 갱신)
 * - EXACT 상태에서는 자동 제거
 */

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, HelpCircle, ChevronRight } from "lucide-react";
import {
  CoverageGuideState,
  GUIDE_MESSAGES,
} from "@/lib/conversation-hygiene.config";
import { SuggestedCoverage } from "@/lib/types";

interface CoverageGuidePanelProps {
  /** 가이드 상태 (null이면 렌더링 안함) */
  guide: CoverageGuideState | null;
  /** 담보 선택 콜백 */
  onSelectCoverage?: (coverage: SuggestedCoverage) => void;
  /** 가이드 닫기 콜백 */
  onDismiss?: () => void;
}

export function CoverageGuidePanel({
  guide,
  onSelectCoverage,
  onDismiss,
}: CoverageGuidePanelProps) {
  // 가이드가 없으면 렌더링하지 않음
  if (!guide || !guide.resolutionState) {
    return null;
  }

  const isAmbiguous = guide.resolutionState === "AMBIGUOUS";
  const isNotFound = guide.resolutionState === "NOT_FOUND";
  const messages = isAmbiguous ? GUIDE_MESSAGES.AMBIGUOUS : GUIDE_MESSAGES.NOT_FOUND;

  return (
    <Card className="mx-4 my-2 border-amber-200 bg-amber-50/50">
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2 text-amber-800">
          {isAmbiguous ? (
            <HelpCircle className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          {messages.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 pb-3 space-y-3">
        {/* 메시지 표시 */}
        <p className="text-sm text-amber-700">
          {guide.message || messages.description}
        </p>

        {/* 도메인이 감지된 경우 표시 */}
        {guide.detectedDomain && (
          <div className="text-xs text-amber-600">
            감지된 도메인: <Badge variant="outline" className="ml-1 text-xs">{guide.detectedDomain}</Badge>
          </div>
        )}

        {/* 선택 가능한 담보 목록 (AMBIGUOUS 상태) */}
        {isAmbiguous && guide.suggestedCoverages.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-amber-600">{messages.hint}</p>
            <div className="flex flex-wrap gap-2">
              {guide.suggestedCoverages.map((coverage, index) => (
                <Button
                  key={coverage.coverage_code || index}
                  variant="outline"
                  size="sm"
                  className="text-xs bg-white hover:bg-amber-100 border-amber-300"
                  onClick={() => onSelectCoverage?.(coverage)}
                >
                  <span>{coverage.coverage_name || coverage.coverage_code}</span>
                  <ChevronRight className="h-3 w-3 ml-1" />
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* NOT_FOUND 상태 힌트 */}
        {isNotFound && (
          <p className="text-xs text-amber-600">{messages.hint}</p>
        )}

        {/* 원본 쿼리 표시 (디버그용, 필요시 제거) */}
        {guide.originalQuery && (
          <div className="text-xs text-amber-500 pt-1 border-t border-amber-200">
            질의: &quot;{guide.originalQuery}&quot;
          </div>
        )}
      </CardContent>
    </Card>
  );
}
