"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info, CheckCircle, XCircle, AlertCircle, Bot, Cpu, FileText } from "lucide-react";

// Slot types (from API)
interface SlotEvidenceRef {
  document_id: number;
  page_start: number | null;
  chunk_id?: number | null;
}

interface LLMTrace {
  method: "rule" | "llm" | "hybrid";
  llm_used: boolean;
  llm_reason?: "flag_off" | "ambiguity_high" | "parse_fail" | "cost_guard" | "not_needed" | null;
  model?: string | null;
}

interface SlotInsurerValue {
  insurer_code: string;
  value: string | null;
  confidence: "high" | "medium" | "low" | "not_found";
  reason?: string | null;
  evidence_refs: SlotEvidenceRef[];
  trace?: LLMTrace | null;
}

interface ComparisonSlot {
  slot_key: string;
  label: string;
  comparable: boolean;
  insurers: SlotInsurerValue[];
  diff_summary?: string | null;
}

interface SlotsTableProps {
  slots: ComparisonSlot[];
  /** STEP 4.9: 단일 보험사만 표시할 때 해당 insurer_code 전달 */
  singleInsurer?: string;
}

const INSURER_NAMES: Record<string, string> = {
  SAMSUNG: "삼성",
  MERITZ: "메리츠",
  LOTTE: "롯데",
  DB: "DB",
  KB: "KB",
  HANWHA: "한화",
  HYUNDAI: "현대",
  HEUNGKUK: "흥국",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-orange-100 text-orange-800",
  not_found: "bg-gray-100 text-gray-500",
};

const CONFIDENCE_ICONS: Record<string, React.ReactNode> = {
  high: <CheckCircle className="h-3 w-3 text-green-600" />,
  medium: <AlertCircle className="h-3 w-3 text-yellow-600" />,
  low: <AlertCircle className="h-3 w-3 text-orange-600" />,
  not_found: <XCircle className="h-3 w-3 text-gray-400" />,
};

const LLM_REASON_LABELS: Record<string, string> = {
  flag_off: "flag",
  ambiguity_high: "ambiguity",
  parse_fail: "parse_fail",
  cost_guard: "cost",
  not_needed: "not_needed",
};

// =============================================================================
// U-4.18-δ: Slots Anti-Overreach Configuration
// =============================================================================

/** Maximum character length for slot values (120 chars or ~2 lines) */
const SLOT_VALUE_MAX_LENGTH = 120;

/** Fallback text when value exceeds max length */
const SLOT_OVERFLOW_FALLBACK = "일부 조건 요약\n(자세한 내용은 Evidence에서 확인)";

/** Source hint labels */
const SOURCE_HINT_LABELS: Record<string, string> = {
  COMPARABLE_DOC: "비교 문서 기준",
  POLICY_ONLY: "약관 기준",
  UNKNOWN: "근거 부족",
};

/**
 * U-4.18-δ: Truncate slot value if it exceeds max length
 * Also checks for overreach patterns (article numbers, detailed conditions)
 */
function truncateSlotValue(value: string | null): { text: string; truncated: boolean } {
  if (!value) return { text: "", truncated: false };

  // Check for overreach patterns (article numbers, multiple numbers, detailed conditions)
  const hasArticleNumber = /제\s*\d+\s*조|조항|약관/i.test(value);
  const multipleNumbers = (value.match(/\d+/g) || []).length >= 3;
  const hasDetailedCondition = /계약일로부터|경과\s*시|소액암|50%|90일/i.test(value);

  // If overreach detected or exceeds length, truncate
  if (hasArticleNumber || multipleNumbers || hasDetailedCondition || value.length > SLOT_VALUE_MAX_LENGTH) {
    return { text: SLOT_OVERFLOW_FALLBACK, truncated: true };
  }

  return { text: value, truncated: false };
}

function LLMBadge({ trace }: { trace?: LLMTrace | null }) {
  if (!trace) return null;

  if (trace.llm_used) {
    // LLM ON
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge
              variant="outline"
              className="text-[10px] px-1 py-0 h-4 bg-purple-50 text-purple-700 border-purple-200"
            >
              <Bot className="h-2.5 w-2.5 mr-0.5" />
              LLM
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p className="text-xs">
              LLM ON ({trace.model || "unknown"})
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // LLM OFF
  const reasonLabel = trace.llm_reason ? LLM_REASON_LABELS[trace.llm_reason] || trace.llm_reason : "off";
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className="text-[10px] px-1 py-0 h-4 bg-gray-50 text-gray-500 border-gray-200"
          >
            <Cpu className="h-2.5 w-2.5 mr-0.5" />
            rule
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-xs">
            LLM OFF ({reasonLabel})
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// U-4.18: Source Level Badge
function SourceLevelBadge({ sourceLevel }: { sourceLevel?: string }) {
  if (sourceLevel === "POLICY_ONLY") {
    return (
      <Badge
        variant="outline"
        className="text-[10px] px-1 py-0 h-4 bg-amber-50 text-amber-700 border-amber-200"
      >
        ⚠️ 약관 기준
      </Badge>
    );
  }
  return null;
}

function SlotValueCell({ iv }: { iv: SlotInsurerValue }) {
  // U-4.18: source_level 기반 렌더링
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sourceLevel = (iv as any).source_level as string | undefined;

  // UNKNOWN source_level with not_found
  if (iv.confidence === "not_found" || !iv.value) {
    return (
      <div className="space-y-1">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 text-gray-400">
                {CONFIDENCE_ICONS.not_found}
                <span className="text-sm">
                  {sourceLevel === "UNKNOWN" ? "근거 부족" : "미확인"}
                </span>
              </div>
            </TooltipTrigger>
            {iv.reason && (
              <TooltipContent>
                <p className="text-xs">{iv.reason}</p>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>
        <LLMBadge trace={iv.trace} />
        {/* U-4.18-δ: Source Hint */}
        <SourceHint sourceLevel={sourceLevel} />
      </div>
    );
  }

  // U-4.18-δ: Apply truncation to prevent overreach
  const { text: displayValue, truncated } = truncateSlotValue(iv.value);

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        {CONFIDENCE_ICONS[iv.confidence]}
        <span className={`text-sm ${truncated ? "text-muted-foreground italic" : "font-medium"}`}>
          {displayValue.split("\n").map((line, i) => (
            <span key={i}>
              {line}
              {i < displayValue.split("\n").length - 1 && <br />}
            </span>
          ))}
        </span>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        {iv.evidence_refs.length > 0 && (
          <span className="text-xs text-muted-foreground">
            {iv.evidence_refs.length}개 근거
          </span>
        )}
        <LLMBadge trace={iv.trace} />
        {/* U-4.18: Source Level Badge (약관만 표시) */}
        <SourceLevelBadge sourceLevel={sourceLevel} />
      </div>
      {/* U-4.18-δ: Source Hint (항상 표시) */}
      <SourceHint sourceLevel={sourceLevel} />
    </div>
  );
}

/**
 * U-4.18-δ: Source Hint Component
 * Shows source level hint below each slot item
 */
function SourceHint({ sourceLevel }: { sourceLevel?: string }) {
  const level = sourceLevel || "UNKNOWN";
  const label = SOURCE_HINT_LABELS[level] || SOURCE_HINT_LABELS.UNKNOWN;

  return (
    <span className="text-[10px] text-muted-foreground">
      ({label})
    </span>
  );
}

export function SlotsTable({ slots, singleInsurer }: SlotsTableProps) {
  if (!slots || slots.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        슬롯 비교 결과가 없습니다
      </div>
    );
  }

  // Get unique insurers from slots
  // STEP 4.9: singleInsurer가 지정되면 해당 insurer만 표시
  const allInsurers = slots[0]?.insurers.map((iv) => iv.insurer_code) || [];
  const insurers = singleInsurer
    ? allInsurers.filter((ic) => ic === singleInsurer)
    : allInsurers;

  // Separate comparable and non-comparable slots
  const comparableSlots = slots.filter((s) => s.comparable);
  const definitionSlots = slots.filter((s) => !s.comparable);

  // STEP 4.9: singleInsurer일 때 slot.insurers 필터링 헬퍼
  const filterInsurers = (ivList: SlotInsurerValue[]) =>
    singleInsurer ? ivList.filter((iv) => iv.insurer_code === singleInsurer) : ivList;

  return (
    <div className="space-y-6">
      {/* Comparable Slots Table */}
      {comparableSlots.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <span>비교 항목</span>
              <Badge variant="secondary" className="text-xs">
                {comparableSlots.length}개 슬롯
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium whitespace-nowrap">항목</th>
                    {insurers.map((ic) => (
                      <th key={ic} className="px-4 py-2 text-center font-medium whitespace-nowrap">
                        {INSURER_NAMES[ic] || ic}
                      </th>
                    ))}
                    {/* STEP 4.9: 단일 보험사에서는 diff_summary 열 불필요 */}
                    {!singleInsurer && (
                      <th className="px-4 py-2 text-left font-medium whitespace-nowrap">차이 요약</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {comparableSlots.map((slot) => (
                    <tr key={slot.slot_key} className="border-b">
                      <td className="px-4 py-2 font-medium">{slot.label}</td>
                      {filterInsurers(slot.insurers).map((iv) => (
                        <td key={iv.insurer_code} className="px-4 py-2 text-center">
                          <SlotValueCell iv={iv} />
                        </td>
                      ))}
                      {/* STEP 4.9: 단일 보험사에서는 diff_summary 불필요 */}
                      {!singleInsurer && (
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          {slot.diff_summary || "-"}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Definition Slots (약관 기반 - 참고용) */}
      {definitionSlots.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <span>정의/참고 (약관)</span>
              <Badge variant="outline" className="text-xs bg-orange-50 text-orange-700 border-orange-200">
                비교 계산 미사용
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {definitionSlots.map((slot) => (
                <div key={slot.slot_key} className="space-y-2">
                  <h4 className="text-sm font-medium flex items-center gap-1">
                    <Info className="h-3 w-3 text-muted-foreground" />
                    {slot.label}
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {filterInsurers(slot.insurers).map((iv) => (
                      <div
                        key={iv.insurer_code}
                        className="p-3 bg-muted/50 rounded-lg"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">
                            {INSURER_NAMES[iv.insurer_code] || iv.insurer_code}
                          </span>
                          <Badge className={CONFIDENCE_COLORS[iv.confidence]}>
                            {iv.confidence}
                          </Badge>
                        </div>
                        {iv.value ? (
                          <p className="text-xs text-muted-foreground line-clamp-3">
                            {iv.value}
                          </p>
                        ) : (
                          <p className="text-xs text-gray-400 italic">
                            {iv.reason || "정보 없음"}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* U-4.18-δ: Slots → Evidence 유도 안내 */}
      <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="flex items-start gap-2">
          <FileText className="h-4 w-4 text-gray-600 mt-0.5 shrink-0" />
          <div className="text-sm text-gray-700">
            <p className="text-xs">
              ※ Slots는 비교를 위한 요약 정보입니다.
              <br />
              세부 조건 및 근거 문구는 <span className="font-medium">Evidence 탭</span>에서 확인하세요.
            </p>
          </div>
        </div>
      </div>

      {/* A2 Policy Notice */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium">A2 정책</p>
            <p className="text-xs mt-1">
              비교 항목은 가입설계서/상품요약서/사업방법서에서 추출되며,
              정의/참고 항목은 약관에서 참조용으로만 제공됩니다.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
