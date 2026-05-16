"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { safeDate } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboard-store";

export function LiveLogPanel() {
  const logs = useDashboardStore((state) => state.logs);
  const events = useDashboardStore((state) => state.liveEvents);
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Live Logs</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-80 pr-3">
          <div className="space-y-2 font-mono text-xs">
            {logs.length === 0 && events.length === 0 ? <p className="text-muted-foreground">Waiting for workflow events...</p> : null}
            {logs.map((log) => (
              <div key={log.id} className="rounded-lg bg-black/25 p-2">
                <span className="text-cyan-200">{safeDate(log.created_at)}</span> <span>{log.level}</span> {log.message}
              </div>
            ))}
            {events.slice(0, 20).map((event) => (
              <div key={event.event_id} className="rounded-lg bg-black/25 p-2 text-muted-foreground">
                event:{event.event_name}
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
