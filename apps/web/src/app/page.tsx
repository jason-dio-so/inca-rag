"use client";

/**
 * STEP 3.8: Main Page with State Isolation
 * STEP 3.7-γ: Coverage Guide Isolation / Conversation Hygiene
 * STEP 3.7-δ-γ: Frontend derives UI only from resolution_state
 *
 * Query State와 View State의 명확한 분리:
 * - Query State: messages, currentResponse, currentAnchor, isLoading
 *   → handleSendMessage로만 변경 가능
 * - View State: ViewContext를 통해 관리
 *   → Evidence/Document 열람은 Query State에 영향 없음
 *
 * Conversation Hygiene (STEP 3.7-γ):
 * - 담보 미확정 안내는 ChatMessage가 아님
 * - UNRESOLVED / INVALID는 UI State로 취급
 * - 가이드는 항상 1개만 존재 (교체, 누적 금지)
 * - RESOLVED 상태에서만 Chat 로그에 정상 응답 추가
 *
 * STEP 3.7-δ-γ: resolution_state만 사용
 * - coverage_resolution.status에서 재계산 금지
 * - API 응답의 resolution_state를 직접 사용
 */

import { useState, useCallback, useEffect, Suspense, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Image from "next/image";
import { ChatPanel } from "@/components/ChatPanel";
import { ResultsPanel } from "@/components/ResultsPanel";
import { PdfPageViewer } from "@/components/PdfPageViewer";
import { SingleCoverageDetailView, determineUIMode } from "@/components/SingleCoverageDetailView";
import { compare } from "@/lib/api";
import { ChatMessage, CompareRequestWithIntent, CompareResponseWithSlots, CompareResponseWithSubtype, QueryAnchor, SuggestedCoverage } from "@/lib/types";
import { ViewProvider, useViewContext } from "@/contexts/ViewContext";
import {
  CoverageGuideState,
  createCoverageGuideState,
} from "@/lib/conversation-hygiene.config";
import {
  detectResetCondition,
  resolveAnchorUpdate,
  resolveResolutionState,
  logTransition,
} from "@/lib/resolution-lock.config";
import { ResolutionState } from "@/lib/ui-gating.config";

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
  // STEP 3.7-γ: Coverage Guide State (UI State, NOT Chat State)
  // - 담보 미확정 안내는 ChatMessage가 아님
  // - 항상 1개만 존재 (새 질의 시 교체)
  // ===========================================================================
  const [coverageGuide, setCoverageGuide] = useState<CoverageGuideState | null>(null);

  // ===========================================================================
  // STEP 3.7-δ-γ10: Lifted Insurer Selection State
  // - UI 체크박스 선택값이 유일한 Source of Truth
  // - 담보 선택 시에도 insurers 변경 금지
  // ===========================================================================
  const [selectedInsurers, setSelectedInsurers] = useState<string[]>([
    "SAMSUNG",
    "MERITZ",
  ]);

  // ===========================================================================
  // STEP 3.9 + 4.5: Explicit Coverage Lock State
  // - 사용자가 명시적으로 담보를 선택하면 lock
  // - UNLOCK 버튼을 누르기 전까지 유지
  // - STEP 4.5: 복수 담보 지원 (멀티 subtype)
  // ===========================================================================
  const [lockedCoverages, setLockedCoverages] = useState<Array<{
    code: string;
    name: string;
  }>>([]);

  // 하위 호환성: 첫 번째 locked coverage 반환
  const lockedCoverage = lockedCoverages.length > 0 ? lockedCoverages[0] : null;

  // ===========================================================================
  // Query State 변경 함수 (유일한 Query State 변경 경로)
  // STEP 3.8: send_message 이벤트만 Query State 변경 허용
  // STEP 3.7-γ: EXACT 상태에서만 Chat 로그에 응답 추가
  // STEP 3.7-δ: Resolution Lock - EXACT 상태 퇴행 방지
  // ===========================================================================
  const handleSendMessage = useCallback(async (request: CompareRequestWithIntent) => {
    // STEP 3.9 + 4.5: 명시적 coverage lock이 있으면 항상 사용 (리셋 조건 무시)
    // lockedCoverages는 사용자가 UNLOCK 버튼을 누르기 전까지 유지
    const effectiveLockedCodes = lockedCoverages.length > 0
      ? lockedCoverages.map(c => c.code)
      : undefined;

    // STEP 3.7-δ: 리셋 조건 감지 (새 담보 키워드 질의 등) - lock이 없을 때만 적용
    const resetCondition = lockedCoverages.length > 0 ? null : detectResetCondition(request.query, currentAnchor);

    console.log("[STEP 4.5] Anchor Persistence:", {
      query: request.query,
      lockedCoverages,
      effectiveLockedCodes,
      resetCondition,
      currentAnchor: currentAnchor?.coverage_code,
    });

    // STEP 3.6: 이전 anchor가 있으면 요청에 포함 (리셋 조건이 아닐 때만)
    // STEP 4.5: locked_coverage_codes 사용 (복수 담보 지원)
    const requestWithAnchor: CompareRequestWithIntent = {
      ...request,
      anchor: resetCondition ? undefined : (currentAnchor ?? undefined),
      locked_coverage_codes: effectiveLockedCodes,
    };

    // STEP 3.7-γ: 새 질의 시 기존 가이드 제거 (교체 준비)
    setCoverageGuide(null);

    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: request.query,
      timestamp: new Date(),
    };

    // STEP 3.7-γ: 일단 사용자 메시지만 추가, 로딩 메시지는 EXACT일 때만 표시
    const assistantId = `assistant-${Date.now()}`;
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await compare(requestWithAnchor);

      // =======================================================================
      // STEP 3.7-δ-γ: Resolution Lock 적용 (resolution_state 직접 사용)
      // - Lock 위반 시 기존 anchor 유지, 새 resolution 무시
      // =======================================================================
      const currentState: ResolutionState | null = currentAnchor ? "RESOLVED" : null;
      const newState: ResolutionState = response.resolution_state || "RESOLVED";

      // Resolution Lock: anchor 업데이트 결정
      const resolvedAnchor = resolveAnchorUpdate(
        currentAnchor,
        response.anchor,
        newState,
        resetCondition
      );

      // Resolution Lock: 상태 결정 (Lock 위반 시 RESOLVED 유지)
      const resolvedState = resolveResolutionState(
        currentAnchor,
        newState,
        resetCondition
      );

      // 디버그 로그
      logTransition(currentState, newState, resolvedState === newState, resetCondition ?? undefined);

      // STEP 3.7-δ-γ: Lock 위반 시 기존 anchor + 기존 response 유지
      const isLockViolated = resolvedState !== newState;
      setCurrentAnchor(resolvedAnchor);

      // Lock 위반이 아닌 경우에만 response 업데이트
      if (!isLockViolated) {
        setCurrentResponse(response);
      } else {
        console.log("[Resolution Lock] Lock violation - keeping previous response");
      }

      // =======================================================================
      // STEP 3.7-δ-γ5: resolution_state 우선순위 (UNRESOLVED > INVALID > RESOLVED)
      // - UNRESOLVED: "담보 선택 필요" + 후보 버튼
      // - INVALID: "담보 미확정" (후보 없음)
      // - RESOLVED: 결과 표시
      // =======================================================================
      const canAddToChat = resolvedState === "RESOLVED";

      if (!canAddToChat) {
        // (A) UNRESOLVED / INVALID: ChatMessage 추가 ❌, Guide Panel 표시 ✅
        // STEP 3.7-δ-γ6: 전체 후보 렌더링 (slice/filter 없음)
        const candidates =
          response.coverage_resolution?.suggested_coverages ?? [];

        const guide = createCoverageGuideState({
          resolutionState: resolvedState,
          message: response.coverage_resolution?.message,
          suggestedCoverages: candidates,
          detectedDomain: response.coverage_resolution?.detected_domain,
          originalQuery: request.query,
        });
        setCoverageGuide(guide);
        // 사용자 메시지는 이미 추가됨, assistant 메시지는 추가하지 않음
        return;
      }

      // (B) RESOLVED: ChatMessage 정상 응답 추가 ✅, Guide Panel 제거 ✅
      setCoverageGuide(null);

      // STEP 2.5: 사용자 친화적 요약 사용 (API에서 제공)
      let summaryText = "";

      // STEP 3.5: recovery_message가 있으면 먼저 표시
      if (response.recovery_message) {
        summaryText = `ℹ️ ${response.recovery_message}\n\n`;
      }

      if (response.user_summary) {
        // user_summary가 있으면 그대로 사용
        summaryText += response.user_summary;
      } else {
        // Fallback: 기본 정보만 표시
        const compareAxis = response.compare_axis || [];
        const totalEvidence = compareAxis.reduce(
          (sum, item) => sum + (item.evidence?.length || 0),
          0
        );
        summaryText += `검색 완료: ${totalEvidence}건의 근거를 찾았습니다.\n\n자세한 비교 내용은 오른쪽 패널을 확인해주세요.`;
      }

      // Add assistant message (EXACT 상태에서만)
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: summaryText,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "알 수 없는 오류";

      // 에러 발생 시 assistant 메시지로 표시 (이것은 대화의 일부)
      const errorAssistantMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        error: errorMessage,
      };
      setMessages((prev) => [...prev, errorAssistantMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [currentAnchor, lockedCoverages]);

  // ===========================================================================
  // STEP 3.7-δ-γ2 + 4.5: 담보 선택 핸들러 (Guide Panel에서 담보 선택 시)
  // coverage_code를 직접 전달하여 즉시 RESOLVED 상태로 전환
  // STEP 3.7-δ-γ10: UI 선택된 insurers 유지 (하드코딩 금지)
  // STEP 4.5: 복수 담보 선택 지원 (멀티 subtype)
  // ===========================================================================
  const handleSelectCoverage = useCallback((coverage: SuggestedCoverage) => {
    const coverageCode = coverage.coverage_code;
    const coverageName = coverage.coverage_name || coverageCode;
    if (coverageCode) {
      // STEP 4.5: 사용자가 담보를 선택하면 명시적으로 lock
      setLockedCoverages([{ code: coverageCode, name: coverageName }]);
      setCoverageGuide(null);

      console.log("[STEP 4.5] Coverage locked by user:", { code: coverageCode, name: coverageName });

      // STEP 3.7-δ-γ10: UI 선택된 insurers 사용 (기본값 하드코딩 금지)
      handleSendMessage({
        query: coverageName,
        insurers: selectedInsurers, // UI 선택값 사용
        coverage_codes: [coverageCode],
        top_k_per_insurer: 5,
      });
    }
  }, [handleSendMessage, selectedInsurers]);

  // ===========================================================================
  // STEP 4.5-β: 복수 담보 선택 핸들러 (멀티 subtype 비교)
  // ===========================================================================
  const handleSelectCoverages = useCallback((coverages: SuggestedCoverage[]) => {
    if (coverages.length === 0) return;

    const lockedItems = coverages.map(c => ({
      code: c.coverage_code,
      name: c.coverage_name || c.coverage_code,
    }));
    const codes = coverages.map(c => c.coverage_code);
    const names = coverages.map(c => c.coverage_name || c.coverage_code).join(", ");

    setLockedCoverages(lockedItems);
    setCoverageGuide(null);

    console.log("[STEP 4.5-β] Multiple coverages locked by user:", lockedItems);

    handleSendMessage({
      query: names,
      insurers: selectedInsurers,
      coverage_codes: codes,
      top_k_per_insurer: 5,
    });
  }, [handleSendMessage, selectedInsurers]);

  // ===========================================================================
  // STEP 3.9 + 4.5: UNLOCK 핸들러 (담보 변경 버튼)
  // - 명시적 lock 해제
  // - 다음 질의에서 다시 UNRESOLVED 플로우로 진입
  // ===========================================================================
  const handleUnlockCoverage = useCallback(() => {
    console.log("[STEP 4.5] Coverage unlocked by user");
    setLockedCoverages([]);
    setCurrentAnchor(null);
    setCoverageGuide(null);
    setCurrentResponse(null);
  }, []);

  // ===========================================================================
  // Memoized Response (STEP 3.8: 불필요한 re-render 방지)
  // ===========================================================================
  const memoizedResponse = useMemo(() => currentResponse, [currentResponse]);

  // ===========================================================================
  // STEP 4.9: UI Mode 결정 (SINGLE_DETAIL / COMPARE / GUIDE)
  // 정답 경로: debug.anchor.coverage_locked, debug.anchor.locked_coverage_codes
  // ===========================================================================
  const uiMode = useMemo(
    () => determineUIMode(selectedInsurers, memoizedResponse as CompareResponseWithSubtype | null),
    [selectedInsurers, memoizedResponse]
  );

  // STEP 4.9: 단일 상세 뷰에서 필요한 정보 추출
  const singleDetailInfo = useMemo(() => {
    if (uiMode !== "SINGLE_DETAIL" || !memoizedResponse) return null;

    const debug = memoizedResponse.debug as Record<string, unknown> | undefined;
    const anchor = debug?.anchor as {
      locked_coverage_codes?: string[];
    } | undefined;
    const lockedCode = anchor?.locked_coverage_codes?.[0] || lockedCoverages[0]?.code;
    const lockedName = lockedCoverages[0]?.name;

    return {
      insurerCode: selectedInsurers[0],
      coverageCode: lockedCode,
      coverageName: lockedName,
    };
  }, [uiMode, memoizedResponse, selectedInsurers, lockedCoverages]);

  return (
    // STEP 4.9-β-1: 최상위 컨테이너는 overflow-hidden (이중 스크롤 방지)
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Deep-link URL 파라미터 처리 (STEP 3.8: View State만 변경) */}
      <Suspense fallback={null}>
        <DeepLinkHandler />
      </Suspense>

      {/* Document Viewers (STEP 3.8: View State 기반, Query State 불변) */}
      <DocumentViewerLayer />

      {/* Left: Chat Panel (Query State 표시) */}
      {/* STEP 4.9-β-1: 좌측 패널 - header 고정, 내부 flex-col로 스크롤 책임 전달 */}
      <div className="w-1/2 flex flex-col border-r">
        {/* 헤더: shrink-0 (고정) */}
        <header className="shrink-0 p-4 border-b">
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
        {/* STEP 4.9-β-1: ChatPanel이 flex-1로 나머지 공간 차지, 내부에서 스크롤 처리 */}
        <div className="flex-1 min-h-0">
          <ChatPanel
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            coverageGuide={coverageGuide}
            onSelectCoverage={handleSelectCoverage}
            onSelectCoverages={handleSelectCoverages}
            selectedInsurers={selectedInsurers}
            onInsurersChange={setSelectedInsurers}
            lockedCoverage={lockedCoverage}
            onUnlockCoverage={handleUnlockCoverage}
          />
        </div>
      </div>

      {/* Right: Results Panel (Query State 표시, View State 격리) */}
      {/* STEP 4.9-β-1: 우측 패널 - header 고정, 콘텐츠 영역만 스크롤 */}
      <div className="w-1/2 flex flex-col">
        {/* 헤더: shrink-0 (고정) */}
        <header className="shrink-0 p-4 border-b">
          <h2 className="text-lg font-semibold">
            {uiMode === "SINGLE_DETAIL" ? "담보 상세" : "비교 결과"}
          </h2>
        </header>
        {/* STEP 4.9-β-1: 콘텐츠 영역 - flex-1 overflow-y-auto (스크롤 책임자) */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {uiMode === "SINGLE_DETAIL" && singleDetailInfo && memoizedResponse ? (
            <SingleCoverageDetailView
              response={memoizedResponse as CompareResponseWithSubtype}
              insurerCode={singleDetailInfo.insurerCode}
              coverageCode={singleDetailInfo.coverageCode || ""}
              coverageName={singleDetailInfo.coverageName}
              onUnlock={handleUnlockCoverage}
            />
          ) : (
            <ResultsPanel response={memoizedResponse} />
          )}
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
