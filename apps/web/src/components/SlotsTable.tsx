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
import { Info, CheckCircle, XCircle, AlertCircle, Bot, Cpu } from "lucide-react";

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

function SlotValueCell({ iv }: { iv: SlotInsurerValue }) {
  if (iv.confidence === "not_found" || !iv.value) {
    return (
      <div className="space-y-1">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 text-gray-400">
                {CONFIDENCE_ICONS.not_found}
                <span className="text-sm">미확인</span>
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
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        {CONFIDENCE_ICONS[iv.confidence]}
        <span className="text-sm font-medium">{iv.value}</span>
      </div>
      <div className="flex items-center gap-2">
        {iv.evidence_refs.length > 0 && (
          <span className="text-xs text-muted-foreground">
            {iv.evidence_refs.length}개 근거
          </span>
        )}
        <LLMBadge trace={iv.trace} />
      </div>
    </div>
  );
}

export function SlotsTable({ slots }: SlotsTableProps) {
  if (!slots || slots.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        슬롯 비교 결과가 없습니다
      </div>
    );
  }

  // Get unique insurers from slots
  const insurers = slots[0]?.insurers.map((iv) => iv.insurer_code) || [];

  // Separate comparable and non-comparable slots
  const comparableSlots = slots.filter((s) => s.comparable);
  const definitionSlots = slots.filter((s) => !s.comparable);

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
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[150px]">항목</TableHead>
                  {insurers.map((ic) => (
                    <TableHead key={ic} className="text-center">
                      {INSURER_NAMES[ic] || ic}
                    </TableHead>
                  ))}
                  <TableHead className="w-[200px]">차이 요약</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {comparableSlots.map((slot) => (
                  <TableRow key={slot.slot_key}>
                    <TableCell className="font-medium">{slot.label}</TableCell>
                    {slot.insurers.map((iv) => (
                      <TableCell key={iv.insurer_code} className="text-center">
                        <SlotValueCell iv={iv} />
                      </TableCell>
                    ))}
                    <TableCell className="text-xs text-muted-foreground">
                      {slot.diff_summary || "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
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
                    {slot.insurers.map((iv) => (
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

      {/* A2 Policy Notice */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium">A2 정책</p>
            <p className="text-xs mt-1">
              비교 항목(comparable=true)은 가입설계서/상품요약서/사업방법서에서 추출되며,
              정의/참고 항목은 약관에서 참조용으로만 제공됩니다.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
