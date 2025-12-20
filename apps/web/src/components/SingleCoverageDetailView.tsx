"use client";

/**
 * STEP 4.9: Single-Insurer Locked Coverage Detail View
 *
 * 단일 보험사 + 특정 담보 고정(locked_coverage_codes 제공) 시 전용 상세 뷰
 * 기존 비교 테이블 대신 단일 보험사에 최적화된 상세 정보 표시
 *
 * 전환 조건:
 * - insurers.length == 1
 * - debug.anchor.coverage_locked == true
 * - debug.anchor.locked_coverage_codes.length >= 1
 *
 * 정답 데이터 소스:
 * - 축: debug.anchor.locked_coverage_codes[0]
 * - 결과: coverage_compare_result
 * - 근거: compare_axis (evidence refs)
 * - 슬롯: slots (payout_amount 등)
 * - fallback 정보: debug.retrieval.*
 */

import { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { EvidencePanel } from "./EvidencePanel";
import { SlotsTable } from "./SlotsTable";
import { CompareResponseWithSubtype } from "@/lib/types";
import { ChevronDown, ChevronUp, FileText, Info, Unlock, AlertTriangle, DollarSign } from "lucide-react";

interface SingleCoverageDetailViewProps {
  response: CompareResponseWithSubtype;
  insurerCode: string;
  coverageCode: string;
  coverageName?: string | null;
  onUnlock: () => void;
}

export function SingleCoverageDetailView({
  response,
  insurerCode,
  coverageCode,
  coverageName,
  onUnlock,
}: SingleCoverageDetailViewProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(true);
  const [debugOpen, setDebugOpen] = useState(false);

  // 보험사명 매핑 (간단한 버전)
  const insurerNames: Record<string, string> = {
    SAMSUNG: "삼성화재",
    MERITZ: "메리츠화재",
    LOTTE: "롯데손해보험",
    KB: "KB손해보험",
    DB: "DB손해보험",
    HANWHA: "한화손해보험",
    HEUNGKUK: "흥국화재",
    HYUNDAI: "현대해상",
  };

  // debug 정보 추출 (정답 경로)
  const debug = response.debug as Record<string, unknown> | undefined;
  const anchor = debug?.anchor as {
    coverage_locked?: boolean;
    locked_coverage_codes?: string[];
  } | undefined;
  const retrieval = debug?.retrieval as {
    fallback_used?: boolean;
    fallback_reason?: string;
    fallback_source?: string;
    effective_locked_code?: string;
  } | undefined;

  // coverage_compare_result에서 해당 insurer의 데이터 추출
  const coverageResult = response.coverage_compare_result?.find(
    (item) => item.coverage_code === coverageCode
  );
  const insurerCell = coverageResult?.insurers?.find(
    (cell) => cell.insurer_code === insurerCode
  );

  // slots 중 해당 insurer 관련 값 추출
  const slots = response.slots || [];

  // compare_axis에서 해당 insurer의 evidence 추출
  const evidenceItems = response.compare_axis?.filter(
    (item) => item.insurer_code === insurerCode
  ) || [];

  // STEP 4.9: best_evidence 기반 금액 정보 추출 (resolved_amount 생성 금지)
  // 우선순위: best_evidence[0].amount > best_evidence[0].amount (amount_text) > 없음
  const bestEvidence = insurerCell?.best_evidence || [];
  const firstEvidenceWithAmount = bestEvidence.find((ev) => ev.amount?.amount_value);
  const amountInfo = firstEvidenceWithAmount?.amount;

  return (
    <div className="h-full flex flex-col">
      {/* 헤더 */}
      <div className="px-4 py-4 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-sm font-medium">
                {insurerNames[insurerCode] || insurerCode}
              </Badge>
              <span className="text-xs text-muted-foreground">단일 보험사 조회</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-blue-900">
                {coverageName || coverageCode}
              </span>
              <Badge variant="secondary" className="text-xs">
                {coverageCode}
              </Badge>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onUnlock}
            className="gap-1"
          >
            <Unlock className="h-4 w-4" />
            담보 변경
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* 핵심 결과 카드 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Info className="h-4 w-4" />
                담보 정보
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* STEP 4.9: best_evidence 기반 금액 정보 표시 (resolved_amount 생성 금지) */}
              {amountInfo?.amount_value ? (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-baseline gap-2">
                    <DollarSign className="h-5 w-5 text-green-600" />
                    <span className="text-2xl font-bold text-green-700">
                      {amountInfo.amount_text || `${amountInfo.amount_value.toLocaleString()}${amountInfo.unit || "원"}`}
                    </span>
                    <Badge
                      variant={
                        amountInfo.confidence === "high"
                          ? "default"
                          : amountInfo.confidence === "medium"
                          ? "secondary"
                          : "outline"
                      }
                      className="text-xs"
                    >
                      {amountInfo.confidence}
                    </Badge>
                  </div>
                  {firstEvidenceWithAmount?.doc_type && (
                    <p className="text-xs text-green-600 mt-1">
                      출처: {firstEvidenceWithAmount.doc_type}
                      {firstEvidenceWithAmount.page_start && ` (p.${firstEvidenceWithAmount.page_start})`}
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-center gap-2 text-amber-700">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="text-sm font-medium">금액 정보 없음</span>
                  </div>
                  <p className="text-xs text-amber-600 mt-1">
                    근거 문서에서 직접 확인해 주세요.
                  </p>
                </div>
              )}

              {/* Slots 기반 요약 */}
              {slots.length > 0 && (
                <div className="pt-2">
                  <h4 className="text-xs font-medium text-muted-foreground mb-2">
                    슬롯 정보
                  </h4>
                  <SlotsTable
                    slots={slots}
                    singleInsurer={insurerCode}
                  />
                </div>
              )}

              {/* 슬롯 없을 때 안내 */}
              {slots.length === 0 && !amountInfo?.amount_value && (
                <p className="text-xs text-muted-foreground">
                  추출된 슬롯 정보가 없습니다. 아래 근거 자료를 참고해 주세요.
                </p>
              )}
            </CardContent>
          </Card>

          {/* 근거 섹션 */}
          <Collapsible open={evidenceOpen} onOpenChange={setEvidenceOpen}>
            <Card>
              <CardHeader className="pb-2">
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    className="w-full justify-between p-0 h-auto hover:bg-transparent"
                  >
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      근거 자료 ({evidenceItems.length}건)
                    </CardTitle>
                    {evidenceOpen ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </Button>
                </CollapsibleTrigger>
              </CardHeader>
              <CollapsibleContent>
                <CardContent>
                  {evidenceItems.length > 0 ? (
                    <EvidencePanel
                      data={evidenceItems}
                      isPolicyMode={false}
                      slots={slots.length > 0 ? slots : undefined}
                    />
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      해당 담보에 대한 근거 자료가 없습니다.
                    </p>
                  )}
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>

          {/* Fallback 알림 (fallback 발생 시에만 표시) */}
          {retrieval?.fallback_used && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-2 text-blue-700">
                <Info className="h-4 w-4" />
                <span className="text-xs font-medium">
                  해당 담보 코드로 직접 태깅된 자료가 없어 유사 자료를 검색했습니다.
                </span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Debug 섹션 (개발자/QA 전용) */}
      <div className="border-t">
        <Collapsible open={debugOpen} onOpenChange={setDebugOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-between rounded-none"
            >
              <span className="text-xs text-muted-foreground">
                Debug (개발자 전용)
              </span>
              {debugOpen ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronUp className="h-3 w-3" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ScrollArea className="h-[200px]">
              <div className="p-4 space-y-3">
                <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
                  이 섹션은 개발자/QA 전용입니다. 사용자 UX 판단 기준으로 사용하지 마세요.
                </div>

                {/* Contract Debug */}
                <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                  <h4 className="text-xs font-medium text-purple-800 mb-2">
                    Contract (정답 경로):
                  </h4>
                  <div className="text-xs text-purple-700 space-y-1">
                    <div>
                      <span className="font-medium">debug.anchor.coverage_locked:</span>{" "}
                      <span className="text-green-700">
                        {anchor?.coverage_locked ? "true" : "false"}
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">debug.anchor.locked_coverage_codes:</span>{" "}
                      {anchor?.locked_coverage_codes?.join(", ") || "(none)"}
                    </div>
                    <div>
                      <span className="font-medium">coverage_compare_result[0].coverage_code:</span>{" "}
                      {coverageResult?.coverage_code || "(none)"}
                    </div>
                  </div>
                </div>

                {/* Fallback Debug */}
                {retrieval && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="text-xs font-medium text-blue-800 mb-2">
                      Retrieval Fallback:
                    </h4>
                    <div className="text-xs text-blue-700 space-y-1">
                      <div>
                        <span className="font-medium">fallback_used:</span>{" "}
                        {retrieval.fallback_used ? "true" : "false"}
                      </div>
                      {retrieval.fallback_used && (
                        <>
                          <div>
                            <span className="font-medium">fallback_reason:</span>{" "}
                            {retrieval.fallback_reason}
                          </div>
                          <div>
                            <span className="font-medium">fallback_source:</span>{" "}
                            {retrieval.fallback_source}
                          </div>
                          <div>
                            <span className="font-medium">effective_locked_code:</span>{" "}
                            {retrieval.effective_locked_code}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}

// =============================================================================
// UI 모드 결정 함수
// =============================================================================

export type UIMode = "SINGLE_DETAIL" | "COMPARE" | "GUIDE";

/**
 * UI 모드 결정 함수
 *
 * 정답 경로:
 * - Lock 판단: debug.anchor.coverage_locked, debug.anchor.locked_coverage_codes
 * - 후보 추천: coverage_resolution.suggested_coverages
 *
 * @param selectedInsurers UI에서 선택된 보험사 리스트
 * @param response API 응답
 * @returns UI 모드
 */
export function determineUIMode(
  selectedInsurers: string[],
  response: CompareResponseWithSubtype | null
): UIMode {
  if (!response) {
    return "COMPARE";
  }

  // 정답 경로: debug.anchor.* (최상위 필드 참조 금지)
  const debug = response.debug as Record<string, unknown> | undefined;
  const anchor = debug?.anchor as {
    coverage_locked?: boolean;
    locked_coverage_codes?: string[];
  } | undefined;

  const coverageLocked = anchor?.coverage_locked === true;
  const lockedCodes = anchor?.locked_coverage_codes || [];

  // 조건 1: 단일 insurer + locked → SINGLE_DETAIL
  if (
    selectedInsurers.length === 1 &&
    coverageLocked &&
    lockedCodes.length >= 1
  ) {
    return "SINGLE_DETAIL";
  }

  // 조건 2: UNRESOLVED + 후보 존재 → GUIDE
  if (
    response.resolution_state === "UNRESOLVED" &&
    (response.coverage_resolution?.suggested_coverages?.length ?? 0) > 0
  ) {
    return "GUIDE";
  }

  // 기본: COMPARE
  return "COMPARE";
}
