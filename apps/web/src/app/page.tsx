"use client";

import { useState, useCallback } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { ResultsPanel } from "@/components/ResultsPanel";
import { compare } from "@/lib/api";
import { ChatMessage, CompareRequest, CompareResponse } from "@/lib/types";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentResponse, setCurrentResponse] = useState<CompareResponse | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = useCallback(async (request: CompareRequest) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: request.query,
      timestamp: new Date(),
    };

    // Add loading assistant message
    const assistantId = `assistant-${Date.now()}`;
    const loadingMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setIsLoading(true);

    try {
      const response = await compare(request);
      setCurrentResponse(response);

      // Generate summary from diff_summary
      const diffSummary = response.diff_summary || [];
      let summaryText = "";

      if (diffSummary.length > 0) {
        const topDiffs = diffSummary.slice(0, 3);
        summaryText = topDiffs
          .map((d, i) => `${i + 1}. ${d.description}`)
          .join("\n");
        summaryText += "\n\n자세한 비교표/근거는 오른쪽 패널을 확인해주세요.";
      } else {
        // No diff summary, show basic info
        const compareAxis = response.compare_axis || [];
        const totalEvidence = compareAxis.reduce(
          (sum, item) => sum + (item.evidence?.length || 0),
          0
        );
        summaryText = `검색 완료: ${totalEvidence}건의 근거를 찾았습니다.\n\n자세한 비교표/근거는 오른쪽 패널을 확인해주세요.`;
      }

      // Update assistant message
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: summaryText, isLoading: false }
            : msg
        )
      );
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "알 수 없는 오류";

      // Update assistant message with error
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, isLoading: false, error: errorMessage }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="flex h-screen bg-background">
      {/* Left: Chat Panel */}
      <div className="w-1/2 flex flex-col border-r">
        <header className="p-4 border-b">
          <h1 className="text-lg font-semibold">보험 담보 비교</h1>
          <p className="text-sm text-muted-foreground">
            Insurance Coverage Comparison
          </p>
        </header>
        <div className="flex-1 overflow-hidden">
          <ChatPanel
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Right: Results Panel */}
      <div className="w-1/2 flex flex-col">
        <header className="p-4 border-b">
          <h2 className="text-lg font-semibold">비교 결과</h2>
        </header>
        <div className="flex-1 overflow-hidden">
          <ResultsPanel response={currentResponse} />
        </div>
      </div>
    </div>
  );
}
