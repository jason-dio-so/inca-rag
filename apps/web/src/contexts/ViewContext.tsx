"use client";

/**
 * STEP 3.8: View State Context
 *
 * Query State와 완전히 분리된 View State 관리 컨텍스트.
 * Evidence/Policy/Document 열람은 이 Context를 통해서만 처리되며,
 * Query State(messages, currentResponse, anchor 등)에 영향을 주지 않습니다.
 *
 * 핵심 원칙:
 * 1. View State 변경은 Query State에 영향 없음
 * 2. 문서 열람은 Read-only 동작으로만 처리
 * 3. Query Anchor는 View 동작 중 완전 고정
 */

import React, { createContext, useContext, useState, useCallback, useMemo, ReactNode } from "react";
import { isReadOnlyEvent, validateStateChange } from "@/lib/state-isolation.config";

// =============================================================================
// View State Types
// =============================================================================

export interface ViewingDocument {
  documentId: number | string;
  page: number;
  docType?: string;
  highlightQuery?: string;
}

export interface ViewState {
  // 현재 보고 있는 문서 (null = 문서 뷰어 닫힘)
  viewingDocument: ViewingDocument | null;
  // Deep-link로 열린 문서 (별도 관리)
  deepLinkDocument: ViewingDocument | null;
  // 활성 탭
  activeTab: string;
  // 펼쳐진 섹션들
  expandedSections: Set<string>;
}

// =============================================================================
// Context Interface
// =============================================================================

interface ViewContextValue {
  // View State (읽기 전용으로 노출)
  viewState: Readonly<ViewState>;

  // View State 변경 함수들 (Query State 변경 불가)
  openDocument: (doc: ViewingDocument) => void;
  closeDocument: () => void;
  setDocumentPage: (page: number) => void;
  openDeepLinkDocument: (doc: ViewingDocument) => void;
  closeDeepLinkDocument: () => void;
  setActiveTab: (tab: string) => void;
  toggleSection: (sectionId: string) => void;

  // 디버그/검증용
  lastViewEvent: string | null;
}

// =============================================================================
// Context Creation
// =============================================================================

const ViewContext = createContext<ViewContextValue | null>(null);

// =============================================================================
// Provider Component
// =============================================================================

interface ViewProviderProps {
  children: ReactNode;
}

export function ViewProvider({ children }: ViewProviderProps) {
  // View State
  const [viewingDocument, setViewingDocument] = useState<ViewingDocument | null>(null);
  const [deepLinkDocument, setDeepLinkDocument] = useState<ViewingDocument | null>(null);
  const [activeTab, setActiveTabState] = useState<string>("slots");
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [lastViewEvent, setLastViewEvent] = useState<string | null>(null);

  // =============================================================================
  // View State Handlers (Query State 변경 불가 보장)
  // =============================================================================

  /**
   * 문서 열기 (Evidence, Policy 등)
   * - Read-only 이벤트로 Query State 변경 불가
   */
  const openDocument = useCallback((doc: ViewingDocument) => {
    const eventType = "evidence_view";
    const violation = validateStateChange(eventType, "currentResponse");

    if (violation) {
      console.warn(`[ViewContext] State isolation violation blocked: ${violation}`);
      // Query State 변경 시도는 차단되지만, View State 변경은 진행
    }

    setLastViewEvent(eventType);
    setViewingDocument(doc);
  }, []);

  /**
   * 문서 닫기
   * - Query State 변경 없이 View State만 초기화
   */
  const closeDocument = useCallback(() => {
    const eventType = "document_close";
    setLastViewEvent(eventType);
    setViewingDocument(null);
  }, []);

  /**
   * 문서 페이지 변경
   * - Query State 변경 없음
   */
  const setDocumentPage = useCallback((page: number) => {
    const eventType = "document_page_change";
    setLastViewEvent(eventType);
    setViewingDocument((prev) =>
      prev ? { ...prev, page } : null
    );
  }, []);

  /**
   * Deep-link 문서 열기
   * - URL 파라미터로부터 문서 열기
   * - Query State 변경 없음
   */
  const openDeepLinkDocument = useCallback((doc: ViewingDocument) => {
    const eventType = "document_view";
    setLastViewEvent(eventType);
    setDeepLinkDocument(doc);
  }, []);

  /**
   * Deep-link 문서 닫기
   * - Query State 변경 없음
   */
  const closeDeepLinkDocument = useCallback(() => {
    const eventType = "document_close";
    setLastViewEvent(eventType);
    setDeepLinkDocument(null);
  }, []);

  /**
   * 활성 탭 변경
   * - Query State 변경 없음
   */
  const setActiveTab = useCallback((tab: string) => {
    const eventType = "tab_change";
    setLastViewEvent(eventType);
    setActiveTabState(tab);
  }, []);

  /**
   * 섹션 토글 (accordion, collapsible 등)
   * - Query State 변경 없음
   */
  const toggleSection = useCallback((sectionId: string) => {
    const eventType = "accordion_toggle";
    setLastViewEvent(eventType);
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  }, []);

  // =============================================================================
  // Context Value (Memoized)
  // =============================================================================

  const viewState = useMemo<ViewState>(
    () => ({
      viewingDocument,
      deepLinkDocument,
      activeTab,
      expandedSections,
    }),
    [viewingDocument, deepLinkDocument, activeTab, expandedSections]
  );

  const contextValue = useMemo<ViewContextValue>(
    () => ({
      viewState,
      openDocument,
      closeDocument,
      setDocumentPage,
      openDeepLinkDocument,
      closeDeepLinkDocument,
      setActiveTab,
      toggleSection,
      lastViewEvent,
    }),
    [
      viewState,
      openDocument,
      closeDocument,
      setDocumentPage,
      openDeepLinkDocument,
      closeDeepLinkDocument,
      setActiveTab,
      toggleSection,
      lastViewEvent,
    ]
  );

  return (
    <ViewContext.Provider value={contextValue}>
      {children}
    </ViewContext.Provider>
  );
}

// =============================================================================
// Hook for consuming View Context
// =============================================================================

export function useViewContext(): ViewContextValue {
  const context = useContext(ViewContext);
  if (!context) {
    throw new Error("useViewContext must be used within a ViewProvider");
  }
  return context;
}

/**
 * Hook for checking if a document is being viewed
 * (convenience hook for components that only need to know viewing status)
 */
export function useIsViewingDocument(): boolean {
  const { viewState } = useViewContext();
  return viewState.viewingDocument !== null || viewState.deepLinkDocument !== null;
}
