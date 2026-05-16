import { create } from "zustand";

import type { AgentExecution } from "@/types/agent";
import type { LogEntry } from "@/types/api";
import type { Decision } from "@/types/decision";
import type { ExplainabilityRecord } from "@/types/explainability";
import type { GeneratedArtifact } from "@/types/generated-artifact";
import type { ImpactAnalysis } from "@/types/impact-analysis";
import type { PullRequestHistory } from "@/types/pull-request";
import type { VerificationReport } from "@/types/verification-report";
import type { Workflow, WorkflowDetail } from "@/types/workflow";

function upsertById<T extends { id: string }>(items: T[], next: T) {
  const index = items.findIndex((item) => item.id === next.id);
  if (index === -1) return [next, ...items];
  return items.map((item) => (item.id === next.id ? { ...item, ...next } : item));
}

interface WorkflowStore {
  workflows: Workflow[];
  selectedWorkflow: WorkflowDetail | null;
  agentExecutions: AgentExecution[];
  logs: LogEntry[];
  decisions: Decision[];
  explainabilityRecords: ExplainabilityRecord[];
  impactAnalysis: ImpactAnalysis | null;
  generatedArtifacts: GeneratedArtifact[];
  verificationReport: VerificationReport | null;
  prPreview: PullRequestHistory | null;
  setWorkflows: (workflows: Workflow[]) => void;
  setSelectedWorkflow: (workflow: WorkflowDetail | null) => void;
  setWorkflowDetailData: (data: Partial<WorkflowStore>) => void;
  upsertWorkflow: (workflow: Workflow) => void;
  upsertAgentExecution: (agentExecution: AgentExecution) => void;
  addLog: (log: LogEntry) => void;
  addArtifact: (artifact: GeneratedArtifact) => void;
  setImpactAnalysis: (impact: ImpactAnalysis | null) => void;
  setVerificationReport: (report: VerificationReport | null) => void;
  setPRPreview: (preview: PullRequestHistory | null) => void;
  updateWorkflowFromEvent: (event: Partial<Workflow> & { id?: string }) => void;
}

export const useWorkflowStore = create<WorkflowStore>((set) => ({
  workflows: [],
  selectedWorkflow: null,
  agentExecutions: [],
  logs: [],
  decisions: [],
  explainabilityRecords: [],
  impactAnalysis: null,
  generatedArtifacts: [],
  verificationReport: null,
  prPreview: null,
  setWorkflows: (workflows) => set({ workflows }),
  setSelectedWorkflow: (workflow) =>
    set({
      selectedWorkflow: workflow,
      agentExecutions: workflow?.agent_executions ?? [],
      logs: workflow?.logs ?? [],
      decisions: workflow?.decisions ?? [],
      prPreview: workflow?.pull_requests?.[0] ?? null
    }),
  setWorkflowDetailData: (data) => set(data),
  upsertWorkflow: (workflow) =>
    set((state) => ({
      workflows: upsertById(state.workflows, workflow),
      selectedWorkflow:
        state.selectedWorkflow?.id === workflow.id ? ({ ...state.selectedWorkflow, ...workflow } as WorkflowDetail) : state.selectedWorkflow
    })),
  upsertAgentExecution: (agentExecution) =>
    set((state) => ({
      agentExecutions: upsertById(state.agentExecutions, agentExecution)
    })),
  addLog: (log) => set((state) => ({ logs: upsertById(state.logs, log) })),
  addArtifact: (artifact) =>
    set((state) => ({ generatedArtifacts: upsertById(state.generatedArtifacts, artifact) })),
  setImpactAnalysis: (impact) => set({ impactAnalysis: impact }),
  setVerificationReport: (report) => set({ verificationReport: report }),
  setPRPreview: (preview) => set({ prPreview: preview }),
  updateWorkflowFromEvent: (event) => {
    if (!event.id) return;
    set((state) => ({
      workflows: upsertById(state.workflows, event as Workflow),
      selectedWorkflow:
        state.selectedWorkflow?.id === event.id
          ? ({ ...state.selectedWorkflow, ...event } as WorkflowDetail)
          : state.selectedWorkflow
    }));
  }
}));
