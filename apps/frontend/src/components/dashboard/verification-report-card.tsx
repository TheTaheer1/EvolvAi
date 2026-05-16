import { ShieldCheck } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { VerificationReport } from "@/types/verification-report";

export function VerificationReportCard({ report }: { report?: VerificationReport | null }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-cyan-300" />Verification report</CardTitle>
          {report ? <StatusBadge status={report.passed ? "completed" : "blocked"} /> : null}
        </div>
      </CardHeader>
      <CardContent>
        {!report ? (
          <EmptyState title="Verification pending" message="Safety checks run after artifact generation." />
        ) : (
          <div className="min-w-0 space-y-3">
            <p className="text-sm text-muted-foreground">{report.summary}</p>
            <div className="grid min-w-0 gap-2 lg:grid-cols-2">
              {report.checks.map((check) => (
                <div key={check.name} className="min-w-0 rounded-lg border bg-background/40 p-3">
                  <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
                    <p className="min-w-0 break-words text-sm font-medium">{check.name.replaceAll("_", " ")}</p>
                    <div className="shrink-0"><StatusBadge status={check.status} /></div>
                  </div>
                  <p className="mt-1 break-words text-xs text-muted-foreground">{check.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
