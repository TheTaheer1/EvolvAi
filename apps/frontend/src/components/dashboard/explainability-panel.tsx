import { BrainCircuit } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { ScoreBadge } from "@/components/shared/score-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExplainabilityRecord } from "@/types/explainability";

export function ExplainabilityPanel({ records }: { records: ExplainabilityRecord[] }) {
  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2"><BrainCircuit className="h-5 w-5 text-cyan-300" />Explainability</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {records.length === 0 ? <EmptyState title="Explainability pending" message="Agent reasoning will appear as the workflow runs." /> : null}
        {records.map((record) => (
          <div key={record.id} className="rounded-lg border bg-background/40 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-medium">{record.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{record.summary}</p>
              </div>
              <ScoreBadge label="Confidence" value={record.confidence_score} />
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Reasoning</p>
                <ul className="space-y-1 text-sm text-slate-200">
                  {record.reasoning_steps.map((step) => <li key={step}>- {step}</li>)}
                </ul>
              </div>
              <div>
                <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Evidence</p>
                <div className="space-y-2 text-sm">
                  {record.evidence.slice(0, 4).map((item, index) => (
                    <div key={`${record.id}-${index}`} className="rounded-md bg-muted/40 p-2">
                      <span className="text-muted-foreground">{String(item.label || item.title || "Evidence")}: </span>
                      <span>{String(item.value || item.summary || "")}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Assumptions</p>
                <p className="text-sm text-muted-foreground">{record.assumptions.join(" ")}</p>
              </div>
              <div>
                <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Risks</p>
                <p className="text-sm text-muted-foreground">{record.risks.join(" ")}</p>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
