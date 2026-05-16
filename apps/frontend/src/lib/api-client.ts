import axios from "axios";

import { API_URL } from "./constants";
import type { AgentDefinition, AgentExecution } from "@/types/agent";
import type { DashboardDemoState, DashboardLiveState, DashboardSummary, LogEntry } from "@/types/api";
import type { CompanyProfile } from "@/types/company-profile";
import type { Decision } from "@/types/decision";
import type { DemoScenario, DemoSpeed } from "@/types/demo-scenario";
import type { ExplainabilityRecord } from "@/types/explainability";
import type { ExternalEventIngestionRun, ExternalEventRaw, ExternalEventSource, HackerNewsIngestRequest, LiveEventIngestResponse } from "@/types/external-event";
import type { GeneratedArtifact } from "@/types/generated-artifact";
import type { ImpactAnalysis } from "@/types/impact-analysis";
import type { LLMConfig, LLMInvocation, LLMTestResponse } from "@/types/llm";
import type { MarketEvent } from "@/types/market-event";
import type { PRSafetyCheck, PullRequestHistory } from "@/types/pull-request";
import type { CodebaseContext, RepositoryAnalysis } from "@/types/repository";
import type { VerificationReport } from "@/types/verification-report";
import type { TimelineItem, Workflow, WorkflowDetail } from "@/types/workflow";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: { "Content-Type": "application/json" }
});

function friendlyError(error: unknown) {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message || "Backend request failed";
  }
  return "Unexpected frontend request error";
}

async function request<T>(promise: Promise<{ data: T }>): Promise<T> {
  try {
    const response = await promise;
    return response.data;
  } catch (error) {
    throw new Error(String(friendlyError(error)));
  }
}

export const apiClient = {
  health: () => request<Record<string, string>>(api.get("/health")),
  healthDb: () => request<Record<string, string>>(api.get("/health/db")),
  healthRedis: () => request<Record<string, string>>(api.get("/health/redis")),
  healthChroma: () => request<Record<string, string>>(api.get("/health/chroma")),
  liveState: () => request<DashboardLiveState>(api.get("/dashboard/live-state")),
  demoState: () => request<DashboardDemoState>(api.get("/dashboard/demo-state")),
  summary: () => request<DashboardSummary>(api.get("/dashboard/summary")),
  companyProfileDefault: () => request<CompanyProfile>(api.get("/company-profile/default")),
  companyProfiles: () => request<CompanyProfile[]>(api.get("/company-profiles")),
  demoScenarios: () => request<DemoScenario[]>(api.get("/demo/scenarios")),
  demoScenario: (scenarioKey: string) => request<DemoScenario>(api.get(`/demo/scenarios/${scenarioKey}`)),
  triggerScenario: (scenarioKey: string, demoSpeed: DemoSpeed = "normal") =>
    request<Workflow>(api.post(`/demo/scenarios/${scenarioKey}/trigger`, { demo_speed: demoSpeed })),
  triggerWorkflow: () =>
    request<Workflow>(
      api.post("/workflows/trigger", {
        trigger_type: "manual",
        source: "dashboard",
        payload: {
          company: "Demo SaaS",
          event: "Competitor launched AI automation feature"
        }
      })
    ),
  triggerDemoWebhook: () => request<{ workflow_id: string }>(api.post("/webhooks/demo-trigger")),
  workflows: (limit = 50) => request<Workflow[]>(api.get(`/workflows?limit=${limit}`)),
  workflow: (workflowId: string) => request<WorkflowDetail>(api.get(`/workflows/${workflowId}`)),
  workflowTimeline: (workflowId: string) => request<TimelineItem[]>(api.get(`/workflows/${workflowId}/timeline`)),
  workflowExplainability: (workflowId: string) =>
    request<ExplainabilityRecord[]>(api.get(`/workflows/${workflowId}/explainability`)),
  workflowImpactAnalysis: (workflowId: string) =>
    request<ImpactAnalysis | null>(api.get(`/workflows/${workflowId}/impact-analysis`)),
  workflowGeneratedArtifacts: (workflowId: string) =>
    request<GeneratedArtifact[]>(api.get(`/workflows/${workflowId}/generated-artifacts`)),
  workflowVerificationReport: (workflowId: string) =>
    request<VerificationReport | null>(api.get(`/workflows/${workflowId}/verification-report`)),
  workflowPrPreview: (workflowId: string) => request<PullRequestHistory | null>(api.get(`/workflows/${workflowId}/pr-preview`)),
  workflowPrSafetyCheck: (workflowId: string) =>
    request<PRSafetyCheck>(api.get(`/workflows/${workflowId}/pr-safety-check`)),
  openWorkflowDraftPr: (workflowId: string) =>
    request<PullRequestHistory>(api.post(`/workflows/${workflowId}/open-draft-pr`)),
  workflowCodebaseContext: (workflowId: string) =>
    request<CodebaseContext | null>(api.get(`/workflows/${workflowId}/codebase-context`)),
  workflowLLMInvocations: (workflowId: string) =>
    request<LLMInvocation[]>(api.get(`/llm/invocations?workflow_id=${workflowId}`)),
  regeneratePrPreview: (workflowId: string) =>
    request<PullRequestHistory>(api.post(`/workflows/${workflowId}/pr-preview/regenerate`)),
  generatedArtifact: (artifactId: string) => request<GeneratedArtifact>(api.get(`/generated-artifacts/${artifactId}`)),
  workflowAgents: (workflowId: string) => request<AgentExecution[]>(api.get(`/workflows/${workflowId}/agents`)),
  agents: () => request<AgentDefinition[]>(api.get("/agents")),
  logs: () => request<LogEntry[]>(api.get("/logs")),
  marketEvents: (source?: string, eventType?: string) => {
    const params = new URLSearchParams();
    if (source) params.set("source", source);
    if (eventType) params.set("event_type", eventType);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request<MarketEvent[]>(api.get(`/market-events${suffix}`));
  },
  triggerWorkflowFromMarketEvent: (eventId: string) => request<Workflow>(api.post(`/market-events/${eventId}/trigger-workflow`)),
  liveEventSources: () => request<ExternalEventSource[]>(api.get("/live-events/sources")),
  ingestGithubEvents: (query: string, maxResults = 10, triggerWorkflows = false) =>
    request<LiveEventIngestResponse>(
      api.post("/live-events/ingest/github", {
        query,
        max_results: maxResults,
        trigger_workflows: triggerWorkflows
      })
    ),
  ingestHackerNewsEvents: (payload: HackerNewsIngestRequest) =>
    request<LiveEventIngestResponse>(api.post("/live-events/ingest/hacker-news", payload)),
  liveEventIngestionRuns: (source?: string) => {
    const suffix = source ? `?source=${encodeURIComponent(source)}` : "";
    return request<ExternalEventIngestionRun[]>(api.get(`/live-events/ingestion-runs${suffix}`));
  },
  liveEventRaw: (source?: string) => {
    const suffix = source ? `?source=${encodeURIComponent(source)}` : "";
    return request<ExternalEventRaw[]>(api.get(`/live-events/raw${suffix}`));
  },
  analyzeRepository: (owner: string, repo: string, branch = "main") =>
    request<RepositoryAnalysis>(api.post("/repositories/analyze", { owner, repo, branch })),
  repositoryAnalyses: (limit = 25) => request<RepositoryAnalysis[]>(api.get(`/repositories/analyses?limit=${limit}`)),
  repositoryAnalysis: (analysisId: string) =>
    request<RepositoryAnalysis>(api.get(`/repositories/analyses/${analysisId}`)),
  attachRepositoryAnalysis: (analysisId: string, workflowId: string) =>
    request<CodebaseContext>(api.post(`/repositories/analyses/${analysisId}/attach-to-workflow/${workflowId}`)),
  llmConfig: () => request<LLMConfig>(api.get("/llm/config")),
  llmInvocations: () => request<LLMInvocation[]>(api.get("/llm/invocations")),
  testLLM: () => request<LLMTestResponse>(api.post("/llm/test")),
  decisions: () => request<Decision[]>(api.get("/decisions")),
  prs: () => request<PullRequestHistory[]>(api.get("/prs"))
};
