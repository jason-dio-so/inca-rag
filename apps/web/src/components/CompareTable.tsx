"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CoverageCompareItem, Evidence } from "@/lib/types";
import { copyToClipboard, formatEvidenceRef } from "@/lib/api";
import { Copy, Eye, Check } from "lucide-react";
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

// NOTE:
// This filter is defensive.
// A2 policy is enforced by the server.
// UI filtering is only for display safety.
// A2 Policy: 약관 제외 (Compare에서는 약관이 보이면 안 됨)
function filterNonPolicy(evidence: Evidence[]): Evidence[] {
  return evidence.filter((e) => e.doc_type !== "약관");
}

interface CompareTableProps {
  data: CoverageCompareItem[];
}

export function CompareTable({ data }: CompareTableProps) {
  const [copiedRef, setCopiedRef] = useState<string | null>(null);
  const [viewingEvidence, setViewingEvidence] = useState<Evidence | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        비교 결과가 없습니다
      </div>
    );
  }

  // Get all unique insurers from the data (insurers is a list, not dict)
  const allInsurers = new Set<string>();
  data.forEach((item) => {
    (item.insurers || []).forEach((cell) => {
      allInsurers.add(cell.insurer_code);
    });
  });
  const insurerList = Array.from(allInsurers).sort();

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
    <div className="space-y-4">
      {/* A2 Policy Notice */}
      <div className="text-sm text-muted-foreground space-y-1">
        <p>※ 비교 결과는 가입설계서·상품요약서·사업방법서를 기준으로 산출됩니다.</p>
        <p>※ 약관은 비교 계산에 사용되지 않습니다.</p>
      </div>

      {/* PDF Page Viewer Modal (Step U-2.5: highlightQuery 추가) */}
      {viewingEvidence && (
        <PdfPageViewer
          documentId={viewingEvidence.document_id}
          initialPage={viewingEvidence.page_start ?? 1}
          docType={viewingEvidence.doc_type}
          highlightQuery={viewingEvidence.preview?.slice(0, 120)}
          onClose={() => setViewingEvidence(null)}
        />
      )}

      {/* Compare Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b">
              <th className="text-left p-3 font-medium">담보</th>
              {insurerList.map((insurer) => (
                <th key={insurer} className="text-center p-3 font-medium min-w-[200px]">
                  {INSURER_NAMES[insurer] || insurer}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, idx) => (
              <tr key={idx} className="border-b">
                {/* STEP 4.9-β: coverage_code 노출 금지, display name만 표시 */}
                <td className="p-3 font-medium">
                  <div>{item.coverage_name || "담보"}</div>
                </td>
                {insurerList.map((insurer) => {
                  // insurers is a list, find by insurer_code
                  const insurerData = (item.insurers || []).find(
                    (cell) => cell.insurer_code === insurer
                  );
                  if (!insurerData) {
                    return (
                      <td key={insurer} className="p-3 text-center text-muted-foreground">
                        -
                      </td>
                    );
                  }

                  // U-4.18: source_level 기반 렌더링 규칙
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  const sourceLevel = (insurerData as any).source_level as string | undefined;

                  // COMPARABLE_DOC이 아닌 경우 비교 불가 표시
                  if (sourceLevel === "POLICY_ONLY") {
                    return (
                      <td key={insurer} className="p-3 text-center">
                        <div className="text-sm text-amber-600 bg-amber-50 rounded px-2 py-1">
                          비교 불가
                          <br />
                          <span className="text-xs text-muted-foreground">(동일 기준 문서 없음)</span>
                        </div>
                      </td>
                    );
                  }

                  if (sourceLevel === "UNKNOWN" || !sourceLevel) {
                    return (
                      <td key={insurer} className="p-3 text-center">
                        <div className="text-sm text-gray-500 bg-gray-50 rounded px-2 py-1">
                          근거 부족
                        </div>
                      </td>
                    );
                  }

                  // COMPARABLE_DOC: A2 Policy - Filter out 약관 from best_evidence
                  const filteredEvidence = filterNonPolicy(
                    insurerData.best_evidence || []
                  );

                  return (
                    <td key={insurer} className="p-3">
                      <div className="space-y-2">
                        {/* Evidence (A2: 약관 제외) */}
                        {filteredEvidence.slice(0, 2).map((evidence, eIdx) => (
                          <div
                            key={eIdx}
                            className="flex items-center gap-1 text-xs"
                          >
                            <Badge variant="secondary" className="text-[10px]">
                              {evidence.doc_type}
                            </Badge>
                            <span className="text-muted-foreground truncate">
                              {String(evidence.document_id).slice(0, 8)}:p{evidence.page_start ?? 0}
                            </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-5 w-5 p-0"
                              onClick={() => handleCopy(evidence)}
                              title="Copy ref"
                            >
                              {copiedRef ===
                              formatEvidenceRef(
                                evidence.document_id,
                                evidence.page_start ?? 0
                              ) ? (
                                <Check className="h-3 w-3 text-green-500" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-5 w-5 p-0"
                              onClick={() => handleView(evidence)}
                              title="View"
                            >
                              <Eye className="h-3 w-3" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
