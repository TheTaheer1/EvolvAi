export interface ExplainabilityRecord {
  id: string;
  workflow_id: string;
  agent_execution_id?: string | null;
  title: string;
  summary: string;
  reasoning_steps: string[];
  evidence: Array<Record<string, unknown>>;
  assumptions: string[];
  risks: string[];
  confidence_score: number;
  created_at: string;
}
