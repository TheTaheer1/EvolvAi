"use client";

import { useCallback, useEffect, useState } from "react";

import { ScoreBadge } from "@/components/shared/score-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api-client";
import { safeDate } from "@/lib/utils";
import type { MarketEvent } from "@/types/market-event";

export default function MarketEventsPage() {
  const [events, setEvents] = useState<MarketEvent[]>([]);
  const [tab, setTab] = useState<"controlled" | "live">("controlled");
  const [query, setQuery] = useState("AI SaaS automation stars:>500");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadEvents = useCallback(async () => {
    setError(null);
    const source = tab === "controlled" ? "controlled_demo" : "github";
    try {
      setEvents(await apiClient.marketEvents(source));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load market events");
    }
  }, [tab]);

  useEffect(() => { void loadEvents(); }, [loadEvents]);

  async function ingestGithub() {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const response = await apiClient.ingestGithubEvents(query, 10, false);
      setMessage(`Ingestion ${response.run.status}: ${response.run.events_created} created, ${response.run.events_skipped} skipped.`);
      setTab("live");
      await loadEvents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "GitHub ingestion failed safely");
    } finally {
      setLoading(false);
    }
  }

  async function triggerWorkflow(eventId: string) {
    setMessage(null);
    setError(null);
    try {
      const workflow = await apiClient.triggerWorkflowFromMarketEvent(eventId);
      setMessage(`Queued workflow ${workflow.id.slice(0, 8)} from market event.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to trigger workflow");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Market Events</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant={tab === "controlled" ? "default" : "outline"} onClick={() => setTab("controlled")}>Controlled Demo Events</Button>
          <Button size="sm" variant={tab === "live" ? "default" : "outline"} onClick={() => setTab("live")}>Live External Events</Button>
        </div>
        {tab === "live" ? (
          <div className="grid gap-3 rounded-xl border bg-background/40 p-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <Input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="GitHub ingestion query" />
            <Button onClick={() => void ingestGithub()} disabled={loading}>{loading ? "Ingesting..." : "Ingest GitHub Signals"}</Button>
          </div>
        ) : null}
        {message ? <p className="text-sm text-cyan-100">{message}</p> : null}
        {error ? <p className="text-red-300">{error}</p> : null}
        {events.length === 0 ? <p className="text-muted-foreground">{tab === "live" ? "No live events yet. Try ingesting GitHub signals." : "No controlled demo events yet."}</p> : null}
        {events.map((event) => {
          const tags = Array.isArray(event.raw_payload?.tags) ? event.raw_payload.tags as string[] : [];
          const scenarioKey = String(event.raw_payload?.scenario_key || "");
          const workflowId = String(event.raw_payload?.workflow_id || "");
          return (
            <div key={event.id} className="rounded-xl border bg-background/40 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="mb-2 flex flex-wrap gap-2">
                    <Badge>{event.source === "controlled_demo" ? "controlled demo event" : event.source}</Badge>
                    <Badge variant="muted">{event.event_type}</Badge>
                    {scenarioKey ? <Badge variant="muted">{scenarioKey}</Badge> : null}
                  </div>
                  <p className="font-medium">{event.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{event.summary}</p>
                </div>
                <ScoreBadge label="Importance" value={event.importance_score} />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {tags.map((tag) => <Badge key={tag} variant="muted">{tag}</Badge>)}
                <span className="text-xs text-cyan-200">{safeDate(event.created_at)}</span>
                {workflowId ? <span className="text-xs text-muted-foreground">workflow {workflowId.slice(0, 8)}</span> : null}
                {event.url ? <Button asChild size="sm" variant="outline"><a href={event.url} target="_blank" rel="noreferrer">Open source</a></Button> : null}
                <Button size="sm" onClick={() => void triggerWorkflow(event.id)}>Trigger Workflow</Button>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
