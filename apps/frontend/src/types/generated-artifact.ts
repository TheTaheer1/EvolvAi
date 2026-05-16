export interface GeneratedArtifact {
  id: string;
  workflow_id: string;
  artifact_type: string;
  file_path: string;
  title: string;
  description?: string | null;
  content: string;
  language?: string | null;
  status: string;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}
