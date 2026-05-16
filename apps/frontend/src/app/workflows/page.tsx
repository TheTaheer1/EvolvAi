"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useWorkflows } from "@/hooks/use-workflows";
import { safeDate } from "@/lib/utils";

export default function WorkflowsPage() {
  const { workflows, loading, error } = useWorkflows();
  return (
    <Card>
      <CardHeader><CardTitle>Workflows</CardTitle></CardHeader>
      <CardContent>
        {loading ? <p className="text-sm text-muted-foreground">Loading workflows...</p> : null}
        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        <Table>
          <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>Status</TableHead><TableHead>Current Agent</TableHead><TableHead>Created</TableHead></TableRow></TableHeader>
          <TableBody>
            {workflows.length === 0 && !loading ? <TableRow><TableCell colSpan={4} className="text-muted-foreground">No workflows yet.</TableCell></TableRow> : null}
            {workflows.map((workflow) => (
              <TableRow key={workflow.id}>
                <TableCell><Link className="text-cyan-200 hover:underline" href={`/workflows/${workflow.id}`}>{workflow.id.slice(0, 8)}</Link></TableCell>
                <TableCell><StatusBadge status={workflow.status} /></TableCell>
                <TableCell>{workflow.current_agent || "-"}</TableCell>
                <TableCell className="text-muted-foreground">{safeDate(workflow.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
