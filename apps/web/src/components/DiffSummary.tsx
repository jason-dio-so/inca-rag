"use client";

/**
 * STEP 4.0: Diff Summary with Summary Text Section
 *
 * 비교 결과 상단에 요약 문구를 표시합니다.
 * - 기존 Diff 계산 결과만 사용 (새로운 계산 금지)
 * - 유리/불리/추천 표현 사용 금지
 */

import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { DiffSummaryItem } from "@/lib/types";
import {
  INSURER_NAMES,
  generateDiffSummaryTexts,
  SUMMARY_STYLES,
  DiffSummaryText,
} from "@/lib/diff-summary.config";
import { FileText } from "lucide-react";

interface DiffSummaryProps {
  data: DiffSummaryItem[];
}

/**
 * 요약 문구 섹션 (STEP 4.0)
 */
function SummaryTextSection({ summaries }: { summaries: DiffSummaryText[] }) {
  if (summaries.length === 0) return null;

  return (
    <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg">
      <div className="flex items-start gap-2 mb-2">
        <FileText className="h-4 w-4 text-slate-600 mt-0.5 shrink-0" />
        <span className="text-sm font-medium text-slate-700">요약</span>
      </div>
      <ul className="space-y-1.5 ml-6">
        {summaries.map((summary, idx) => {
          const style = SUMMARY_STYLES[summary.type];
          return (
            <li
              key={idx}
              className={`text-sm px-2 py-1 rounded ${style.bgColor} ${style.textColor}`}
            >
              {summary.text}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function DiffSummary({ data }: DiffSummaryProps) {
  // STEP 4.0: Generate summary texts from existing diff bullets
  const summaryTexts = useMemo(() => {
    if (!data || data.length === 0) return [];

    const allTexts: DiffSummaryText[] = [];
    const seenTexts = new Set<string>();

    for (const item of data) {
      const bullets = item.bullets || [];
      for (const bullet of bullets) {
        if (bullet.text && !seenTexts.has(bullet.text)) {
          seenTexts.add(bullet.text);
          const refs = bullet.evidence_refs || [];
          const insurerCodes = [...new Set(refs.map(r => r.insurer_code))];
          const texts = generateDiffSummaryTexts([bullet.text], insurerCodes);
          allTexts.push(...texts);
        }
      }
    }

    return allTexts;
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        차이점이 없거나 비교 결과가 없습니다
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* STEP 4.0: Summary Text Section */}
      <SummaryTextSection summaries={summaryTexts} />
      {data.map((item, idx) => {
        const bullets = item.bullets || [];
        const displayName = item.coverage_name || item.coverage_code || "항목";

        return (
          <Card key={idx}>
            <CardContent className="p-4">
              <div className="space-y-2">
                {/* Coverage Header */}
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{item.coverage_code}</Badge>
                  <span className="font-medium">{displayName}</span>
                </div>

                {/* Bullets */}
                {bullets.length > 0 ? (
                  <ul className="space-y-2 ml-2">
                    {bullets.map((bullet, bIdx) => {
                      const refs = bullet.evidence_refs || [];
                      // Get unique insurers from evidence refs
                      const insurers = [...new Set(refs.map((r) => r.insurer_code))];

                      return (
                        <li key={bIdx} className="text-sm">
                          <p>{bullet.text}</p>
                          {insurers.length > 0 && (
                            <div className="mt-1 flex flex-wrap gap-1">
                              {insurers.map((insurer) => (
                                <Badge
                                  key={insurer}
                                  variant="secondary"
                                  className="text-xs"
                                >
                                  {INSURER_NAMES[insurer] || insurer}
                                </Badge>
                              ))}
                            </div>
                          )}
                          {refs.length > 0 && (
                            <div className="mt-1 text-xs text-muted-foreground">
                              <span className="font-medium">Refs: </span>
                              {refs
                                .map((r) => `${r.document_id}:${r.page_start ?? 0}`)
                                .join(", ")}
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground ml-2">
                    상세 차이점 정보 없음
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
