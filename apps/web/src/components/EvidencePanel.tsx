"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { CompareAxisItem, PolicyAxisItem, Evidence } from "@/lib/types";
import { copyToClipboard, formatEvidenceRef } from "@/lib/api";
import { Copy, Check, Eye } from "lucide-react";
import { PdfPageViewer } from "./PdfPageViewer";

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
}

export function EvidencePanel({ data, isPolicyMode = false }: EvidencePanelProps) {
  const [copiedRef, setCopiedRef] = useState<string | null>(null);
  const [viewingEvidence, setViewingEvidence] = useState<Evidence | null>(null);

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

  const handleCopy = async (evidence: Evidence) => {
    const ref = formatEvidenceRef(evidence.document_id, evidence.page_start);
    const success = await copyToClipboard(ref);
    if (success) {
      setCopiedRef(ref);
      setTimeout(() => setCopiedRef(null), 2000);
    }
  };

  const handleView = (evidence: Evidence) => {
    setViewingEvidence(evidence);
  };

  return (
    <div className="space-y-2">
      {/* PDF Page Viewer Modal (Step U-2.5: highlightQuery 추가) */}
      {viewingEvidence && (
        <PdfPageViewer
          documentId={viewingEvidence.document_id}
          initialPage={viewingEvidence.page_start ?? 1}
          docType={viewingEvidence.doc_type}
          highlightQuery={viewingEvidence.preview?.slice(0, 120) || undefined}
          onClose={() => setViewingEvidence(null)}
        />
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
          const evidence = groupedByInsurer.get(insurer) || [];

          return (
            <AccordionItem key={insurer} value={insurer}>
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-2">
                  <span className="font-medium">
                    {INSURER_NAMES[insurer] || insurer}
                  </span>
                  <Badge variant="secondary">{evidence.length}건</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-2 pt-2">
                  {evidence.map((ev, idx) => (
                    <EvidenceCard
                      key={`${ev.document_id}-${ev.page_start}-${idx}`}
                      evidence={ev}
                      onCopy={handleCopy}
                      onView={handleView}
                      copiedRef={copiedRef}
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
}

function EvidenceCard({
  evidence,
  onCopy,
  onView,
  copiedRef,
}: EvidenceCardProps) {
  const ref = formatEvidenceRef(evidence.document_id, evidence.page_start);
  const isCopied = copiedRef === ref;

  return (
    <Card>
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 space-y-1">
            {/* Doc Type Badge */}
            <div className="flex items-center gap-2">
              <Badge
                className={
                  DOC_TYPE_COLORS[evidence.doc_type] ||
                  "bg-gray-100 text-gray-800"
                }
              >
                {evidence.doc_type}
              </Badge>
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
