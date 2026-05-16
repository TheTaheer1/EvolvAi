export interface PullRequestHistory {
  id: string;
  workflow_id: string;
  repo_owner?: string | null;
  repo_name?: string | null;
  branch_name?: string | null;
  pr_number?: number | null;
  pr_url?: string | null;
  status: string;
  title: string;
  description?: string | null;
  changed_files?: Array<Record<string, unknown>> | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PRSafetyCheck {
  can_open_pr: boolean;
  workflow_id: string;
  pr_preview_id?: string | null;
  existing_pr_url?: string | null;
  prepared_files: Array<{
    path: string;
    original_path: string;
    artifact_type: string;
  }>;
  checks: Array<{
    name: string;
    passed: boolean;
    message: string;
  }>;
}
