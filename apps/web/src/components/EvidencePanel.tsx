"use client";

/**
 * STEP 3.8: Evidence Panel with View State Isolation
 * STEP 4.0: Evidence Priority Ordering (P1/P2/P3)
 * STEP 5: Evidence Summary Integration (비판단 요약)
 *
 * Evidence/Policy 상세보기는 ViewContext를 통해 처리되며,
 * Query State(messages, currentResponse, anchor)에 영향을 주지 않습니다.
 *
 * 핵심 원칙:
 * - Evidence 클릭 = Read-only View Event
 * - Query State 변경 없음
 * - View State만 업데이트
 * - STEP 4.0: P1(결정근거) → P2(해석근거) → P3(보조근거) 순서 정렬
 * - STEP 5: Evidence Summary는 비판단 요약만 제공
 */

import { useState, useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { CompareAxisItem, PolicyAxisItem, Evidence, ComparisonSlot, SlotEvidenceRef, EvidenceItem } from "@/lib/types";
import { copyToClipboard, formatEvidenceRef } from "@/lib/api";
import { Copy, Check, Eye, ChevronDown, Star, FileText } from "lucide-react";
import { useViewContext } from "@/contexts/ViewContext";
import {
  determineEvidencePriority,
  sortEvidenceByPriority,
  PRIORITY_DEFINITIONS,
  PRIORITY_STYLES,
  EvidencePriority,
} from "@/lib/evidence-priority.config";
import { EvidenceSummaryPanel } from "./EvidenceSummaryPanel";

const INSURER_NAMES: Record<string, string> = {
  SAMSUNG: "삼성",
  LOTTE: "롯데",
  DB: "DB",
  KB: "KB",
  MERITZ: "메리츠",
  HANWHA: "한화",
  HYUNDAI: "현대",
  HEUNGKUK: "흥국",
};

const DOC_TYPE_COLORS: Record<string, string> = {
  가입설계서: "bg-green-100 text-green-800",
  상품요약서: "bg-blue-100 text-blue-800",
  사업방법서: "bg-purple-100 text-purple-800",
  약관: "bg-orange-100 text-orange-800",
};

interface EvidencePanelProps {
  data: CompareAxisItem[] | PolicyAxisItem[];
  isPolicyMode?: boolean; // true = Policy tab (약관만), false = Evidence tab (약관 제외)
  slots?: ComparisonSlot[]; // U-4.9: slots for identifying 대표 근거
}

/**
 * Build a Set of "representative evidence" keys from slots.evidence_refs
 * Key format: `${document_id}-${page_start}`
 */
function buildRepresentativeEvidenceSet(slots: ComparisonSlot[] | undefined, insurerCode: string): Set<string> {
  const repSet = new Set<string>();
  if (!slots) return repSet;

  for (const slot of slots) {
    for (const iv of slot.insurers) {
      if (iv.insurer_code === insurerCode && iv.evidence_refs) {
        for (const ref of iv.evidence_refs) {
          repSet.add(`${ref.document_id}-${ref.page_start ?? 0}`);
        }
      }
    }
  }
  return repSet;
}

export function EvidencePanel({ data, isPolicyMode = false, slots }: EvidencePanelProps) {
  const [copiedRef, setCopiedRef] = useState<string | null>(null);
  const [additionalOpen, setAdditionalOpen] = useState<Record<string, boolean>>({});

  // STEP 3.8: ViewContext를 통한 문서 열기 (Query State 변경 없음)
  const { openDocument } = useViewContext();

  if (!data || data.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        {isPolicyMode ? "약관 근거가 없습니다" : "근거 자료가 없습니다"}
      </div>
    );
  }

  // Group by insurer
  const groupedByInsurer = new Map<string, Evidence[]>();

  data.forEach((item) => {
    const insurer = item.insurer_code;
    let evidence = item.evidence || [];

    // NOTE:
    // This filter is defensive.
    // A2 policy is enforced by the server.
    // UI filtering is only for display safety.
    // A2 Policy filtering
    if (isPolicyMode) {
      // Policy tab: only show 약관
      evidence = evidence.filter((e) => e.doc_type === "약관");
    } else {
      // Evidence tab: exclude 약관
      evidence = evidence.filter((e) => e.doc_type !== "약관");
    }

    if (evidence.length > 0) {
      const existing = groupedByInsurer.get(insurer) || [];
      groupedByInsurer.set(insurer, [...existing, ...evidence]);
    }
  });

  const insurerList = Array.from(groupedByInsurer.keys()).sort();

  if (insurerList.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        {isPolicyMode ? "약관 근거가 없습니다" : "근거 자료가 없습니다"}
      </div>
    );
  }

  // STEP 5: Evidence Summary를 위한 데이터 준비
  // 대표 근거들을 EvidenceItem 형식으로 변환
  const evidenceItemsForSummary: EvidenceItem[] = useMemo(() => {
    const items: EvidenceItem[] = [];

    insurerList.forEach((insurer) => {
      const allEvidence = groupedByInsurer.get(insurer) || [];
      const repSet = buildRepresentativeEvidenceSet(slots, insurer);

      // 대표 근거만 요약에 포함 (없으면 처음 2개)
      const representativeEvidence = allEvidence.filter((ev) => {
        const key = `${ev.document_id}-${ev.page_start ?? 0}`;
        return repSet.has(key);
      });

      const evidenceToSummarize = representativeEvidence.length > 0
        ? representativeEvidence.slice(0, 3)
        : allEvidence.slice(0, 2);

      evidenceToSummarize.forEach((ev) => {
        items.push({
          insurer_code: insurer,
          doc_type: ev.doc_type,
          page: ev.page_start ?? undefined,
          excerpt: ev.preview?.slice(0, 500) || "",
        });
      });
    });

    return items;
  }, [insurerList, groupedByInsurer, slots]);

  const handleCopy = async (evidence: Evidence) => {
    const ref = formatEvidenceRef(evidence.document_id, evidence.page_start);
    const success = await copyToClipboard(ref);
    if (success) {
      setCopiedRef(ref);
      setTimeout(() => setCopiedRef(null), 2000);
    }
  };

  /**
   * STEP 3.8: Evidence View 클릭 핸들러
   * - ViewContext.openDocument()를 통해 View State만 변경
   * - Query State(messages, currentResponse, anchor) 변경 없음
   * - 좌측 요약 영역 불변 보장
   */
  const handleView = useCallback((evidence: Evidence) => {
    openDocument({
      documentId: evidence.document_id,
      page: evidence.page_start ?? 1,
      docType: evidence.doc_type,
      highlightQuery: evidence.preview?.slice(0, 120) || undefined,
    });
  }, [openDocument]);

  const toggleAdditional = (insurer: string) => {
    setAdditionalOpen(prev => ({ ...prev, [insurer]: !prev[insurer] }));
  };

  return (
    <div className="space-y-2">
      {/* STEP 3.8: PdfPageViewer는 이제 DocumentViewerLayer (page.tsx)에서 관리됨 */}
      {/* ViewContext.openDocument()를 통해 View State만 변경하고, Query State는 불변 */}

      {/* STEP 5: Evidence Summary Panel (비판단 요약) */}
      {!isPolicyMode && evidenceItemsForSummary.length > 0 && (
        <EvidenceSummaryPanel
          evidenceItems={evidenceItemsForSummary}
          isLoading={false}
        />
      )}

      {/* U-4.9: Evidence Tab Clarification Notice */}
      {!isPolicyMode && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-2">
            <FileText className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
            <div className="text-sm text-blue-800 space-y-1">
              <p>※ Evidence는 비교 계산에 사용된 &apos;대표 근거&apos;가 아니라,</p>
              <p className="ml-3">관련 문서에서 발견된 전체 근거 목록입니다.</p>
            </div>
          </div>
        </div>
      )}

      {isPolicyMode && (
        <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
          <div className="flex items-start gap-2">
            <Badge className="bg-orange-100 text-orange-800 shrink-0">약관</Badge>
            <div className="text-sm text-orange-800 space-y-1">
              <p>※ 약관은 비교 계산에 사용되지 않으며,</p>
              <p className="ml-3">정책/정의 근거 확인용으로만 제공됩니다.</p>
            </div>
          </div>
        </div>
      )}

      <Accordion type="multiple" defaultValue={insurerList} className="w-full">
        {insurerList.map((insurer) => {
          const allEvidence = groupedByInsurer.get(insurer) || [];

          // U-4.9: Split into representative and additional evidence
          const repSet = buildRepresentativeEvidenceSet(slots, insurer);
          const representativeEvidence: Evidence[] = [];
          const additionalEvidence: Evidence[] = [];

          allEvidence.forEach((ev) => {
            const key = `${ev.document_id}-${ev.page_start ?? 0}`;
            if (repSet.has(key)) {
              representativeEvidence.push(ev);
            } else {
              additionalEvidence.push(ev);
            }
          });

          const repCount = representativeEvidence.length;
          const totalCount = allEvidence.length;

          return (
            <AccordionItem key={insurer} value={insurer}>
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-2">
                  <span className="font-medium">
                    {INSURER_NAMES[insurer] || insurer}
                  </span>
                  {/* U-4.9: Show "대표 N / 전체 M" instead of raw count */}
                  <Badge variant="secondary" className="font-normal">
                    {slots && repCount > 0 ? (
                      <span>대표 {repCount} / 전체 {totalCount}</span>
                    ) : (
                      <span>{totalCount}건</span>
                    )}
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-4 pt-2">
                  {/* U-4.9: Section 1 - 비교에 사용된 대표 근거 */}
                  {/* STEP 4.0: Sort by priority within section */}
                  {slots && representativeEvidence.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm font-medium text-amber-700">
                        <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                        비교에 사용된 대표 근거
                      </div>
                      <div className="space-y-2">
                        {sortEvidenceByPriority(representativeEvidence).map((ev, idx) => (
                          <EvidenceCard
                            key={`rep-${ev.document_id}-${ev.page_start}-${idx}`}
                            evidence={ev}
                            onCopy={handleCopy}
                            onView={handleView}
                            copiedRef={copiedRef}
                            isRepresentative={true}
                            showPriority={true}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* U-4.9: Section 2 - 추가 참고 근거 (collapsible) */}
                  {additionalEvidence.length > 0 && (
                    <Collapsible
                      open={additionalOpen[insurer] ?? false}
                      onOpenChange={() => toggleAdditional(insurer)}
                    >
                      <CollapsibleTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-full justify-between text-muted-foreground hover:text-foreground"
                        >
                          <span className="flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            추가 참고 근거 ({additionalEvidence.length}건)
                          </span>
                          <ChevronDown
                            className={`h-4 w-4 transition-transform ${
                              additionalOpen[insurer] ? "rotate-180" : ""
                            }`}
                          />
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        {/* STEP 4.0: Sort by priority within section */}
                        <div className="space-y-2 pt-2">
                          {sortEvidenceByPriority(additionalEvidence).map((ev, idx) => (
                            <EvidenceCard
                              key={`add-${ev.document_id}-${ev.page_start}-${idx}`}
                              evidence={ev}
                              onCopy={handleCopy}
                              onView={handleView}
                              copiedRef={copiedRef}
                              isRepresentative={false}
                              showPriority={true}
                            />
                          ))}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  )}

                  {/* Fallback: No slots, show all evidence normally */}
                  {/* STEP 4.0: Sort by priority */}
                  {!slots && sortEvidenceByPriority(allEvidence).map((ev, idx) => (
                    <EvidenceCard
                      key={`${ev.document_id}-${ev.page_start}-${idx}`}
                      evidence={ev}
                      onCopy={handleCopy}
                      onView={handleView}
                      copiedRef={copiedRef}
                      showPriority={true}
                    />
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}

interface EvidenceCardProps {
  evidence: Evidence;
  onCopy: (evidence: Evidence) => void;
  onView: (evidence: Evidence) => void;
  copiedRef: string | null;
  isRepresentative?: boolean; // U-4.9: true = 대표 근거, false = 참고 근거
  showPriority?: boolean; // STEP 4.0: show P1/P2/P3 priority badge
}

function EvidenceCard({
  evidence,
  onCopy,
  onView,
  copiedRef,
  isRepresentative,
  showPriority = false,
}: EvidenceCardProps) {
  const ref = formatEvidenceRef(evidence.document_id, evidence.page_start);
  const isCopied = copiedRef === ref;

  // STEP 4.0: Determine priority
  const priority = useMemo(() => determineEvidencePriority(evidence), [evidence]);
  const priorityDef = PRIORITY_DEFINITIONS[priority];
  const priorityStyle = PRIORITY_STYLES[priority];

  return (
    <Card className={isRepresentative ? "border-amber-300 bg-amber-50/30" : ""}>
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 space-y-1">
            {/* Doc Type Badge + Representative Badge + Priority Badge */}
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                className={
                  DOC_TYPE_COLORS[evidence.doc_type] ||
                  "bg-gray-100 text-gray-800"
                }
              >
                {evidence.doc_type}
              </Badge>
              {/* STEP 4.0: Priority badge */}
              {showPriority && (
                <Badge
                  variant="outline"
                  className={`${priorityStyle.bgColor} ${priorityStyle.textColor} ${priorityStyle.borderColor}`}
                >
                  <span className="flex items-center gap-1">
                    {/* Stars based on priority */}
                    {Array.from({ length: priorityDef.stars }).map((_, i) => (
                      <Star key={i} className="h-2.5 w-2.5 fill-current" />
                    ))}
                    <span className="ml-0.5">{priorityDef.name}</span>
                  </span>
                </Badge>
              )}
              {/* U-4.9: 대표/참고 근거 badge */}
              {isRepresentative !== undefined && (
                <Badge
                  variant={isRepresentative ? "default" : "outline"}
                  className={
                    isRepresentative
                      ? "bg-amber-500 hover:bg-amber-500 text-white"
                      : "text-muted-foreground"
                  }
                >
                  {isRepresentative ? (
                    <span className="flex items-center gap-1">
                      <Star className="h-3 w-3 fill-current" />
                      대표 근거
                    </span>
                  ) : (
                    "참고 근거"
                  )}
                </Badge>
              )}
              {evidence.score !== undefined && (
                <span className="text-xs text-muted-foreground">
                  score: {evidence.score.toFixed(2)}
                </span>
              )}
            </div>

            {/* Page Range */}
            <div className="text-sm text-muted-foreground">
              <span className="font-mono">
                {String(evidence.document_id).slice(0, 12)}
              </span>
              <span className="mx-1">|</span>
              <span>
                p.{evidence.page_start ?? 0}
              </span>
            </div>

            {/* Preview Text */}
            {evidence.preview && (
              <p className="text-sm mt-2 p-2 bg-muted rounded line-clamp-3">
                {evidence.preview}
              </p>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-1 shrink-0">
            {/* View Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onView(evidence)}
              title="View page"
            >
              <Eye className="h-4 w-4" />
            </Button>

            {/* Copy Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onCopy(evidence)}
              title="Copy ref"
            >
              {isCopied ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
