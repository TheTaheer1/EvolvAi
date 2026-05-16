import { create } from "zustand";

import type { DashboardSummary, LiveEvent, LogEntry } from "@/types/api";
import { apiClient } from "@/lib/api-client";
import type { CompanyProfile } from "@/types/company-profile";
import type { Decision } from "@/types/decision";
import type { DemoScenario, DemoSpeed } from "@/types/demo-scenario";
import type { ExplainabilityRecord } from "@/types/explainability";
import type { GeneratedArtifact } from "@/types/generated-artifact";
import type { ImpactAnalysis } from "@/types/impact-analysis";
import type { MarketEvent } from "@/types/market-event";
import type { PullRequestHistory } from "@/types/pull-request";
import type { VerificationReport } from "@/types/verification-report";
import type { Workflow } from "@/types/workflow";

const emptyMetrics: DashboardSummary = {
  active_workflows: 0,
  completed_workflows: 0,
  failed_workflows: 0,
  market_events: 0,
  decisions: 0,
  pull_requests: 0
};

function upsertById<T extends { id: string }>(items: T[], next: T) {
  const index = items.findIndex((item) => item.id === next.id);
  if (index === -1) return [next, ...items].slice(0, 100);
  return items.map((item) => (item.id === next.id ? { ...item, ...next } : item));
}

interface DashboardStore {
  socketConnected: boolean;
  metrics: DashboardSummary;
  liveEvents: LiveEvent[];
  companyProfile: CompanyProfile | null;
  scenarios: DemoScenario[];
  selectedScenarioKey: string | null;
  activeWorkflow: Workflow | null;
  latestArtifacts: GeneratedArtifact[];
  latestImpactAnalysis: ImpactAnalysis | null;
  latestPRPreview: PullRequestHistory | null;
  verificationReport: VerificationReport | null;
  explainabilityRecords: ExplainabilityRecord[];
  workflows: Workflow[];
  logs: LogEntry[];
  decisions: Decision[];
  pullRequests: PullRequestHistory[];
  marketEvents: MarketEvent[];
  environment: Record<string, unknown>;
  setSocketConnected: (connected: boolean) => void;
  setMetrics: (metrics: DashboardSummary) => void;
  setScenarios: (scenarios: DemoScenario[]) => void;
  selectScenario: (scenarioKey: string) => void;
  triggerScenario: (demoSpeed?: DemoSpeed) => Promise<Workflow>;
  addRealtimeEvent: (event: LiveEvent) => void;
  upsertWorkflow: (workflow: Workflow) => void;
  addArtifact: (artifact: GeneratedArtifact) => void;
  setImpactAnalysis: (impact: ImpactAnalysis | null) => void;
  setVerificationReport: (report: VerificationReport | null) => void;
  setPRPreview: (preview: PullRequestHistory | null) => void;
  setLiveState: (state: Partial<DashboardStore>) => void;
  addEvent: (event: LiveEvent) => void;
}

export const useDashboardStore = create<DashboardStore>((set, get) => ({
  socketConnected: false,
  metrics: emptyMetrics,
  liveEvents: [],
  companyProfile: null,
  scenarios: [],
  selectedScenarioKey: null,
  activeWorkflow: null,
  latestArtifacts: [],
  latestImpactAnalysis: null,
  latestPRPreview: null,
  verificationReport: null,
  explainabilityRecords: [],
  workflows: [],
  logs: [],
  decisions: [],
  pullRequests: [],
  marketEvents: [],
  environment: {},
  setSocketConnected: (connected) => set({ socketConnected: connected }),
  setMetrics: (metrics) => set({ metrics }),
  setScenarios: (scenarios) =>
    set((state) => ({
      scenarios,
      selectedScenarioKey: state.selectedScenarioKey ?? scenarios[0]?.scenario_key ?? null
    })),
  selectScenario: (scenarioKey) => set({ selectedScenarioKey: scenarioKey }),
  triggerScenario: async (demoSpeed = "normal") => {
    const scenarioKey = get().selectedScenarioKey || get().scenarios[0]?.scenario_key;
    if (!scenarioKey) throw new Error("No demo scenario selected");
    const workflow = await apiClient.triggerScenario(scenarioKey, demoSpeed);
    set((state) => ({
      activeWorkflow: workflow,
      workflows: upsertById(state.workflows, workflow)
    }));
    return workflow;
  },
  addRealtimeEvent: (event) => get().addEvent(event),
  upsertWorkflow: (workflow) => set((state) => ({ workflows: upsertById(state.workflows, workflow), activeWorkflow: workflow })),
  addArtifact: (artifact) =>
    set((state) => ({ latestArtifacts: upsertById(state.latestArtifacts, artifact).slice(0, 10) })),
  setImpactAnalysis: (impact) => set({ latestImpactAnalysis: impact }),
  setVerificationReport: (report) => set({ verificationReport: report }),
  setPRPreview: (preview) => set({ latestPRPreview: preview }),
  setLiveState: (state) => set(state),
  addEvent: (event) => {
    if (!event || typeof event !== "object") return;
    const eventId = String(event.event_id || `${event.event_name}:${event.id || Date.now()}`);
    if (get().liveEvents.some((item) => item.event_id === eventId)) return;
    const normalized = { ...event, event_id: eventId } as LiveEvent;
    set((state) => {
      const next: Partial<DashboardStore> = {
        liveEvents: [normalized, ...state.liveEvents].slice(0, 150)
      };
      if (String(event.event_name).startsWith("workflow.") && typeof event.id === "string") {
        next.workflows = upsertById(state.workflows, event as unknown as Workflow);
        next.activeWorkflow = event as unknown as Workflow;
      }
      if (event.event_name === "log.created" && typeof event.id === "string") {
        next.logs = upsertById(state.logs, event as unknown as LogEntry).slice(0, 80);
      }
      if (event.event_name === "decision.created" && typeof event.id === "string") {
        next.decisions = upsertById(state.decisions, event as unknown as Decision);
      }
      if (event.event_name === "pr.created" && typeof event.id === "string") {
        next.pullRequests = upsertById(state.pullRequests, event as unknown as PullRequestHistory);
        next.latestPRPreview = event as unknown as PullRequestHistory;
      }
      if (event.event_name === "pr.preview.created" && typeof event.id === "string") {
        next.latestPRPreview = event as unknown as PullRequestHistory;
      }
      if ((event.event_name === "market_event.created" || event.event_name === "live_event.created") && typeof event.id === "string") {
        next.marketEvents = upsertById(state.marketEvents, event as unknown as MarketEvent);
      }
      if (event.event_name === "artifact.generated" && typeof event.id === "string") {
        next.latestArtifacts = upsertById(state.latestArtifacts, event as unknown as GeneratedArtifact).slice(0, 10);
      }
      if (event.event_name === "impact.created" && typeof event.id === "string") {
        next.latestImpactAnalysis = event as unknown as ImpactAnalysis;
      }
      if (event.event_name === "verification.completed" && typeof event.id === "string") {
        next.verificationReport = event as unknown as VerificationReport;
      }
      if (event.event_name === "explainability.created" && typeof event.id === "string") {
        next.explainabilityRecords = upsertById(
          state.explainabilityRecords,
          event as unknown as ExplainabilityRecord
        );
      }
      return next;
    });
  }
}));
