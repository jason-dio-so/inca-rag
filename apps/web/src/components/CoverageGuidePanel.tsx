"use client";

/**
 * STEP 3.7-γ: Coverage Guide Panel
 * STEP 3.7-δ-β: State names updated (UNRESOLVED / INVALID)
 * STEP 4.5-β: Multi-select support for multi-subtype comparison
 *
 * 담보 미확정(UNRESOLVED / INVALID) 상태에서 표시되는 상태 안내 패널
 *
 * 원칙:
 * - 이 컴포넌트는 ChatMessage가 아님
 * - 항상 단 하나만 존재 (마지막 질의 기준으로 갱신)
 * - RESOLVED 상태에서는 자동 제거
 * - STEP 4.5-β: 복수 담보 선택 가능 (체크박스 + 적용 버튼)
 */

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, HelpCircle, ChevronRight, Check } from "lucide-react";
import {
  CoverageGuideState,
  GUIDE_MESSAGES,
} from "@/lib/conversation-hygiene.config";
import { SuggestedCoverage } from "@/lib/types";

interface CoverageGuidePanelProps {
  /** 가이드 상태 (null이면 렌더링 안함) */
  guide: CoverageGuideState | null;
  /** 단일 담보 선택 콜백 (기존 호환) */
  onSelectCoverage?: (coverage: SuggestedCoverage) => void;
  /** STEP 4.5-β: 복수 담보 선택 콜백 */
  onSelectCoverages?: (coverages: SuggestedCoverage[]) => void;
  /** 가이드 닫기 콜백 */
  onDismiss?: () => void;
}

export function CoverageGuidePanel({
  guide,
  onSelectCoverage,
  onSelectCoverages,
  onDismiss,
}: CoverageGuidePanelProps) {
  // STEP 4.5-β: 복수 선택 상태 관리
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set());

  // 체크박스 토글
  const toggleCoverage = useCallback((code: string) => {
    setSelectedCodes(prev => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  }, []);

  // 선택된 담보들로 비교 실행
  const handleApplySelection = useCallback(() => {
    if (!guide || selectedCodes.size === 0) return;

    const selectedCoverages = guide.suggestedCoverages.filter(
      c => selectedCodes.has(c.coverage_code)
    );

    if (selectedCoverages.length === 1 && onSelectCoverage) {
      // 단일 선택: 기존 콜백 사용
      onSelectCoverage(selectedCoverages[0]);
    } else if (selectedCoverages.length >= 1 && onSelectCoverages) {
      // 복수 선택: 새 콜백 사용
      onSelectCoverages(selectedCoverages);
    } else if (selectedCoverages.length === 1 && onSelectCoverage) {
      // fallback
      onSelectCoverage(selectedCoverages[0]);
    }
  }, [guide, selectedCodes, onSelectCoverage, onSelectCoverages]);

  // 가이드가 없으면 렌더링하지 않음
  if (!guide || !guide.resolutionState) {
    return null;
  }

  const isUnresolved = guide.resolutionState === "UNRESOLVED";
  const isInvalid = guide.resolutionState === "INVALID";
  const messages = isUnresolved ? GUIDE_MESSAGES.UNRESOLVED : GUIDE_MESSAGES.INVALID;
  const hasMultipleCandidates = guide.suggestedCoverages.length > 1;

  return (
    <Card className="mx-4 my-2 border-amber-200 bg-amber-50/50">
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2 text-amber-800">
          {isUnresolved ? (
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

        {/* 선택 가능한 담보 목록 (UNRESOLVED 상태) */}
        {isUnresolved && guide.suggestedCoverages.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-amber-600">
              {hasMultipleCandidates
                ? "비교할 담보를 선택하세요 (복수 선택 가능):"
                : messages.hint}
            </p>

            {/* STEP 4.5-β: 복수 선택 가능한 체크박스 목록 */}
            <div className="space-y-1.5">
              {guide.suggestedCoverages.map((coverage, index) => {
                const code = coverage.coverage_code;
                const label = coverage.coverage_name ||
                  (coverage as unknown as Record<string, string>).coverage_name_ko ||
                  code;
                const isChecked = selectedCodes.has(code);

                return (
                  <label
                    key={code || index}
                    className={`flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors ${
                      isChecked
                        ? "bg-amber-100 border border-amber-300"
                        : "bg-white border border-amber-200 hover:bg-amber-50"
                    }`}
                  >
                    <Checkbox
                      checked={isChecked}
                      onCheckedChange={() => toggleCoverage(code)}
                      className="border-amber-400 data-[state=checked]:bg-amber-500"
                    />
                    <span className="text-sm text-amber-800 flex-1">{label}</span>
                    {coverage.similarity && (
                      <Badge variant="outline" className="text-xs text-amber-600">
                        {(coverage.similarity * 100).toFixed(0)}%
                      </Badge>
                    )}
                  </label>
                );
              })}
            </div>

            {/* 적용 버튼 */}
            <Button
              onClick={handleApplySelection}
              disabled={selectedCodes.size === 0}
              className="w-full mt-2 bg-amber-500 hover:bg-amber-600 text-white"
              size="sm"
            >
              <Check className="h-4 w-4 mr-1" />
              {selectedCodes.size === 0
                ? "담보를 선택하세요"
                : selectedCodes.size === 1
                  ? "선택한 담보로 비교"
                  : `${selectedCodes.size}개 담보로 비교`}
            </Button>
          </div>
        )}

        {/* INVALID 상태 힌트 */}
        {isInvalid && (
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
