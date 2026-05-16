export interface LLMInvocation {
  id: string;
  workflow_id?: string | null;
  agent_execution_id?: string | null;
  agent_name?: string | null;
  provider: string;
  model: string;
  mode: string;
  prompt_hash?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
  status: string;
  error_message?: string | null;
  latency_ms?: number | null;
  fallback_used: boolean;
  structured_output_valid: boolean;
  created_at: string;
}

export interface LLMConfig {
  live_ai_enabled: boolean;
  api_key_present: boolean;
  provider: string;
  model: string;
  reasoning_model: string;
  structured_outputs_enabled: boolean;
  fallback_to_demo: boolean;
  cache_enabled: boolean;
  prompt_logging_enabled: boolean;
  response_logging_enabled: boolean;
}

export interface LLMTestResponse {
  enabled: boolean;
  fallback_used: boolean;
  status: string;
  provider: string;
  model: string;
  message: string;
  latency_ms?: number | null;
}
