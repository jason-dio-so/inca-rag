"use client";

/**
 * STEP 4.1: Subtype Comparison Panel
 *
 * 경계성 종양, 제자리암 등 질병 하위 개념(Subtype)의
 * 정의·포함 여부·조건 중심 비교 UI 제공
 */

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SubtypeComparison, SubtypeComparisonItem } from "@/lib/types";

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

const SUBTYPE_DISPLAY_NAMES: Record<string, string> = {
  BORDERLINE_TUMOR: "경계성 종양",
  CIS_CARCINOMA: "제자리암",
  SIMILAR_CANCER: "유사암",
  RECURRENT_CANCER: "재진단암",
  STROKE: "뇌졸중",
  CEREBROVASCULAR: "뇌혈관질환",
  ISCHEMIC_HEART: "허혈성심장질환",
};

interface SubtypeComparePanelProps {
  comparison: SubtypeComparison | null | undefined;
  insurers: string[];
}

export function SubtypeComparePanel({
  comparison,
  insurers,
}: SubtypeComparePanelProps) {
  if (!comparison || !comparison.is_multi_subtype || comparison.subtypes.length === 0) {
    return null;
  }

  // Group items by (subtype_code, info_type)
  const groupedItems: Record<string, Record<string, SubtypeComparisonItem>> = {};

  for (const item of comparison.comparison_items) {
    const key = `${item.subtype_code}:${item.info_type}`;
    if (!groupedItems[key]) {
      groupedItems[key] = {};
    }
    groupedItems[key][item.insurer_code] = item;
  }

  // Get unique subtype+info_type combinations
  const groupKeys = Object.keys(groupedItems);

  if (groupKeys.length === 0) {
    return null;
  }

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Badge variant="secondary" className="bg-purple-100 text-purple-700">
            다중 Subtype 비교
          </Badge>
          {comparison.subtypes.map((code) => (
            <Badge key={code} variant="outline" className="text-xs">
              {SUBTYPE_DISPLAY_NAMES[code] || code}
            </Badge>
          ))}
        </CardTitle>
        <CardDescription className="text-xs">
          경계성 종양, 제자리암 등 질병 하위 개념의 정의·포함 여부·조건 비교
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="overflow-x-auto">
          <Table className="text-sm">
            <TableHeader>
              <TableRow>
                <TableHead className="w-[120px]">Subtype</TableHead>
                <TableHead className="w-[80px]">항목</TableHead>
                {insurers.map((insurer) => (
                  <TableHead key={insurer} className="text-center min-w-[100px]">
                    {INSURER_NAMES[insurer] || insurer}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {groupKeys.map((key) => {
                const items = groupedItems[key];
                const firstItem = Object.values(items)[0];
                if (!firstItem) return null;

                return (
                  <TableRow key={key}>
                    <TableCell className="font-medium">
                      {SUBTYPE_DISPLAY_NAMES[firstItem.subtype_code] || firstItem.subtype_name}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {firstItem.info_label}
                    </TableCell>
                    {insurers.map((insurer) => {
                      const item = items[insurer];
                      return (
                        <TableCell key={insurer} className="text-center">
                          {item ? (
                            <SubtypeValueCell item={item} />
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function SubtypeValueCell({ item }: { item: SubtypeComparisonItem }) {
  if (item.confidence === "not_found" || !item.value) {
    return (
      <span className="text-muted-foreground text-xs">미확인</span>
    );
  }

  // Coverage status (Y/N/Unknown)
  if (item.info_type === "coverage") {
    if (item.value === "Y") {
      return (
        <Badge variant="default" className="bg-green-500 text-xs">
          보장
        </Badge>
      );
    }
    if (item.value === "N") {
      return (
        <Badge variant="destructive" className="text-xs">
          제외
        </Badge>
      );
    }
    if (item.value === "부분보장") {
      return (
        <Badge variant="secondary" className="bg-amber-100 text-amber-700 text-xs">
          부분보장
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="text-xs">
        {item.value}
      </Badge>
    );
  }

  // Definition or conditions (text)
  return (
    <div
      className="text-xs text-left max-w-[200px] overflow-hidden text-ellipsis"
      title={item.value}
    >
      {item.value.length > 50 ? `${item.value.slice(0, 50)}...` : item.value}
    </div>
  );
}
