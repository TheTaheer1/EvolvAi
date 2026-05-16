import type { Decision } from "./decision";
import type { CompanyProfile } from "./company-profile";
import type { DemoScenario } from "./demo-scenario";
import type { GeneratedArtifact } from "./generated-artifact";
import type { ImpactAnalysis } from "./impact-analysis";
import type { MarketEvent } from "./market-event";
import type { PullRequestHistory } from "./pull-request";
import type { VerificationReport } from "./verification-report";
import type { Workflow } from "./workflow";

export interface LogEntry {
  id: string;
  workflow_id?: string | null;
  agent_execution_id?: string | null;
  level: string;
  message: string;
  context?: Record<string, unknown> | null;
  created_at: string;
}

export interface DashboardSummary {
  active_workflows: number;
  completed_workflows: number;
  failed_workflows: number;
  market_events: number;
  decisions: number;
  pull_requests: number;
}

export interface DashboardLiveState {
  summary: DashboardSummary;
  workflows: Workflow[];
  logs: LogEntry[];
  decisions: Decision[];
  pull_requests: PullRequestHistory[];
  market_events: MarketEvent[];
  environment: Record<string, unknown>;
}

export interface DashboardDemoState {
  company_profile: CompanyProfile;
  scenarios: DemoScenario[];
  latest_workflows: Workflow[];
  latest_live_events?: MarketEvent[];
  metrics: DashboardSummary;
  latest_impact_analysis?: ImpactAnalysis | null;
  latest_pr_preview?: PullRequestHistory | null;
  latest_verification_report?: VerificationReport | null;
  latest_generated_artifacts: GeneratedArtifact[];
  environment: Record<string, unknown>;
}

export interface LiveEvent {
  event_name: string;
  event?: string;
  event_id: string;
  emitted_at?: string;
  timestamp?: string;
  workflow_id?: string;
  [key: string]: unknown;
}
