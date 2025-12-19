"use client";

/**
 * STEP 3.8: Main Page with State Isolation
 *
 * Query State와 View State의 명확한 분리:
 * - Query State: messages, currentResponse, currentAnchor, isLoading
 *   → handleSendMessage로만 변경 가능
 * - View State: ViewContext를 통해 관리
 *   → Evidence/Document 열람은 Query State에 영향 없음
 */

import { useState, useCallback, useEffect, Suspense, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Image from "next/image";
import { ChatPanel } from "@/components/ChatPanel";
import { ResultsPanel } from "@/components/ResultsPanel";
import { PdfPageViewer } from "@/components/PdfPageViewer";
import { compare } from "@/lib/api";
import { ChatMessage, CompareRequestWithIntent, CompareResponseWithSlots, QueryAnchor } from "@/lib/types";
import { ViewProvider, useViewContext, ViewingDocument } from "@/contexts/ViewContext";

// =============================================================================
// Deep-link Handler (View State만 변경, Query State 변경 없음)
// =============================================================================

function DeepLinkHandler() {
  const searchParams = useSearchParams();
  const { openDeepLinkDocument } = useViewContext();

  useEffect(() => {
    const doc = searchParams.get("doc");
    const page = searchParams.get("page");
    const hl = searchParams.get("hl");

    if (doc && page) {
      // STEP 3.8: View State만 변경 (Query State 변경 없음)
      openDeepLinkDocument({
        documentId: doc,
        page: parseInt(page, 10) || 1,
        highlightQuery: hl || undefined,
      });
    }
  }, [searchParams, openDeepLinkDocument]);

  return null;
}

// =============================================================================
// Document Viewer Wrapper (View State 기반, Query State 불변)
// =============================================================================

function DocumentViewerLayer() {
  const router = useRouter();
  const { viewState, closeDocument, closeDeepLinkDocument } = useViewContext();
  const { viewingDocument, deepLinkDocument } = viewState;

  // Deep-link viewer 닫기 (Query State 변경 없음)
  const handleCloseDeepLink = useCallback(() => {
    closeDeepLinkDocument();
    // URL에서 파라미터 제거 (View State 변경만, Query State 불변)
    router.push("/", { scroll: false });
  }, [closeDeepLinkDocument, router]);

  // 일반 document viewer 닫기 (Query State 변경 없음)
  const handleCloseDocument = useCallback(() => {
    closeDocument();
  }, [closeDocument]);

  return (
    <>
      {/* Deep-link PDF Viewer (Step U-2.5, STEP 3.8: View State 분리) */}
      {deepLinkDocument && (
        <PdfPageViewer
          documentId={deepLinkDocument.documentId}
          initialPage={deepLinkDocument.page}
          highlightQuery={deepLinkDocument.highlightQuery}
          onClose={handleCloseDeepLink}
        />
      )}

      {/* Evidence/Policy PDF Viewer (STEP 3.8: View State 분리) */}
      {viewingDocument && (
        <PdfPageViewer
          documentId={viewingDocument.documentId}
          initialPage={viewingDocument.page}
          docType={viewingDocument.docType}
          highlightQuery={viewingDocument.highlightQuery}
          onClose={handleCloseDocument}
        />
      )}
    </>
  );
}

// =============================================================================
// Main Content (Query State 관리)
// =============================================================================

function HomeContent() {
  // ===========================================================================
  // Query State (handleSendMessage로만 변경 가능)
  // STEP 3.8: 이 상태들은 Evidence/Document 열람으로 절대 변경되지 않음
  // ===========================================================================
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentResponse, setCurrentResponse] = useState<CompareResponseWithSlots | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAnchor, setCurrentAnchor] = useState<QueryAnchor | null>(null);

  // ===========================================================================
  // Query State 변경 함수 (유일한 Query State 변경 경로)
  // STEP 3.8: send_message 이벤트만 Query State 변경 허용
  // ===========================================================================
  const handleSendMessage = useCallback(async (request: CompareRequestWithIntent) => {
    // STEP 3.6: 이전 anchor가 있으면 요청에 포함
    const requestWithAnchor: CompareRequestWithIntent = {
      ...request,
      anchor: currentAnchor ?? undefined,
    };

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
      const response = await compare(requestWithAnchor);
      setCurrentResponse(response);

      // STEP 3.6: 응답에서 anchor 저장 (다음 질의에 전달)
      if (response.anchor) {
        setCurrentAnchor(response.anchor);
      }

      // STEP 2.5: 사용자 친화적 요약 사용 (API에서 제공)
      let summaryText = "";

      // STEP 3.5: recovery_message가 있으면 먼저 표시
      if (response.recovery_message) {
        summaryText = `ℹ️ ${response.recovery_message}\n\n`;
      }

      // STEP 3.7: Coverage Resolution 실패 처리
      const resolution = response.coverage_resolution;
      if (resolution && resolution.status !== "resolved") {
        // 실패/추천/재질문 응답 처리
        if (resolution.message) {
          summaryText += `⚠️ ${resolution.message}`;
        }

        // suggested_coverages가 있으면 버튼 형태로 표시할 수 있도록 안내
        if (resolution.suggested_coverages && resolution.suggested_coverages.length > 0) {
          const suggestions = resolution.suggested_coverages
            .map((s) => `• ${s.coverage_name || s.coverage_code}`)
            .join("\n");
          summaryText += `\n\n${suggestions}`;
        }

        // 도메인이 감지된 경우 추가 안내
        if (resolution.detected_domain) {
          summaryText += `\n\n위 담보 중 하나를 선택하거나, 좀 더 구체적인 담보명을 입력해 주세요.`;
        }
      } else if (response.user_summary) {
        // user_summary가 있으면 그대로 사용
        summaryText += response.user_summary;
      } else {
        // Fallback: 기본 정보만 표시
        const compareAxis = response.compare_axis || [];
        const totalEvidence = compareAxis.reduce(
          (sum, item) => sum + (item.evidence?.length || 0),
          0
        );
        summaryText += `검색 완료: ${totalEvidence}건의 근거를 찾았습니다.\n\n자세한 비교표/근거는 오른쪽 패널을 확인해주세요.`;
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
  }, [currentAnchor]);

  // ===========================================================================
  // Memoized Response (STEP 3.8: 불필요한 re-render 방지)
  // ===========================================================================
  const memoizedResponse = useMemo(() => currentResponse, [currentResponse]);

  return (
    <div className="flex h-screen bg-background">
      {/* Deep-link URL 파라미터 처리 (STEP 3.8: View State만 변경) */}
      <Suspense fallback={null}>
        <DeepLinkHandler />
      </Suspense>

      {/* Document Viewers (STEP 3.8: View State 기반, Query State 불변) */}
      <DocumentViewerLayer />

      {/* Left: Chat Panel (Query State 표시) */}
      <div className="w-1/2 flex flex-col border-r">
        <header className="p-4 border-b">
          <div className="flex items-center gap-4">
            <Image
              src="/incar_logo.png"
              alt="INCAR Logo"
              width={160}
              height={160}
              className="rounded"
            />
            <div className="flex-1 flex flex-col items-end">
              <h1 className="text-3xl font-bold">AI RAG</h1>
              <p className="text-sm text-muted-foreground">
                Insurance Coverage Comparison
              </p>
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-hidden">
          <ChatPanel
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Right: Results Panel (Query State 표시, View State 격리) */}
      <div className="w-1/2 flex flex-col">
        <header className="p-4 border-b">
          <h2 className="text-lg font-semibold">비교 결과</h2>
        </header>
        <div className="flex-1 overflow-hidden">
          <ResultsPanel response={memoizedResponse} />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Root Component with ViewProvider
// =============================================================================

export default function Home() {
  return (
    <ViewProvider>
      <HomeContent />
    </ViewProvider>
  );
}
