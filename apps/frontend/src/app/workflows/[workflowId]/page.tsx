"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AlertCircle, ShieldCheck, WifiOff } from "lucide-react";

import { CompanyProfileCard } from "@/components/dashboard/company-profile-card";
import { ExplainabilityPanel } from "@/components/dashboard/explainability-panel";
import { GeneratedArtifactsPanel } from "@/components/dashboard/generated-artifacts-panel";
import { ImpactAnalysisCard } from "@/components/dashboard/impact-analysis-card";
import { LiveAgentPipeline } from "@/components/dashboard/live-agent-pipeline";
import { LiveLogPanel } from "@/components/dashboard/live-log-panel";
import { PrPreviewCard } from "@/components/dashboard/pr-preview-card";
import { VerificationReportCard } from "@/components/dashboard/verification-report-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useSocket } from "@/hooks/use-socket";
import { apiClient } from "@/lib/api-client";
import { safeDate } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboard-store";
import { useWorkflowStore } from "@/store/workflow-store";
import type { CompanyProfile } from "@/types/company-profile";
import type { DemoScenario } from "@/types/demo-scenario";
import type { LLMInvocation } from "@/types/llm";
import type { CodebaseContext } from "@/types/repository";

export default function WorkflowDetailPage() {
  const params = useParams<{ workflowId: string }>();
  const workflowId = params.workflowId;
  useSocket(workflowId);
  const socketConnected = useDashboardStore((state) => state.socketConnected);
  const selectedWorkflow = useWorkflowStore((state) => state.selectedWorkflow);
  const setSelectedWorkflow = useWorkflowStore((state) => state.setSelectedWorkflow);
  const setWorkflowDetailData = useWorkflowStore((state) => state.setWorkflowDetailData);
  const explainabilityRecords = useWorkflowStore((state) => state.explainabilityRecords);
  const impactAnalysis = useWorkflowStore((state) => state.impactAnalysis);
  const generatedArtifacts = useWorkflowStore((state) => state.generatedArtifacts);
  const verificationReport = useWorkflowStore((state) => state.verificationReport);
  const prPreview = useWorkflowStore((state) => state.prPreview);
  const [error, setError] = useState<string | null>(null);
  const [llmInvocations, setLlmInvocations] = useState<LLMInvocation[]>([]);
  const [codebaseContext, setCodebaseContext] = useState<CodebaseContext | null>(null);

  const loadWorkflow = useCallback(async () => {
    try {
      const [workflow, explainability, impact, artifacts, verification, prPreviewData, llmData, codebaseData] = await Promise.all([
        apiClient.workflow(workflowId),
        apiClient.workflowExplainability(workflowId),
        apiClient.workflowImpactAnalysis(workflowId),
        apiClient.workflowGeneratedArtifacts(workflowId),
        apiClient.workflowVerificationReport(workflowId),
        apiClient.workflowPrPreview(workflowId),
        apiClient.workflowLLMInvocations(workflowId),
        apiClient.workflowCodebaseContext(workflowId)
      ]);
      setError(null);
      setSelectedWorkflow(workflow);
      setLlmInvocations(llmData);
      setCodebaseContext(codebaseData);
      setWorkflowDetailData({
        explainabilityRecords: explainability,
        impactAnalysis: impact,
        generatedArtifacts: artifacts,
        verificationReport: verification,
        prPreview: prPreviewData
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Workflow not found");
    }
  }, [setSelectedWorkflow, setWorkflowDetailData, workflowId]);

  useEffect(() => {
    void loadWorkflow();
  }, [loadWorkflow]);

  useEffect(() => {
    if (!selectedWorkflow || !["queued", "running", "pending"].includes(selectedWorkflow.status)) return;
    const interval = window.setInterval(() => {
      void loadWorkflow();
    }, socketConnected ? 5000 : 3000);
    return () => window.clearInterval(interval);
  }, [loadWorkflow, selectedWorkflow, socketConnected]);

  const scenario = useMemo(() => selectedWorkflow?.input_payload?.scenario as DemoScenario | undefined, [selectedWorkflow]);
  const companyProfile = useMemo(() => selectedWorkflow?.input_payload?.company_profile as CompanyProfile | undefined, [selectedWorkflow]);
  const liveEvent = Boolean(selectedWorkflow?.input_payload?.live_event);
  const triggerMarketEvent = useMemo(
    () => selectedWorkflow?.input_payload?.market_event as Record<string, unknown> | undefined,
    [selectedWorkflow]
  );
  const hasLLM = llmInvocations.some((item) => item.status === "success");
  const hasFallback = llmInvocations.some((item) => item.fallback_used);
  const llmStats = useMemo(() => {
    const successful = llmInvocations.filter((item) => item.status === "success").length;
    const fallback = llmInvocations.filter((item) => item.fallback_used).length;
    const totalTokens = llmInvocations.reduce((sum, item) => sum + (item.total_tokens || 0), 0);
    const latencies = llmInvocations.map((item) => item.latency_ms).filter((value): value is number => typeof value === "number");
    const averageLatency = latencies.length ? Math.round(latencies.reduce((sum, value) => sum + value, 0) / latencies.length) : null;
    return { successful, fallback, totalTokens, averageLatency };
  }, [llmInvocations]);
  const normalizedEvent = selectedWorkflow?.agent_executions
    ?.find((agent) => agent.agent_name === "watcher_agent")
    ?.output_state?.normalized_market_event as Record<string, unknown> | undefined;
  const triggerEvent = normalizedEvent || triggerMarketEvent;
  const decision = selectedWorkflow?.decisions?.[0];
  const plan = selectedWorkflow?.agent_executions
    ?.find((agent) => agent.agent_name === "planner_agent")
    ?.output_state?.implementation_plan as Record<string, unknown> | undefined;

  const workflowProgress =
    selectedWorkflow?.status === "completed" || selectedWorkflow?.status === "no_action_needed"
      ? 100
      : selectedWorkflow?.status === "failed" || selectedWorkflow?.status === "cancelled"
        ? 100
        : selectedWorkflow?.status === "running"
          ? 62
          : selectedWorkflow?.status === "queued"
            ? 18
            : 0;

  if (error) return <Card><CardContent className="p-6 text-red-300">{error}</CardContent></Card>;
  if (!selectedWorkflow) return <Card><CardContent className="p-6 text-muted-foreground">Loading workflow...</CardContent></Card>;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle>Workflow {selectedWorkflow.id.slice(0, 8)}</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge>{liveEvent ? "GitHub live event" : "Controlled demo"}</Badge>
            <Badge variant="success">Real PR disabled</Badge>
            <Badge variant="success">Code execution disabled</Badge>
            <Badge variant="success">Generated preview-only</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <div><p className="text-xs text-muted-foreground">Status</p><StatusBadge status={selectedWorkflow.status} /></div>
            <div><p className="text-xs text-muted-foreground">Trigger</p><p>{String(triggerEvent?.title || scenario?.title || selectedWorkflow.trigger_type)}</p></div>
            <div><p className="text-xs text-muted-foreground">Current agent</p><p>{selectedWorkflow.current_agent || "-"}</p></div>
            <div><p className="text-xs text-muted-foreground">Created</p><p>{safeDate(selectedWorkflow.created_at)}</p></div>
          </div>
          <Progress value={workflowProgress} />
          {selectedWorkflow.status === "queued" ? (
            <Alert className="border-amber-400/30 bg-amber-950/20">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Workflow queued</AlertTitle>
              <AlertDescription>Workflow is queued. Make sure the Celery worker is running.</AlertDescription>
            </Alert>
          ) : null}
          {!socketConnected ? (
            <Alert className="border-cyan-400/30 bg-cyan-950/20">
              <WifiOff className="h-4 w-4" />
              <AlertTitle>Realtime disconnected</AlertTitle>
              <AlertDescription>Realtime disconnected. Polling for updates through REST.</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Intelligence mode</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge>{liveEvent ? "Live Event" : "Controlled Demo"}</Badge>
            {hasLLM ? <Badge>LLM Enhanced</Badge> : <Badge variant="muted">Deterministic</Badge>}
            {hasFallback ? <Badge variant="warning">Fallback Used</Badge> : null}
            <Badge variant="warning">Real PR creation disabled</Badge>
          </div>
          {hasFallback ? (
            <Alert className="border-amber-400/30 bg-amber-950/20">
              <ShieldCheck className="h-4 w-4" />
              <AlertTitle>Fallback used to keep workflow reliable</AlertTitle>
              <AlertDescription>
                One or more agents used deterministic fallback because live LLM output was unavailable or invalid. This is a safe degraded mode, not a workflow failure.
              </AlertDescription>
            </Alert>
          ) : null}
          {llmInvocations.length ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-lg border bg-background/40 p-3">
                  <p className="text-xs text-muted-foreground">Total LLM calls</p>
                  <p className="text-2xl font-semibold">{llmInvocations.length}</p>
                </div>
                <div className="rounded-lg border bg-background/40 p-3">
                  <p className="text-xs text-muted-foreground">Successful</p>
                  <p className="text-2xl font-semibold">{llmStats.successful}</p>
                </div>
                <div className="rounded-lg border bg-background/40 p-3">
                  <p className="text-xs text-muted-foreground">Fallbacks</p>
                  <p className="text-2xl font-semibold">{llmStats.fallback}</p>
                </div>
                <div className="rounded-lg border bg-background/40 p-3">
                  <p className="text-xs text-muted-foreground">Tokens / latency</p>
                  <p className="text-sm font-medium">{llmStats.totalTokens || "-"} tokens</p>
                  <p className="text-xs text-muted-foreground">{llmStats.averageLatency ? `${llmStats.averageLatency}ms avg` : "Latency pending"}</p>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {llmInvocations.map((invocation) => (
                <div key={invocation.id} className="rounded-lg border bg-background/40 p-3 text-sm">
                  <p className="font-medium">{invocation.agent_name}</p>
                  <p className="text-xs text-muted-foreground">{invocation.provider} · {invocation.model}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge variant={invocation.status === "success" ? "success" : invocation.fallback_used ? "warning" : "muted"}>{invocation.status}</Badge>
                    <Badge variant={invocation.structured_output_valid ? "success" : "muted"}>{invocation.structured_output_valid ? "schema valid" : "schema fallback"}</Badge>
                    {invocation.latency_ms ? <Badge variant="muted">{invocation.latency_ms}ms</Badge> : null}
                    {invocation.total_tokens ? <Badge variant="muted">{invocation.total_tokens} tokens</Badge> : null}
                  </div>
                  {invocation.error_message ? <p className="mt-2 text-xs text-amber-200">{invocation.error_message}</p> : null}
                </div>
              ))}
              </div>
            </div>
          ) : <p className="text-sm text-muted-foreground">LLM metadata will appear after LLM-capable agents run.</p>}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <CompanyProfileCard profile={companyProfile || null} mode={liveEvent ? "Live Event Mode" : "Controlled Demo Mode"} />
        <Card>
          <CardHeader><CardTitle>Trigger event</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex flex-wrap gap-2">
              <Badge>{String(scenario?.event_type || triggerEvent?.event_type || selectedWorkflow.trigger_source || "controlled_demo")}</Badge>
              {(scenario?.tags || []).map((tag) => <Badge key={tag} variant="muted">{tag}</Badge>)}
              {typeof triggerEvent?.importance_score === "number" ? <Badge variant="muted">{Math.round(triggerEvent.importance_score * 100)}% importance</Badge> : null}
            </div>
            <p className="text-lg font-medium">{String(triggerEvent?.title || scenario?.title || "Market event")}</p>
            <p className="text-muted-foreground">{String(triggerEvent?.summary || scenario?.market_event?.summary || "")}</p>
            {typeof triggerEvent?.url === "string" ? (
              <a className="break-all text-cyan-200" href={triggerEvent.url} target="_blank" rel="noreferrer">{triggerEvent.url}</a>
            ) : null}
            <p className="text-cyan-100">{scenario?.expected_recommendation}</p>
          </CardContent>
        </Card>
      </div>

      <LiveAgentPipeline />

      {decision ? (
        <Card>
          <CardHeader><CardTitle>Strategic decision</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="md:col-span-2">
              <p className="font-medium">{decision.title}</p>
              <p className="mt-2 text-sm text-muted-foreground">{decision.summary}</p>
              <p className="mt-3 text-sm text-cyan-100">{decision.recommended_action}</p>
            </div>
            <div className="space-y-2">
              <Badge>Impact {Math.round(decision.impact_score * 100)}%</Badge>
              <Badge>Confidence {Math.round(decision.confidence_score * 100)}%</Badge>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <ImpactAnalysisCard impact={impactAnalysis} />

      <Card>
        <CardHeader><CardTitle>Research evidence and implementation plan</CardTitle></CardHeader>
        <CardContent className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-3">
            {(scenario?.research_evidence || []).map((item, index) => (
              <div key={index} className="rounded-lg border bg-background/40 p-3 text-sm">
                <p className="font-medium">{String(item.title)}</p>
                <p className="mt-1 text-muted-foreground">{String(item.summary)}</p>
              </div>
            ))}
          </div>
          <div className="rounded-lg border bg-background/40 p-4 text-sm">
            <p className="font-medium">{String(plan?.objective || scenario?.expected_recommendation || "Plan pending")}</p>
            <div className="mt-3 space-y-2 text-muted-foreground">
              {Array.isArray(plan?.tasks)
                ? (plan.tasks as Array<Record<string, unknown>>).map((task) => <p key={String(task.title)}>- {String(task.title)}</p>)
                : <p>Implementation plan pending.</p>}
            </div>
          </div>
        </CardContent>
      </Card>

      <ExplainabilityPanel records={explainabilityRecords} />
      <Card>
        <CardHeader><CardTitle>Codebase Context</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {!codebaseContext ? (
            <p className="text-sm text-muted-foreground">No repository context attached. Workflow still uses product and market context.</p>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">{codebaseContext.architecture_summary}</p>
              <div className="grid gap-3 lg:grid-cols-2">
                {codebaseContext.relevant_files.map((file) => (
                  <div key={file.id || file.path} className="rounded-lg border bg-background/40 p-3">
                    <p className="break-all font-mono text-sm text-cyan-100">{file.path}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {file.file_type || "file"} · {file.language || "unknown"} · {file.size_bytes ?? "?"} bytes
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">{file.summary}</p>
                  </div>
                ))}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border bg-background/40 p-3">
                  <p className="text-sm font-medium">Implementation hints</p>
                  <div className="mt-2 space-y-1 text-sm text-muted-foreground">
                    {codebaseContext.implementation_hints.map((hint) => <p key={hint}>- {hint}</p>)}
                  </div>
                </div>
                <div className="rounded-lg border bg-background/40 p-3">
                  <p className="text-sm font-medium">Risks</p>
                  <div className="mt-2 space-y-1 text-sm text-muted-foreground">
                    {codebaseContext.risks.map((risk) => <p key={risk}>- {risk}</p>)}
                  </div>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
      <GeneratedArtifactsPanel artifacts={generatedArtifacts} />
      <div className="grid gap-6 xl:grid-cols-2">
        <VerificationReportCard report={verificationReport} />
        <PrPreviewCard preview={prPreview} workflowId={workflowId} />
      </div>
      <LiveLogPanel />
    </div>
  );
}
