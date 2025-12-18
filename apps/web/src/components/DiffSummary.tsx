"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { DiffSummaryItem } from "@/lib/types";

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

interface DiffSummaryProps {
  data: DiffSummaryItem[];
}

export function DiffSummary({ data }: DiffSummaryProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        차이점이 없거나 비교 결과가 없습니다
      </div>
    );
  }

  return (
    <div className="space-y-3">
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
