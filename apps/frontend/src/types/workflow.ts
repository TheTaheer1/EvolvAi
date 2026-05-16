import type { AgentExecution } from "./agent";
import type { Decision } from "./decision";
import type { LogEntry } from "./api";
import type { PullRequestHistory } from "./pull-request";

export type WorkflowStatus =
  | "pending"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "no_action_needed";

export interface Workflow {
  id: string;
  trigger_type: string;
  trigger_source: string;
  status: WorkflowStatus | string;
  current_agent?: string | null;
  company_context?: Record<string, unknown> | null;
  input_payload: Record<string, unknown>;
  final_summary?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends Workflow {
  agent_executions: AgentExecution[];
  logs: LogEntry[];
  decisions: Decision[];
  pull_requests: PullRequestHistory[];
}

export interface TimelineItem {
  id: string;
  type: string;
  title: string;
  status?: string | null;
  timestamp: string;
  payload: Record<string, unknown>;
}
