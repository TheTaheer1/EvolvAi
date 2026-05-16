export interface MarketEvent {
  id: string;
  source: string;
  event_type: string;
  title: string;
  summary?: string | null;
  url?: string | null;
  company_name?: string | null;
  competitor_name?: string | null;
  importance_score: number;
  raw_payload?: Record<string, unknown> | null;
  detected_at: string;
  created_at: string;
}
