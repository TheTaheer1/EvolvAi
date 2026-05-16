export interface AgentExecution {
  id: string;
  workflow_id: string;
  agent_name: string;
  status: string;
  input_state?: Record<string, unknown> | null;
  output_state?: Record<string, unknown> | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  created_at: string;
}

export interface AgentDefinition {
  name: string;
  description: string;
}
