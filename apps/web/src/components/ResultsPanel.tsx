"use client";

/**
 * STEP 3.7-δ-β: Results Panel with Resolution State Gate
 *
 * Resolution State에 따른 렌더링 제어:
 * - RESOLVED: Results Panel 전체 활성화
 * - UNRESOLVED: Results Panel 렌더링 차단 (담보 선택 필요)
 * - INVALID: Results Panel 렌더링 차단 (재입력 필요)
 *
 * 원칙: resolution_state !== "RESOLVED"일 때 우측 패널은 비어 있어야 함
 */

import { useState, useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { CompareTable } from "./CompareTable";
import { DiffSummary } from "./DiffSummary";
import { EvidencePanel } from "./EvidencePanel";
import { SlotsTable } from "./SlotsTable";
import { SubtypeComparePanel } from "./SubtypeComparePanel";
import { CompareResponseWithSubtype, CoverageCompareItem } from "@/lib/types";
import { ChevronDown, ChevronUp, Info, AlertCircle } from "lucide-react";

interface ResultsPanelProps {
  response: CompareResponseWithSubtype | null;
}

export function ResultsPanel({ response }: ResultsPanelProps) {
  const [debugOpen, setDebugOpen] = useState(false);
  const [relatedOpen, setRelatedOpen] = useState(false);

  // STEP 2.5: 대표 담보와 연관 담보 분리
  const { primaryCoverageData, relatedCoverageData } = useMemo(() => {
    if (!response) {
      return { primaryCoverageData: [], relatedCoverageData: [] };
    }

    const primaryCode = response.primary_coverage_code;
    const relatedCodes = response.related_coverage_codes || [];
    const allData = response.coverage_compare_result || [];

    // __amount_fallback__ 제외
    const filteredData = allData.filter(
      (item) => item.coverage_code !== "__amount_fallback__"
    );

    if (!primaryCode) {
      // 대표 담보가 없으면 첫 번째를 대표로
      return {
        primaryCoverageData: filteredData.slice(0, 1),
        relatedCoverageData: filteredData.slice(1),
      };
    }

    const primary = filteredData.filter(
      (item) => item.coverage_code === primaryCode
    );
    const related = filteredData.filter(
      (item) =>
        item.coverage_code !== primaryCode &&
        (relatedCodes.length === 0 || relatedCodes.includes(item.coverage_code))
    );

    return {
      primaryCoverageData: primary,
      relatedCoverageData: related,
    };
  }, [response]);

  if (!response) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <p className="text-lg">비교 결과</p>
          <p className="text-sm mt-2">질문을 입력하면 결과가 여기에 표시됩니다</p>
        </div>
      </div>
    );
  }

  // ===========================================================================
  // STEP 3.7-δ-β: Resolution State Gate
  // resolution_state !== "RESOLVED"이면 Results Panel 렌더링 차단
  // ===========================================================================
  const resolutionState = response.resolution_state;

  // ===========================================================================
  // STEP 3.7-δ-γ3: resolution_state 직접 사용 (UNRESOLVED 우선)
  // - coverage_resolution에서 재파생 금지
  // - UNRESOLVED → "담보 선택 필요"
  // - INVALID → "담보 미확정"
  // ===========================================================================
  if (resolutionState !== "RESOLVED") {
    const isUnresolved = resolutionState === "UNRESOLVED";
    const title = isUnresolved ? "담보 선택 필요" : "담보 미확정";
    const message = isUnresolved
      ? "담보를 선택해 주세요. 선택 후 비교 결과가 표시됩니다."
      : "담보가 확정되면 비교 결과가 표시됩니다.";

    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <div className="text-center max-w-md">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
            <p className="text-lg font-medium mb-2">{title}</p>
            <p className="text-sm">{message}</p>
          </div>
        </div>
        {/* STEP 4.4: Contract Debug View (UNRESOLVED/INVALID 상태에서도 표시) */}
        <div className="border-t p-3 bg-purple-50">
          <h4 className="text-xs font-medium text-purple-800 mb-2">Contract Debug (STEP 4.4):</h4>
          <div className="text-xs text-purple-700 space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-medium">resolution_state:</span>
              <Badge variant="destructive" className="text-xs">
                {resolutionState}
              </Badge>
            </div>
            <div>
              <span className="font-medium">coverage_resolution.status:</span>{" "}
              {response.coverage_resolution?.status ?? "(null)"}
            </div>
            <div>
              <span className="font-medium">suggested_coverages.length:</span>{" "}
              {response.coverage_resolution?.suggested_coverages?.length ?? 0}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const hasPrimaryCoverage = response.primary_coverage_code && response.primary_coverage_name;
  const hasRelatedCoverages = relatedCoverageData.length > 0;

  return (
    <div className="h-full flex flex-col">
      {/* STEP 4.9-β: 대표 담보 헤더 - display name만 표시 (coverage_code 노출 금지) */}
      {hasPrimaryCoverage && (
        <div className="px-4 py-3 border-b bg-muted/30">
          <div className="flex items-center gap-2">
            <Badge variant="default" className="text-sm">
              {response.primary_coverage_name}
            </Badge>
          </div>
        </div>
      )}

      <Tabs defaultValue={response.slots && response.slots.length > 0 ? "slots" : "compare"} className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start rounded-none border-b bg-transparent p-0">
          {/* U-4.8: Slots tab (first if available) */}
          {response.slots && response.slots.length > 0 && (
            <TabsTrigger
              value="slots"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
            >
              Slots
            </TabsTrigger>
          )}
          <TabsTrigger
            value="compare"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Compare
          </TabsTrigger>
          <TabsTrigger
            value="diff"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Diff
          </TabsTrigger>
          <TabsTrigger
            value="evidence"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Evidence
          </TabsTrigger>
          <TabsTrigger
            value="policy"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Policy(약관)
          </TabsTrigger>
          {/* STEP 4.1: Subtype Comparison Tab */}
          {response.subtype_comparison?.is_multi_subtype && (
            <TabsTrigger
              value="subtype"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
            >
              Subtype
            </TabsTrigger>
          )}
        </TabsList>

        <ScrollArea className="flex-1">
          {/* U-4.8: Slots content */}
          {response.slots && response.slots.length > 0 && (
            <TabsContent value="slots" className="m-0 p-4">
              <SlotsTable slots={response.slots} />
            </TabsContent>
          )}

          <TabsContent value="compare" className="m-0 p-4 space-y-4">
            {/* STEP 2.5: 대표 담보 비교표 */}
            {primaryCoverageData.length > 0 && (
              <CompareTable data={primaryCoverageData} />
            )}

            {/* STEP 2.5: 연관 담보 (접힘 섹션) */}
            {hasRelatedCoverages && (
              <Collapsible open={relatedOpen} onOpenChange={setRelatedOpen}>
                <CollapsibleTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-between"
                  >
                    <span className="flex items-center gap-2">
                      <Info className="h-4 w-4" />
                      연관 담보 보기 ({relatedCoverageData.length})
                    </span>
                    {relatedOpen ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="pt-4">
                  <CompareTable data={relatedCoverageData} />
                </CollapsibleContent>
              </Collapsible>
            )}

            {/* 데이터가 없는 경우 */}
            {primaryCoverageData.length === 0 && !hasRelatedCoverages && (
              <CompareTable data={response.coverage_compare_result} />
            )}
          </TabsContent>

          <TabsContent value="diff" className="m-0 p-4">
            <DiffSummary data={response.diff_summary} />
          </TabsContent>

          <TabsContent value="evidence" className="m-0 p-4">
            <EvidencePanel data={response.compare_axis} isPolicyMode={false} slots={response.slots ?? undefined} />
          </TabsContent>

          <TabsContent value="policy" className="m-0 p-4">
            <EvidencePanel data={response.policy_axis} isPolicyMode={true} />
          </TabsContent>

          {/* STEP 4.1: Subtype Comparison content */}
          {response.subtype_comparison?.is_multi_subtype && (
            <TabsContent value="subtype" className="m-0 p-4">
              <SubtypeComparePanel
                comparison={response.subtype_comparison}
                insurers={
                  response.compare_axis?.map((item) => item.insurer_code).filter(
                    (v, i, a) => a.indexOf(v) === i
                  ) || []
                }
              />
            </TabsContent>
          )}
        </ScrollArea>
      </Tabs>

      {/* STEP 4.6: Debug Section - 개발자/QA 전용 (사용자 UX에서 분리) */}
      <div className="border-t">
        <Collapsible open={debugOpen} onOpenChange={setDebugOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-between rounded-none"
            >
              <span className="text-xs text-muted-foreground">🔧 Debug (개발자 전용)</span>
              {debugOpen ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronUp className="h-3 w-3" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ScrollArea className="h-[300px]">
              <div className="p-4 space-y-4">
                {/* STEP 4.6: 개발자 전용 경고 */}
                <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
                  ⚠️ 이 섹션은 개발자/QA 전용입니다. 사용자 UX 판단 기준으로 사용하지 마세요.
                </div>
                {/* STEP 4.4 + 4.6: Contract Debug View (정답 경로 표시) */}
                <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                  <h4 className="text-sm font-medium text-purple-800 mb-2">Contract Debug (정답 경로):</h4>
                  <div className="text-xs text-purple-700 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">resolution_state:</span>
                      <Badge variant={resolutionState === "RESOLVED" ? "default" : "destructive"} className="text-xs">
                        {resolutionState}
                      </Badge>
                    </div>
                    <div>
                      <span className="font-medium">coverage_resolution.status:</span>{" "}
                      {response.coverage_resolution?.status ?? "(null)"}
                    </div>
                    <div>
                      <span className="font-medium">suggested_coverages.length:</span>{" "}
                      {response.coverage_resolution?.suggested_coverages?.length ?? 0}
                    </div>
                    {(() => {
                      // STEP 4.6: 정답 경로 - debug.anchor.* 사용 (최상위 필드 참조 금지)
                      const debug = response.debug as Record<string, unknown> | undefined;
                      const anchor = debug?.anchor as {
                        coverage_locked?: boolean;
                        locked_coverage_codes?: string[];
                      } | undefined;
                      const coverageLocked = anchor?.coverage_locked;
                      const lockedCodes = anchor?.locked_coverage_codes;
                      return (
                        <>
                          <div>
                            <span className="font-medium">debug.anchor.coverage_locked:</span>{" "}
                            <span className={coverageLocked ? "text-green-700" : "text-gray-500"}>
                              {coverageLocked === true ? "true" : coverageLocked === false ? "false" : "(undefined)"}
                            </span>
                          </div>
                          {lockedCodes && lockedCodes.length > 0 && (
                            <div>
                              <span className="font-medium">debug.anchor.locked_coverage_codes:</span>{" "}
                              <span className="text-green-700">{lockedCodes.join(", ")}</span>
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                </div>
                {/* Evidence Count by Insurer */}
                {(() => {
                  const compareAxis = response.compare_axis || [];
                  const counts: Record<string, number> = {};
                  compareAxis.forEach((item) => {
                    const ic = item.insurer_code || "";
                    counts[ic] = (counts[ic] || 0) + 1;
                  });
                  const insurers = Object.keys(counts).sort();
                  const hasZero = insurers.some((ic) => counts[ic] === 0) || insurers.length < 2;

                  return (
                    <div className={`p-3 rounded-lg border ${hasZero ? "bg-orange-50 border-orange-200" : "bg-green-50 border-green-200"}`}>
                      <h4 className={`text-sm font-medium mb-2 ${hasZero ? "text-orange-800" : "text-green-800"}`}>
                        Compare Evidence Count:
                        {hasZero && (
                          <span className="ml-2 px-2 py-0.5 text-xs bg-orange-200 text-orange-800 rounded">WARN</span>
                        )}
                      </h4>
                      <div className="flex gap-4 text-sm">
                        {insurers.length > 0 ? (
                          insurers.map((ic) => (
                            <span key={ic} className={counts[ic] === 0 ? "text-orange-700 font-medium" : "text-green-700"}>
                              {ic}: {counts[ic]}
                            </span>
                          ))
                        ) : (
                          <span className="text-orange-700">No evidence found</span>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* Resolved Parameters from Debug */}
                {response.debug && (
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-800 mb-2">Resolved Parameters:</h4>
                    <div className="text-xs text-gray-700 space-y-1">
                      {(() => {
                        const debug = response.debug as Record<string, unknown>;
                        const resolvedCodes = debug.resolved_coverage_codes as string[] | undefined;
                        const recommendedCodes = debug.recommended_coverage_codes as string[] | undefined;
                        const policyKeywords = debug.resolved_policy_keywords as string[] | undefined;
                        return (
                          <>
                            {resolvedCodes && (
                              <div>
                                <span className="font-medium">coverage_codes:</span>{" "}
                                {resolvedCodes.join(", ") || "(none)"}
                              </div>
                            )}
                            {recommendedCodes && (
                              <div>
                                <span className="font-medium">recommended:</span>{" "}
                                {recommendedCodes.join(", ") || "(none)"}
                              </div>
                            )}
                            {policyKeywords && (
                              <div>
                                <span className="font-medium">policy_keywords:</span>{" "}
                                {policyKeywords.join(", ") || "(auto)"}
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* A2 Policy Status */}
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <h4 className="text-sm font-medium text-blue-800 mb-2">A2 Policy:</h4>
                  <ul className="text-xs text-blue-700 space-y-1">
                    <li>• Compare Axis: 약관 제외 (server enforced)</li>
                    <li>• Policy Axis: 약관 전용 (server enforced)</li>
                  </ul>
                </div>

                {/* Debug JSON */}
                <div>
                  <h4 className="text-xs font-medium text-muted-foreground mb-2">Raw Debug:</h4>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    {JSON.stringify(response.debug, null, 2)}
                  </pre>
                </div>
              </div>
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}
