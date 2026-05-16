export interface CompanyProfile {
  id: string;
  name: string;
  description?: string | null;
  industry?: string | null;
  product_modules: string[];
  target_users: string[];
  business_goals: string[];
  technical_stack: string[];
  competitors: string[];
  risk_tolerance: string;
  engineering_capacity: string;
  raw_profile?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}
