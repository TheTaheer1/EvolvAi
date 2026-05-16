export interface ImpactAnalysis {
  id: string;
  workflow_id: string;
  business_impact: number;
  technical_complexity: number;
  urgency: number;
  confidence: number;
  risk_score: number;
  opportunity_score: number;
  final_priority: string;
  impact_breakdown: Record<string, number>;
  recommendation?: string | null;
  created_at: string;
}
