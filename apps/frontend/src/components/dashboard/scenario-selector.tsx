"use client";

import { Loader2, Play, Zap } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboard-store";
import type { DemoSpeed } from "@/types/demo-scenario";

export function ScenarioSelector() {
  const scenarios = useDashboardStore((state) => state.scenarios);
  const selectedScenarioKey = useDashboardStore((state) => state.selectedScenarioKey);
  const selectScenario = useDashboardStore((state) => state.selectScenario);
  const triggerScenario = useDashboardStore((state) => state.triggerScenario);
  const [speed, setSpeed] = useState<DemoSpeed>("normal");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runDemo() {
    setRunning(true);
    setError(null);
    try {
      await triggerScenario(speed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scenario trigger failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2"><Zap className="h-5 w-5 text-cyan-300" />Demo scenarios</CardTitle>
          <div className="flex rounded-lg border p-1">
            {(["fast", "normal", "slow"] as DemoSpeed[]).map((item) => (
              <button
                key={item}
                className={cn("rounded-md px-3 py-1 text-xs", speed === item ? "bg-cyan-400 text-slate-950" : "text-muted-foreground")}
                onClick={() => setSpeed(item)}
                type="button"
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {scenarios.length === 0 ? (
          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No scenarios found. Run `make seed` or open the debug page after the backend starts.</div>
        ) : (
          <div className="grid min-w-0 gap-3 md:grid-cols-2">
            {scenarios.map((scenario) => {
              const selected = scenario.scenario_key === selectedScenarioKey;
              return (
                <button
                  key={scenario.scenario_key}
                  type="button"
                  onClick={() => selectScenario(scenario.scenario_key)}
                  className={cn(
                    "min-w-0 rounded-lg border p-4 text-left transition hover:border-cyan-300/70",
                    selected ? "border-cyan-300 bg-cyan-300/10" : "border-border bg-background/40"
                  )}
                >
                  <div className="flex min-w-0 flex-col gap-3">
                    <div className="min-w-0">
                      <p className="text-wrap text-base font-medium leading-snug">{scenario.title}</p>
                      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{scenario.market_event.summary || scenario.description}</p>
                    </div>
                    <Badge className="w-fit max-w-full break-words" variant={selected ? "default" : "muted"}>{scenario.event_type}</Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {scenario.tags.slice(0, 4).map((tag) => <Badge key={tag} variant="muted">{tag}</Badge>)}
                  </div>
                  <p className="mt-3 break-words text-xs text-cyan-100/80">{scenario.expected_recommendation}</p>
                </button>
              );
            })}
          </div>
        )}
        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        <Button className="w-full gap-2" onClick={() => void runDemo()} disabled={running || scenarios.length === 0}>
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Run Demo Workflow
        </Button>
      </CardContent>
    </Card>
  );
}
