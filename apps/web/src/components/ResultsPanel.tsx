"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { CompareTable } from "./CompareTable";
import { DiffSummary } from "./DiffSummary";
import { EvidencePanel } from "./EvidencePanel";
import { CompareResponse } from "@/lib/types";
import { ChevronDown, ChevronUp } from "lucide-react";

interface ResultsPanelProps {
  response: CompareResponse | null;
}

export function ResultsPanel({ response }: ResultsPanelProps) {
  const [debugOpen, setDebugOpen] = useState(false);

  if (!response) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <p className="text-lg">비교 결과</p>
          <p className="text-sm mt-2">질문을 입력하면 결과가 여기에 표시됩니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <Tabs defaultValue="compare" className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start rounded-none border-b bg-transparent p-0">
          <TabsTrigger
            value="compare"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Compare
          </TabsTrigger>
          <TabsTrigger
            value="diff"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Diff
          </TabsTrigger>
          <TabsTrigger
            value="evidence"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Evidence
          </TabsTrigger>
          <TabsTrigger
            value="policy"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Policy(약관)
          </TabsTrigger>
        </TabsList>

        <ScrollArea className="flex-1">
          <TabsContent value="compare" className="m-0 p-4">
            <CompareTable data={response.coverage_compare_result} />
          </TabsContent>

          <TabsContent value="diff" className="m-0 p-4">
            <DiffSummary data={response.diff_summary} />
          </TabsContent>

          <TabsContent value="evidence" className="m-0 p-4">
            <EvidencePanel data={response.compare_axis} isPolicyMode={false} />
          </TabsContent>

          <TabsContent value="policy" className="m-0 p-4">
            <EvidencePanel data={response.policy_axis} isPolicyMode={true} />
          </TabsContent>
        </ScrollArea>
      </Tabs>

      {/* Debug Section */}
      <div className="border-t">
        <Collapsible open={debugOpen} onOpenChange={setDebugOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-between rounded-none"
            >
              <span className="text-xs text-muted-foreground">Debug</span>
              {debugOpen ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronUp className="h-3 w-3" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ScrollArea className="h-[200px]">
              <pre className="p-4 text-xs bg-muted">
                {JSON.stringify(response.debug, null, 2)}
              </pre>
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
}
