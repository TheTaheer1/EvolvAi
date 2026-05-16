export interface RepositoryFile {
  id: string;
  analysis_id: string;
  path: string;
  file_type?: string | null;
  language?: string | null;
  size_bytes?: number | null;
  sha?: string | null;
  importance_score: number;
  summary?: string | null;
  raw_metadata?: Record<string, unknown> | null;
  created_at: string;
}

export interface RepositoryAnalysis {
  id: string;
  owner: string;
  repo: string;
  branch: string;
  status: string;
  repo_url?: string | null;
  default_branch?: string | null;
  detected_stack: string[];
  file_count: number;
  analyzed_file_count: number;
  summary?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  files?: RepositoryFile[];
}

export interface CodebaseContext {
  id: string;
  workflow_id?: string | null;
  analysis_id: string;
  relevant_files: Array<{
    id?: string;
    path: string;
    file_type?: string | null;
    language?: string | null;
    size_bytes?: number | null;
    importance_score?: number | null;
    summary?: string | null;
  }>;
  architecture_summary?: string | null;
  implementation_hints: string[];
  risks: string[];
  created_at: string;
}
