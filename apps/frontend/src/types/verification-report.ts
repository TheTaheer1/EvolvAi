export interface VerificationReport {
  id: string;
  workflow_id: string;
  status: string;
  passed: boolean;
  checks: Array<{ name: string; status: string; message: string; [key: string]: unknown }>;
  warnings: Array<Record<string, unknown> | string>;
  errors: Array<Record<string, unknown> | string>;
  summary?: string | null;
  created_at: string;
}
