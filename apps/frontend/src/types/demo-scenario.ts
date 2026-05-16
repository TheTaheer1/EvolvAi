export interface DemoScenario {
  id: string;
  scenario_key: string;
  title: string;
  description?: string | null;
  event_source: string;
  event_type: string;
  market_event: {
    title?: string;
    summary?: string;
    why_it_matters?: string;
    recommended_evolution?: string;
    importance_score?: number;
    [key: string]: unknown;
  };
  research_evidence: Array<Record<string, unknown>>;
  expected_recommendation?: string | null;
  default_impact_score: number;
  default_complexity_score: number;
  default_urgency_score: number;
  tags: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type DemoSpeed = "fast" | "normal" | "slow";
