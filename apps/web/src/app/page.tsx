"use client";

import { useState, useCallback, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ChatPanel } from "@/components/ChatPanel";
import { ResultsPanel } from "@/components/ResultsPanel";
import { PdfPageViewer } from "@/components/PdfPageViewer";
import { compare } from "@/lib/api";
import { ChatMessage, CompareRequest, CompareResponse } from "@/lib/types";

// Deep-link 상태 타입
interface DeepLinkState {
  documentId: string;
  page: number;
  highlightQuery?: string;
}

// Deep-link 처리 컴포넌트 (Suspense 경계 내에서 사용)
function DeepLinkHandler({
  onOpen,
}: {
  onOpen: (state: DeepLinkState) => void;
}) {
  const searchParams = useSearchParams();

  useEffect(() => {
    const doc = searchParams.get("doc");
    const page = searchParams.get("page");
    const hl = searchParams.get("hl");

    if (doc && page) {
      onOpen({
        documentId: doc,
        page: parseInt(page, 10) || 1,
        highlightQuery: hl || undefined,
      });
    }
  }, [searchParams, onOpen]);

  return null;
}

export default function Home() {
  const router = useRouter();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentResponse, setCurrentResponse] = useState<CompareResponse | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);

  // Deep-link: URL에서 viewer 상태 읽기
  const [deepLinkViewer, setDeepLinkViewer] = useState<DeepLinkState | null>(null);

  // Deep-link 열기 핸들러
  const handleDeepLinkOpen = useCallback((state: DeepLinkState) => {
    setDeepLinkViewer(state);
  }, []);

  // Deep-link viewer 닫기
  const handleCloseDeepLinkViewer = useCallback(() => {
    setDeepLinkViewer(null);
    // URL에서 파라미터 제거
    router.push("/", { scroll: false });
  }, [router]);

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
      {/* Deep-link URL 파라미터 처리 (Step U-2.5) */}
      <Suspense fallback={null}>
        <DeepLinkHandler onOpen={handleDeepLinkOpen} />
      </Suspense>

      {/* Deep-link PDF Viewer (Step U-2.5) */}
      {deepLinkViewer && (
        <PdfPageViewer
          documentId={deepLinkViewer.documentId}
          initialPage={deepLinkViewer.page}
          highlightQuery={deepLinkViewer.highlightQuery}
          onClose={handleCloseDeepLinkViewer}
        />
      )}

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
