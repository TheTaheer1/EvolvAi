"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, formatStatus } from "@/lib/utils";
import { useWorkflowStore } from "@/store/workflow-store";

const agents = [
  { key: "watcher_agent", label: "Watcher" },
  { key: "research_agent", label: "Research" },
  { key: "strategy_agent", label: "Strategy" },
  { key: "planner_agent", label: "Planning" },
  { key: "execution_agent", label: "Execution" },
  { key: "verification_agent", label: "Verification" },
  { key: "pr_agent", label: "PR Preview" }
];

function iconFor(status: string) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4 text-emerald-300" />;
  if (status === "running") return <Loader2 className="h-4 w-4 animate-spin text-cyan-300" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-red-300" />;
  return <Circle className="h-4 w-4 text-muted-foreground" />;
}

function llmMetaFor(outputState: Record<string, unknown> | null | undefined, agentKey: string) {
  const byAgent = outputState?.llm_metadata_by_agent as Record<string, Record<string, unknown>> | undefined;
  return byAgent?.[agentKey];
}

function modeLabel(mode?: string) {
  if (mode === "llm_enhanced") return "LLM Enhanced";
  if (mode === "fallback_used") return "Fallback Used";
  return "Deterministic";
}

export function LiveAgentPipeline() {
  const executions = useWorkflowStore((state) => state.agentExecutions);

  return (
    <Card>
      <CardHeader><CardTitle>Live agent orchestration</CardTitle></CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-7">
          {agents.map((agent, index) => {
            const execution = executions.find((item) => item.agent_name === agent.key);
            const status = execution?.status || "pending";
            const meta = llmMetaFor(execution?.output_state, agent.key);
            const mode = String(execution?.output_state?.output_mode || meta?.mode || "deterministic");
            const provider = meta?.provider ? String(meta.provider) : null;
            const model = meta?.model ? String(meta.model) : null;
            return (
              <div key={agent.key} className="relative">
                {index < agents.length - 1 ? <div className="absolute left-1/2 top-5 hidden h-px w-full bg-border md:block" /> : null}
                <div className={cn("relative z-10 rounded-lg border bg-background p-3", status === "running" && "border-cyan-300 bg-cyan-300/10")}>
                  <div className="flex items-center gap-2">
                    {iconFor(status)}
                    <span className="text-sm font-medium">{agent.label}</span>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{formatStatus(status)}</p>
                  {status !== "pending" ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                      <Badge variant={mode === "llm_enhanced" ? "success" : mode === "fallback_used" ? "warning" : "muted"}>
                        {modeLabel(mode)}
                      </Badge>
                      {provider ? <Badge variant="muted">{provider}</Badge> : null}
                      {model ? <span className="line-clamp-1 text-[10px] text-muted-foreground">{model}</span> : null}
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
