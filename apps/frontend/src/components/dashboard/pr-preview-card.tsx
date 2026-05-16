"use client";

import { GitPullRequestArrow } from "lucide-react";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";
import type { PRSafetyCheck, PullRequestHistory } from "@/types/pull-request";

export function PrPreviewCard({
  preview,
  workflowId
}: {
  preview?: PullRequestHistory | null;
  workflowId?: string;
}) {
  const targetWorkflowId = workflowId || preview?.workflow_id;
  const [safety, setSafety] = useState<PRSafetyCheck | null>(null);
  const [currentPreview, setCurrentPreview] = useState<PullRequestHistory | null | undefined>(preview);
  const [opening, setOpening] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setCurrentPreview(preview);
  }, [preview]);

  useEffect(() => {
    let cancelled = false;
    setSafety(null);
    setMessage(null);
    if (!targetWorkflowId || !preview) return;
    apiClient.workflowPrSafetyCheck(targetWorkflowId)
      .then((result) => {
        if (!cancelled) setSafety(result);
      })
      .catch((err) => {
        if (!cancelled) setMessage(err instanceof Error ? err.message : "Unable to load PR safety checks.");
      });
    return () => {
      cancelled = true;
    };
  }, [targetWorkflowId, preview]);

  async function openDraftPr() {
    if (!targetWorkflowId) return;
    setOpening(true);
    setMessage(null);
    try {
      const result = await apiClient.openWorkflowDraftPr(targetWorkflowId);
      setCurrentPreview(result);
      setMessage(result.pr_url ? "Draft PR opened safely." : "Draft PR request completed.");
      const updatedSafety = await apiClient.workflowPrSafetyCheck(targetWorkflowId);
      setSafety(updatedSafety);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Draft PR creation was blocked safely.");
    } finally {
      setOpening(false);
    }
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2"><GitPullRequestArrow className="h-5 w-5 text-cyan-300" />PR preview</CardTitle>
          <Badge variant="warning">External write action gated</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {!currentPreview ? (
          <EmptyState title="PR preview pending" message="PR Agent creates a planned or blocked preview after verification." />
        ) : (
          <div className="min-w-0 space-y-4">
            <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium">{currentPreview.title}</p>
                <p className="mt-1 break-words text-sm text-muted-foreground">{currentPreview.branch_name}</p>
                {currentPreview.pr_url ? (
                  <a className="mt-1 block break-all text-sm text-cyan-200" href={currentPreview.pr_url} target="_blank" rel="noreferrer">
                    {currentPreview.pr_url}
                  </a>
                ) : null}
              </div>
              <div className="shrink-0"><StatusBadge status={currentPreview.status} /></div>
            </div>
            <p className="text-sm text-amber-100">
              Opening a draft PR is an external write action and requires explicit backend opt-in. Generated preview artifacts only.
            </p>
            <div className="flex min-w-0 flex-wrap gap-1.5">
              {(currentPreview.changed_files || []).map((file) => <Badge key={String(file.path)} className="break-words" variant="muted">{String(file.path)}</Badge>)}
            </div>
            {safety ? (
              <div className="rounded-lg border bg-background/40 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium">Draft PR safety checklist</p>
                  <Badge variant={safety.can_open_pr ? "success" : "warning"}>{safety.can_open_pr ? "ready" : "blocked"}</Badge>
                </div>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  {safety.checks.map((check) => (
                    <div key={check.name} className="rounded-md bg-muted/30 p-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{check.name}</span>
                        <Badge variant={check.passed ? "success" : "destructive"}>{check.passed ? "passed" : "blocked"}</Badge>
                      </div>
                      <p className="mt-1 text-muted-foreground">{check.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {currentPreview.error_message ? <p className="text-sm text-red-300">{currentPreview.error_message}</p> : null}
            {message ? <p className="text-sm text-cyan-100">{message}</p> : null}
            <pre className="max-h-96 max-w-full overflow-auto rounded-lg border bg-slate-950 p-4 text-xs leading-relaxed text-slate-100">
              <code className="block min-w-0 whitespace-pre-wrap break-words">{currentPreview.description}</code>
            </pre>
            <Button
              disabled={!safety?.can_open_pr || opening || currentPreview.status === "opened"}
              variant="outline"
              onClick={() => void openDraftPr()}
            >
              {currentPreview.status === "opened" ? "Draft PR Opened" : opening ? "Opening..." : "Open Draft PR"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
