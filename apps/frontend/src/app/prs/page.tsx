"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/shared/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api-client";
import { safeDate } from "@/lib/utils";
import type { PullRequestHistory } from "@/types/pull-request";

export default function PRsPage() {
  const [prs, setPrs] = useState<PullRequestHistory[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { void apiClient.prs().then(setPrs).catch((err) => setError(err.message)); }, []);
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>PR Center</CardTitle>
              <p className="mt-2 text-sm text-muted-foreground">
                Review EvolvAI PR previews, verification state, and safe generated files. Real PR opening stays gated by explicit environment flags.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="success">Preview-only by default</Badge>
              <Badge variant="success">Real PR disabled</Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      <Alert className="border-emerald-400/30 bg-emerald-950/20">
        <AlertTitle>Safety posture</AlertTitle>
        <AlertDescription>
          Opening a real draft PR is an external write action and requires explicit opt-in, passing verification, safe generated artifacts, and GitHub credentials.
        </AlertDescription>
      </Alert>

      <Card>
      <CardContent className="pt-6">
        {error ? <p className="text-red-300">{error}</p> : null}
        <Table>
          <TableHeader><TableRow><TableHead>Title</TableHead><TableHead>Status</TableHead><TableHead>Generated files</TableHead><TableHead>Created</TableHead><TableHead>Workflow</TableHead></TableRow></TableHeader>
          <TableBody>
            {prs.length === 0 ? <TableRow><TableCell colSpan={5} className="text-muted-foreground">No PR previews yet. Run Reliable Demo to create one.</TableCell></TableRow> : null}
            {prs.map((pr) => (
              <TableRow key={pr.id}>
                <TableCell>
                  <p className="font-medium">{pr.title}</p>
                  <p className="break-all text-xs text-muted-foreground">{pr.branch_name}</p>
                  {pr.pr_url ? <a className="block break-all text-xs text-cyan-200" href={pr.pr_url} target="_blank" rel="noreferrer">{pr.pr_url}</a> : null}
                  <Badge variant={pr.status === "opened" ? "success" : "muted"}>{pr.status === "opened" ? "draft opened" : "preview only"}</Badge>
                  {pr.error_message ? <p className="mt-1 text-xs text-red-300">{pr.error_message}</p> : null}
                </TableCell>
                <TableCell><StatusBadge status={pr.status} /></TableCell>
                <TableCell className="max-w-md">
                  <div className="flex flex-wrap gap-1.5">
                    {(pr.changed_files || []).map((file) => <Badge key={String(file.path)} variant="muted">{String(file.path)}</Badge>)}
                  </div>
                </TableCell>
                <TableCell>{safeDate(pr.created_at)}</TableCell>
                <TableCell><Button asChild size="sm" variant="outline"><Link href={`/workflows/${pr.workflow_id}`}>Open workflow</Link></Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
    </div>
  );
}
