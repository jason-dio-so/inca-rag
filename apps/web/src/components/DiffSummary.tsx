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

const DIFF_TYPE_COLORS: Record<string, string> = {
  amount_diff: "bg-blue-100 text-blue-800",
  coverage_missing: "bg-red-100 text-red-800",
  condition_diff: "bg-yellow-100 text-yellow-800",
  default: "bg-gray-100 text-gray-800",
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
      {data.map((item, idx) => (
        <Card key={idx}>
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              {/* Diff Type Badge */}
              <Badge
                className={
                  DIFF_TYPE_COLORS[item.diff_type] || DIFF_TYPE_COLORS.default
                }
              >
                {item.diff_type}
              </Badge>

              <div className="flex-1">
                {/* Description */}
                <p className="text-sm">{item.description}</p>

                {/* Affected Insurers */}
                {item.insurers_affected && item.insurers_affected.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {item.insurers_affected.map((insurer) => (
                      <Badge key={insurer} variant="outline" className="text-xs">
                        {INSURER_NAMES[insurer] || insurer}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Evidence References */}
                {item.evidence_refs && item.evidence_refs.length > 0 && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    <span className="font-medium">Refs: </span>
                    {item.evidence_refs.join(", ")}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
