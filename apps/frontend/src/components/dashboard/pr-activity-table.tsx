"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { safeDate } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboard-store";

export function PrActivityTable() {
  const prs = useDashboardStore((state) => state.pullRequests);
  return (
    <Card>
      <CardHeader>
        <CardTitle>PR Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow><TableHead>Title</TableHead><TableHead>Status</TableHead><TableHead>Created</TableHead></TableRow>
          </TableHeader>
          <TableBody>
            {prs.length === 0 ? <TableRow><TableCell colSpan={3} className="text-muted-foreground">No PR intents yet.</TableCell></TableRow> : null}
            {prs.map((pr) => (
              <TableRow key={pr.id}>
                <TableCell className="font-medium">{pr.title}</TableCell>
                <TableCell><StatusBadge status={pr.status} /></TableCell>
                <TableCell className="text-muted-foreground">{safeDate(pr.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
