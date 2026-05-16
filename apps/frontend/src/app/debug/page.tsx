"use client";

import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";
import { useDashboardStore } from "@/store/dashboard-store";
import type { DemoScenario } from "@/types/demo-scenario";
import type { ExternalEventIngestionRun, ExternalEventSource } from "@/types/external-event";
import type { LLMConfig, LLMInvocation } from "@/types/llm";

export default function DebugPage() {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);
  const [sources, setSources] = useState<ExternalEventSource[]>([]);
  const [runs, setRuns] = useState<ExternalEventIngestionRun[]>([]);
  const [invocations, setInvocations] = useState<LLMInvocation[]>([]);
  const [seedStatus, setSeedStatus] = useState<string>("checking");
  const events = useDashboardStore((state) => state.liveEvents);
  const connected = useDashboardStore((state) => state.socketConnected);

  useEffect(() => {
    async function load() {
      try {
        const demoState = await apiClient.demoState();
        setScenarios(demoState.scenarios);
        setSeedStatus(demoState.scenarios.length >= 4 ? "ready" : "missing");
        const [config, liveSources, liveRuns, llmInvocations] = await Promise.all([
          apiClient.llmConfig(),
          apiClient.liveEventSources(),
          apiClient.liveEventIngestionRuns(),
          apiClient.llmInvocations()
        ]);
        setLlmConfig(config);
        setSources(liveSources);
        setRuns(liveRuns);
        setInvocations(llmInvocations);
      } catch {
        setSeedStatus("unavailable");
      }
    }
    void load();
  }, []);

  async function run(check: "health" | "db" | "redis" | "chroma") {
    const response = check === "health" ? await apiClient.health() : check === "db" ? await apiClient.healthDb() : check === "redis" ? await apiClient.healthRedis() : await apiClient.healthChroma();
    setResult(response);
  }

  async function trigger(scenarioKey: string) {
    const response = await apiClient.triggerScenario(scenarioKey, "fast");
    setResult(response as unknown as Record<string, unknown>);
  }

  async function testLLM() {
    const response = await apiClient.testLLM();
    setResult(response as unknown as Record<string, unknown>);
    setInvocations(await apiClient.llmInvocations());
  }

  async function testGithub() {
    const response = await apiClient.ingestGithubEvents("AI SaaS automation stars:>500", 3, false);
    setResult(response as unknown as Record<string, unknown>);
    setRuns(await apiClient.liveEventIngestionRuns());
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>Health checks</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border p-3 text-sm">Seed data <StatusBadge status={seedStatus === "ready" ? "completed" : seedStatus} /></div>
            <div className="rounded-lg border p-3 text-sm">Socket <StatusBadge status={connected ? "completed" : "unavailable"} /></div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void run("health")}>API</Button>
            <Button variant="outline" onClick={() => void run("db")}>DB</Button>
            <Button variant="outline" onClick={() => void run("redis")}>Redis</Button>
            <Button variant="outline" onClick={() => void run("chroma")}>Chroma</Button>
          </div>
          <pre className="max-h-80 overflow-auto rounded-xl bg-black/30 p-3 text-xs">{JSON.stringify(result, null, 2)}</pre>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Manual scenario triggers</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {scenarios.length === 0 ? <p className="text-sm text-muted-foreground">No scenarios visible. Run `make seed` or call `/api/v1/dashboard/demo-state` after migrations.</p> : null}
          {scenarios.map((scenario) => (
            <div key={scenario.scenario_key} className="flex items-center justify-between gap-3 rounded-lg border p-3">
              <div>
                <p className="text-sm font-medium">{scenario.title}</p>
                <p className="text-xs text-muted-foreground">{scenario.scenario_key}</p>
              </div>
              <Button size="sm" variant="outline" onClick={() => void trigger(scenario.scenario_key)}>Trigger fast</Button>
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>LLM config</CardTitle></CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border p-3">Live AI <StatusBadge status={llmConfig?.live_ai_enabled ? "completed" : "paused"} /></div>
            <div className="rounded-lg border p-3">OpenAI key <StatusBadge status={llmConfig?.api_key_present ? "completed" : "missing"} /></div>
            <div className="rounded-lg border p-3">Model <span className="text-cyan-100">{llmConfig?.model ?? "-"}</span></div>
            <div className="rounded-lg border p-3">Fallback <StatusBadge status={llmConfig?.fallback_to_demo ? "completed" : "blocked"} /></div>
          </div>
          <Button variant="outline" onClick={() => void testLLM()}>Test LLM config</Button>
          <pre className="max-h-64 overflow-auto rounded-xl bg-black/30 p-3 text-xs">{JSON.stringify(invocations.slice(0, 5), null, 2)}</pre>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>GitHub ingestion config</CardTitle></CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            {sources.map((source) => (
              <div key={source.id} className="rounded-lg border p-3">
                <p className="font-medium">{source.display_name}</p>
                <p className="text-xs text-muted-foreground">{source.source_key}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <StatusBadge status={source.enabled ? "completed" : "paused"} />
                  <StatusBadge status={source.config?.token_present ? "completed" : "missing"} />
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" onClick={() => void testGithub()}>Test GitHub ingestion</Button>
          <pre className="max-h-64 overflow-auto rounded-xl bg-black/30 p-3 text-xs">{JSON.stringify(runs.slice(0, 5), null, 2)}</pre>
        </CardContent>
      </Card>
      <Card className="lg:col-span-2">
        <CardHeader><CardTitle>Latest raw realtime events</CardTitle></CardHeader>
        <CardContent>
          <pre className="max-h-96 overflow-auto rounded-xl bg-black/30 p-3 text-xs">{JSON.stringify(events.slice(0, 30), null, 2)}</pre>
        </CardContent>
      </Card>
    </div>
  );
}
