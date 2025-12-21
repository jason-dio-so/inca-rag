"use client";

/**
 * STEP 3.7-γ: ChatPanel with Coverage Guide Isolation
 * STEP 5: Query Assist Integration
 *
 * Chat 영역은 "대화"로서의 역할만 수행
 * 담보 선택 가이드는 CoverageGuidePanel로 분리되어 표시
 * Query Assist 힌트는 선택적 적용 (자동 적용 금지)
 */

import { useState, useRef, useEffect, useCallback } from "react";
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
import { ChatMessage, CompareRequestWithIntent, SuggestedCoverage, QueryAssistResponse } from "@/lib/types";
import { ChevronDown, ChevronUp, Send, Sparkles } from "lucide-react";
import { CoverageGuidePanel } from "./CoverageGuidePanel";
import { CoverageGuideState } from "@/lib/conversation-hygiene.config";
import { QueryAssistHint } from "./QueryAssistHint";
import { queryAssist } from "@/lib/api";

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
  /** STEP 3.7-γ: 담보 선택 핸들러 (단일) */
  onSelectCoverage?: (coverage: SuggestedCoverage) => void;
  /** STEP 4.5-β: 담보 선택 핸들러 (복수) */
  onSelectCoverages?: (coverages: SuggestedCoverage[]) => void;
  /** STEP 3.7-δ-γ10: Lifted insurer selection state */
  selectedInsurers: string[];
  onInsurersChange: (insurers: string[]) => void;
  /** STEP 3.9: Locked coverage state */
  lockedCoverage?: { code: string; name: string } | null;
  /** STEP 3.9: Unlock coverage handler */
  onUnlockCoverage?: () => void;
}

export function ChatPanel({
  messages,
  onSendMessage,
  isLoading,
  coverageGuide,
  onSelectCoverage,
  onSelectCoverages,
  selectedInsurers,
  onInsurersChange,
  lockedCoverage,
  onUnlockCoverage,
}: ChatPanelProps) {
  const [query, setQuery] = useState("");
  // STEP 3.7-δ-γ10: selectedInsurers lifted to parent (page.tsx)
  const [age, setAge] = useState<string>("");
  const [gender, setGender] = useState<"M" | "F" | "">("");
  const [topK, setTopK] = useState<number>(5);
  const [coverageCodes, setCoverageCodes] = useState("");
  const [policyKeywords, setPolicyKeywords] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);

  // STEP 5: Query Assist state
  const [assistResponse, setAssistResponse] = useState<QueryAssistResponse | null>(null);
  const [isAssistLoading, setIsAssistLoading] = useState(false);
  const [showAssistHint, setShowAssistHint] = useState(false);

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

  // STEP 5: Query Assist - AI 힌트 요청
  const handleRequestAssist = useCallback(async () => {
    if (!query.trim() || isAssistLoading) return;

    setIsAssistLoading(true);
    setShowAssistHint(false);

    try {
      const response = await queryAssist({
        query: query.trim(),
        insurers: selectedInsurers,
        context: {
          has_anchor: !!lockedCoverage,
          locked_coverage_codes: lockedCoverage ? [lockedCoverage.code] : null,
        },
      });

      if (response) {
        setAssistResponse(response);
        setShowAssistHint(true);
      }
    } catch (error) {
      console.warn("Query assist error:", error);
    } finally {
      setIsAssistLoading(false);
    }
  }, [query, selectedInsurers, lockedCoverage, isAssistLoading]);

  // STEP 5: Apply assist hint
  const handleApplyAssist = useCallback((normalizedQuery: string, keywords: string[]) => {
    // 정규화된 질의로 교체 후 검색
    setQuery(normalizedQuery);
    setShowAssistHint(false);

    // 자동으로 검색 실행
    const request: CompareRequestWithIntent = {
      insurers: selectedInsurers,
      query: normalizedQuery,
      top_k_per_insurer: topK,
    };

    if (age) {
      request.age = parseInt(age, 10);
    }
    if (gender) {
      request.gender = gender;
    }
    if (keywords.length > 0) {
      request.policy_keywords = keywords;
    }

    onSendMessage(request);
    setQuery("");
  }, [selectedInsurers, topK, age, gender, onSendMessage]);

  // STEP 5: Ignore assist hint
  const handleIgnoreAssist = useCallback(() => {
    setShowAssistHint(false);
    // 원본 질의로 검색 진행
    handleSend();
  }, []);

  const handleSend = () => {
    // STEP 3.5: insurer 0개도 허용 (서버에서 auto-recovery 적용)
    if (!query.trim() || isLoading) return;

    const request: CompareRequestWithIntent = {
      insurers: selectedInsurers,
      query: query.trim(),
      top_k_per_insurer: topK,
    };

    // STEP 3.9: Debug logging for SSOT verification
    if (process.env.NODE_ENV !== "production") {
      console.log("[ChatPanel] UI selectedInsurers(state):", selectedInsurers);
      console.log("[ChatPanel] Outbound payload insurers:", request.insurers);
    }

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
    // STEP 5: 검색 시 assist 힌트 초기화
    setShowAssistHint(false);
    setAssistResponse(null);
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

            {/* STEP 3.7-γ + 4.5-β: Coverage Guide Panel (UI State, NOT Chat State) */}
            {/* 담보 미확정 상태에서만 표시, 항상 1개만 존재, 복수 선택 가능 */}
            <CoverageGuidePanel
              guide={coverageGuide ?? null}
              onSelectCoverage={onSelectCoverage}
              onSelectCoverages={onSelectCoverages}
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

        {/* STEP 3.9: Locked Coverage Display + UNLOCK Button */}
        {lockedCoverage && (
          <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
            <Badge variant="default" className="bg-amber-500">
              🔒 {lockedCoverage.name}
            </Badge>
            <span className="text-xs text-amber-700">담보 고정됨</span>
            {onUnlockCoverage && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onUnlockCoverage}
                className="ml-auto text-xs h-6 px-2"
              >
                담보 변경
              </Button>
            )}
          </div>
        )}

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

        {/* STEP 5: Query Assist Hint Card */}
        {showAssistHint && assistResponse && (
          <QueryAssistHint
            assistResponse={assistResponse}
            originalQuery={query}
            onApply={handleApplyAssist}
            onIgnore={handleIgnoreAssist}
            isLoading={isLoading}
          />
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
          {/* STEP 5: AI 힌트 버튼 */}
          <Button
            variant="outline"
            onClick={handleRequestAssist}
            disabled={!query.trim() || isLoading || isAssistLoading}
            className="px-3"
            title="AI 힌트"
          >
            <Sparkles className={`h-4 w-4 ${isAssistLoading ? "animate-pulse" : ""}`} />
          </Button>
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
