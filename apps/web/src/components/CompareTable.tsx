"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CoverageCompareItem, Evidence } from "@/lib/types";
import { copyToClipboard, formatEvidenceRef } from "@/lib/api";
import { Copy, Eye, Check } from "lucide-react";

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

  // Get all unique insurers from the data
  const allInsurers = new Set<string>();
  data.forEach((item) => {
    Object.keys(item.insurers || {}).forEach((insurer) => {
      allInsurers.add(insurer);
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
      {/* Evidence View Modal */}
      {viewingEvidence && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="max-w-lg w-full mx-4">
            <CardHeader>
              <CardTitle className="flex justify-between items-center">
                <span>Evidence 상세</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setViewingEvidence(null)}
                >
                  &times;
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div>
                <span className="font-medium">Document ID:</span>{" "}
                {viewingEvidence.document_id}
              </div>
              <div>
                <span className="font-medium">Page:</span>{" "}
                {viewingEvidence.page_start}
                {viewingEvidence.page_end &&
                  viewingEvidence.page_end !== viewingEvidence.page_start &&
                  ` - ${viewingEvidence.page_end}`}
              </div>
              <div>
                <span className="font-medium">Doc Type:</span>{" "}
                <Badge variant="outline">{viewingEvidence.doc_type}</Badge>
              </div>
              {viewingEvidence.source_path && (
                <div>
                  <span className="font-medium">Source:</span>{" "}
                  <span className="text-sm text-muted-foreground break-all">
                    {viewingEvidence.source_path}
                  </span>
                </div>
              )}
              {viewingEvidence.snippet && (
                <div>
                  <span className="font-medium">Snippet:</span>
                  <p className="text-sm mt-1 p-2 bg-muted rounded">
                    {viewingEvidence.snippet}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
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
                <td className="p-3 font-medium">
                  <div>{item.coverage_name || item.coverage_code}</div>
                  {item.coverage_name && (
                    <div className="text-xs text-muted-foreground">
                      {item.coverage_code}
                    </div>
                  )}
                </td>
                {insurerList.map((insurer) => {
                  const insurerData = item.insurers?.[insurer];
                  if (!insurerData) {
                    return (
                      <td key={insurer} className="p-3 text-center text-muted-foreground">
                        -
                      </td>
                    );
                  }

                  // A2 Policy: Filter out 약관 from best_evidence
                  const filteredEvidence = filterNonPolicy(
                    insurerData.best_evidence || []
                  );

                  return (
                    <td key={insurer} className="p-3">
                      <div className="space-y-2">
                        {/* Amount */}
                        {insurerData.resolved_amount && (
                          <div className="text-lg font-bold text-primary">
                            {insurerData.resolved_amount}
                          </div>
                        )}

                        {/* Condition */}
                        {insurerData.condition_snippet && (
                          <div className="text-sm text-muted-foreground line-clamp-2">
                            {insurerData.condition_snippet}
                          </div>
                        )}

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
                              {evidence.document_id.slice(0, 8)}:p{evidence.page_start}
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
                                evidence.page_start
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
