"use client";

/**
 * STEP 3.7-γ: ChatPanel with Coverage Guide Isolation
 *
 * Chat 영역은 "대화"로서의 역할만 수행
 * 담보 선택 가이드는 CoverageGuidePanel로 분리되어 표시
 */

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChatMessage, CompareRequestWithIntent, SuggestedCoverage } from "@/lib/types";
import { ChevronDown, ChevronUp, Send } from "lucide-react";
import { CoverageGuidePanel } from "./CoverageGuidePanel";
import { CoverageGuideState } from "@/lib/conversation-hygiene.config";

const ALL_INSURERS = [
  "SAMSUNG",
  "LOTTE",
  "DB",
  "KB",
  "MERITZ",
  "HANWHA",
  "HYUNDAI",
  "HEUNGKUK",
];

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

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: (request: CompareRequestWithIntent) => void;
  isLoading: boolean;
  /** STEP 3.7-γ: Coverage Guide State (UI State) */
  coverageGuide?: CoverageGuideState | null;
  /** STEP 3.7-γ: 담보 선택 핸들러 */
  onSelectCoverage?: (coverage: SuggestedCoverage) => void;
  /** STEP 3.7-δ-γ10: Lifted insurer selection state */
  selectedInsurers: string[];
  onInsurersChange: (insurers: string[]) => void;
}

export function ChatPanel({
  messages,
  onSendMessage,
  isLoading,
  coverageGuide,
  onSelectCoverage,
  selectedInsurers,
  onInsurersChange,
}: ChatPanelProps) {
  const [query, setQuery] = useState("");
  // STEP 3.7-δ-γ10: selectedInsurers lifted to parent (page.tsx)
  const [age, setAge] = useState<string>("");
  const [gender, setGender] = useState<"M" | "F" | "">("");
  const [topK, setTopK] = useState<number>(5);
  const [coverageCodes, setCoverageCodes] = useState("");
  const [policyKeywords, setPolicyKeywords] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    // Find the scroll viewport inside ScrollArea
    if (scrollContainerRef.current) {
      const viewport = scrollContainerRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    }
  }, [messages]);

  // STEP 3.7-δ-γ10: Use lifted state callback
  const toggleInsurer = (insurer: string) => {
    const newInsurers = selectedInsurers.includes(insurer)
      ? selectedInsurers.filter((i) => i !== insurer)
      : [...selectedInsurers, insurer];
    onInsurersChange(newInsurers);
  };

  const handleSend = () => {
    // STEP 3.5: insurer 0개도 허용 (서버에서 auto-recovery 적용)
    if (!query.trim() || isLoading) return;

    const request: CompareRequestWithIntent = {
      insurers: selectedInsurers,
      query: query.trim(),
      top_k_per_insurer: topK,
    };

    if (age) {
      request.age = parseInt(age, 10);
    }
    if (gender) {
      request.gender = gender;
    }
    if (coverageCodes.trim()) {
      request.coverage_codes = coverageCodes
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);
    }
    if (policyKeywords.trim()) {
      request.policy_keywords = policyKeywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean);
    }

    onSendMessage(request);
    setQuery("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Messages Area - STEP 2.5: 스크롤 버그 수정 */}
      <div className="flex-1 overflow-hidden" ref={scrollContainerRef}>
        <ScrollArea className="h-full">
          <div className="p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-muted-foreground py-8">
                <p className="text-lg font-medium">보험 담보 비교 챗봇</p>
                <p className="text-sm mt-2">
                  질문을 입력하고 보험사를 선택해서 담보를 비교해보세요
                </p>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-4 py-2 ${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {message.isLoading ? (
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-[200px]" />
                      <Skeleton className="h-4 w-[150px]" />
                    </div>
                  ) : message.error ? (
                    <div className="text-destructive">{message.error}</div>
                  ) : (
                    <div className="whitespace-pre-wrap break-words overflow-y-auto max-h-[400px]">
                      {message.content}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* STEP 3.7-γ: Coverage Guide Panel (UI State, NOT Chat State) */}
            {/* 담보 미확정 상태에서만 표시, 항상 1개만 존재 */}
            <CoverageGuidePanel
              guide={coverageGuide ?? null}
              onSelectCoverage={onSelectCoverage}
            />
          </div>
        </ScrollArea>
      </div>

      {/* Input Area */}
      <div className="border-t bg-background p-4 space-y-3">
        {/* Advanced Options */}
        <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-between"
            >
              <span>Advanced 옵션</span>
              {advancedOpen ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-3 pt-3">
            {/* Insurers Selection */}
            <div>
              <label className="text-sm font-medium mb-2 block">
                보험사 선택
              </label>
              <div className="flex flex-wrap gap-2">
                {ALL_INSURERS.map((insurer) => (
                  <Badge
                    key={insurer}
                    variant={
                      selectedInsurers.includes(insurer) ? "default" : "outline"
                    }
                    className="cursor-pointer"
                    onClick={() => toggleInsurer(insurer)}
                  >
                    {INSURER_NAMES[insurer]}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Age & Gender */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium mb-1 block">나이</label>
                <Input
                  type="number"
                  placeholder="예: 40"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">성별</label>
                <div className="flex gap-2">
                  <Button
                    variant={gender === "M" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setGender(gender === "M" ? "" : "M")}
                  >
                    남
                  </Button>
                  <Button
                    variant={gender === "F" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setGender(gender === "F" ? "" : "F")}
                  >
                    여
                  </Button>
                </div>
              </div>
            </div>

            {/* Top K */}
            <div>
              <label className="text-sm font-medium mb-1 block">
                top_k_per_insurer: {topK}
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value, 10))}
                className="w-full"
              />
            </div>

            {/* Coverage Codes */}
            <div>
              <label className="text-sm font-medium mb-1 block">
                coverage_codes (쉼표 구분)
              </label>
              <Input
                placeholder="예: A4200_1,A4210"
                value={coverageCodes}
                onChange={(e) => setCoverageCodes(e.target.value)}
              />
            </div>

            {/* Policy Keywords */}
            <div>
              <label className="text-sm font-medium mb-1 block">
                policy_keywords (쉼표 구분)
              </label>
              <Input
                placeholder="예: 경계성,유사암"
                value={policyKeywords}
                onChange={(e) => setPolicyKeywords(e.target.value)}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* Selected Insurers Display (when advanced is closed) */}
        {!advancedOpen && (
          <div className="flex flex-wrap gap-1">
            {selectedInsurers.map((insurer) => (
              <Badge key={insurer} variant="secondary" className="text-xs">
                {INSURER_NAMES[insurer]}
              </Badge>
            ))}
          </div>
        )}

        {/* Message Input */}
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            placeholder="질문을 입력하세요... (예: 경계성 종양 암진단비)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="min-h-[60px] resize-none"
            disabled={isLoading}
          />
          <Button
            onClick={handleSend}
            disabled={!query.trim() || isLoading}
            className="px-4"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
