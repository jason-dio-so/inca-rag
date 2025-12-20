"use client";

/**
 * STEP 4.1 + 4.6: Subtype Comparison Panel
 *
 * 경계성 종양, 제자리암 등 질병 하위 개념(Subtype)의
 * 정의·포함 여부·조건 중심 비교 UI 제공
 *
 * STEP 4.6 결과 표현 규약:
 * - Subtype별로 그룹핑 (금액 중심 단일 테이블 표현 금지)
 * - 각 Subtype 결과는 자기 근거만 사용
 * - 근거 없는 요약 문구 생성 금지
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
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
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

  // STEP 4.6: Group items by subtype_code first, then by info_type
  // Structure: { subtype_code: { info_type: { insurer_code: item } } }
  const bySubtype: Record<string, Record<string, Record<string, SubtypeComparisonItem>>> = {};

  for (const item of comparison.comparison_items) {
    if (!bySubtype[item.subtype_code]) {
      bySubtype[item.subtype_code] = {};
    }
    if (!bySubtype[item.subtype_code][item.info_type]) {
      bySubtype[item.subtype_code][item.info_type] = {};
    }
    bySubtype[item.subtype_code][item.info_type][item.insurer_code] = item;
  }

  const subtypeCodes = Object.keys(bySubtype);

  if (subtypeCodes.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Badge variant="secondary" className="bg-purple-100 text-purple-700">
          다중 Subtype 비교
        </Badge>
        <span className="text-xs text-muted-foreground">
          ({comparison.subtypes.length}개 subtype)
        </span>
      </div>

      {/* STEP 4.6: Subtype별 분리 그룹핑 - Accordion 형태 */}
      <Accordion type="multiple" defaultValue={subtypeCodes} className="space-y-3">
        {subtypeCodes.map((subtypeCode) => {
          const infoTypes = bySubtype[subtypeCode];
          const displayName = SUBTYPE_DISPLAY_NAMES[subtypeCode] || subtypeCode;

          return (
            <AccordionItem key={subtypeCode} value={subtypeCode} className="border rounded-lg">
              <AccordionTrigger className="px-4 py-3 hover:no-underline">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-medium">
                    {displayName}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    ({Object.keys(infoTypes).length}개 항목)
                  </span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4">
                <SubtypeGroupTable
                  subtypeCode={subtypeCode}
                  infoTypes={infoTypes}
                  insurers={insurers}
                />
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}

/**
 * STEP 4.6: 각 Subtype의 비교 테이블
 * - 보장 여부
 * - 정의 요약
 * - 지급 조건
 * - (근거 문서는 Evidence 탭 참조)
 */
function SubtypeGroupTable({
  subtypeCode,
  infoTypes,
  insurers,
}: {
  subtypeCode: string;
  infoTypes: Record<string, Record<string, SubtypeComparisonItem>>;
  insurers: string[];
}) {
  const infoTypeOrder = ["coverage", "definition", "conditions"];
  const sortedInfoTypes = Object.keys(infoTypes).sort((a, b) => {
    const idxA = infoTypeOrder.indexOf(a);
    const idxB = infoTypeOrder.indexOf(b);
    return (idxA === -1 ? 99 : idxA) - (idxB === -1 ? 99 : idxB);
  });

  return (
    <div className="overflow-x-auto">
      <Table className="text-sm">
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">항목</TableHead>
            {insurers.map((insurer) => (
              <TableHead key={insurer} className="text-center min-w-[120px]">
                {INSURER_NAMES[insurer] || insurer}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedInfoTypes.map((infoType) => {
            const items = infoTypes[infoType];
            const firstItem = Object.values(items)[0];
            if (!firstItem) return null;

            return (
              <TableRow key={infoType}>
                <TableCell className="font-medium text-muted-foreground">
                  {firstItem.info_label}
                </TableCell>
                {insurers.map((insurer) => {
                  const item = items[insurer];
                  return (
                    <TableCell key={insurer} className="text-center align-top">
                      {item ? (
                        <SubtypeValueCell item={item} />
                      ) : (
                        <span className="text-muted-foreground text-xs">-</span>
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
