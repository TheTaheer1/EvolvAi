"use client";

import { useEffect, useState } from "react";

import { ScoreBadge } from "@/components/shared/score-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { apiClient } from "@/lib/api-client";
import type { Decision } from "@/types/decision";

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { void apiClient.decisions().then(setDecisions).catch((err) => setError(err.message)); }, []);
  return (
    <Card>
      <CardHeader><CardTitle>Decisions</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {error ? <p className="text-red-300">{error}</p> : null}
        {decisions.length === 0 ? <p className="text-muted-foreground">No decisions yet.</p> : null}
        {decisions.map((decision) => {
          const reasoning = decision.reasoning || {};
          const risks = Array.isArray(reasoning.risks) ? reasoning.risks : [];
          return (
            <div key={decision.id} className="rounded-xl border bg-background/40 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Badge>{decision.decision_type}</Badge>
                  <p className="mt-3 font-medium">{decision.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{decision.summary}</p>
                  <p className="mt-2 text-sm text-cyan-100">{decision.recommended_action}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <ScoreBadge label="Impact" value={decision.impact_score} />
                  <ScoreBadge label="Confidence" value={decision.confidence_score} />
                </div>
              </div>
              <div className="mt-4"><Progress value={decision.impact_score * 100} /></div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-lg bg-muted/30 p-3 text-sm">
                  <p className="font-medium">Why now</p>
                  <p className="mt-1 text-muted-foreground">{String(reasoning.why_now || "Pending")}</p>
                </div>
                <div className="rounded-lg bg-muted/30 p-3 text-sm">
                  <p className="font-medium">Risks</p>
                  <p className="mt-1 text-muted-foreground">{risks.map(String).join(" ") || "No risks recorded."}</p>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
