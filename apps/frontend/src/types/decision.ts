export interface Decision {
  id: string;
  workflow_id: string;
  decision_type: string;
  title: string;
  summary?: string | null;
  impact_score: number;
  confidence_score: number;
  recommended_action?: string | null;
  reasoning?: Record<string, unknown> | null;
  created_at: string;
}
