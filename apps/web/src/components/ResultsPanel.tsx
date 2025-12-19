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
import { CompareResponseWithSlots, CoverageCompareItem } from "@/lib/types";
import { ChevronDown, ChevronUp, Info, AlertCircle } from "lucide-react";
import { getResolutionMessage } from "@/lib/ui-gating.config";

interface ResultsPanelProps {
  response: CompareResponseWithSlots | null;
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

  if (resolutionState !== "RESOLVED") {
    const message = getResolutionMessage(response.coverage_resolution);
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
          <p className="text-lg font-medium mb-2">
            {resolutionState === "UNRESOLVED" ? "담보 선택 필요" : "담보 미확정"}
          </p>
          <p className="text-sm">{message}</p>
          {/* STEP 3.7-δ-β: resolution_state !== RESOLVED → 결과 표시 완전 차단 */}
        </div>
      </div>
    );
  }

  const hasPrimaryCoverage = response.primary_coverage_code && response.primary_coverage_name;
  const hasRelatedCoverages = relatedCoverageData.length > 0;

  return (
    <div className="h-full flex flex-col">
      {/* STEP 2.5: 대표 담보 헤더 */}
      {hasPrimaryCoverage && (
        <div className="px-4 py-3 border-b bg-muted/30">
          <div className="flex items-center gap-2">
            <Badge variant="default" className="text-sm">
              {response.primary_coverage_name}
            </Badge>
            <span className="text-xs text-muted-foreground">
              ({response.primary_coverage_code})
            </span>
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
        </ScrollArea>
      </Tabs>

      {/* Debug Section */}
      <div className="border-t">
        <Collapsible open={debugOpen} onOpenChange={setDebugOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-between rounded-none"
            >
              <span className="text-xs text-muted-foreground">Debug</span>
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
