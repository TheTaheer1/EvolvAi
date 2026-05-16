import type { MarketEvent } from "./market-event";

export interface ExternalEventSource {
  id: string;
  source_key: string;
  source_type: string;
  display_name: string;
  enabled: boolean;
  config?: Record<string, unknown> | null;
  last_sync_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExternalEventIngestionRun {
  id: string;
  source_key: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
  events_found: number;
  events_created: number;
  events_skipped: number;
  error_message?: string | null;
  raw_summary?: Record<string, unknown> | null;
  created_at: string;
}

export interface ExternalEventRaw {
  id: string;
  source: string;
  external_id?: string | null;
  title: string;
  url?: string | null;
  raw_payload: Record<string, unknown>;
  normalized_market_event_id?: string | null;
  content_hash: string;
  created_at: string;
}

export interface LiveEventIngestResponse {
  run_id: string;
  source: string;
  status: string;
  events_found: number;
  events_created: number;
  events_skipped: number;
  market_events: MarketEvent[];
  run: ExternalEventIngestionRun;
  source_config?: ExternalEventSource | null;
  events: MarketEvent[];
  raw_events: ExternalEventRaw[];
  warnings: string[];
  workflows_triggered: string[];
}

export interface HackerNewsIngestRequest {
  feed: "top" | "new" | "best" | "show" | "ask" | "jobs";
  max_results: number;
  keywords?: string[] | null;
  min_score?: number | null;
  trigger_workflows?: boolean;
}
