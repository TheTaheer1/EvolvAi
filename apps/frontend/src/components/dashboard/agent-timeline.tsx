"use client";

import { CheckCircle2, CircleDot, Loader2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboardStore } from "@/store/dashboard-store";

const agents = ["watcher_agent", "research_agent", "strategy_agent", "planner_agent", "execution_agent", "verification_agent", "pr_agent"];

export function AgentTimeline() {
  const liveEvents = useDashboardStore((state) => state.liveEvents);
  const latest = liveEvents.find((event) => String(event.event_name).startsWith("agent."));
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Live Agent Timeline</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {agents.map((agent) => {
          const related = liveEvents.find((event) => event.agent_name === agent);
          const status = String(related?.status || (latest?.agent_name === agent ? "running" : "waiting"));
          const Icon = status === "completed" ? CheckCircle2 : status === "running" ? Loader2 : CircleDot;
          return (
            <div key={agent} className="flex items-center gap-3 rounded-xl border bg-background/40 p-3">
              <Icon className={status === "running" ? "h-4 w-4 animate-spin text-cyan-200" : "h-4 w-4 text-muted-foreground"} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{agent}</p>
                <p className="text-xs text-muted-foreground">{status}</p>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
