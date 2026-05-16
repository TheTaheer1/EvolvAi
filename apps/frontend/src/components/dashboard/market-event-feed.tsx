"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { safeDate } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboard-store";

export function MarketEventFeed() {
  const events = useDashboardStore((state) => state.marketEvents);
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Market Event Feed</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-72 pr-3">
          {events.length === 0 ? <p className="text-sm text-muted-foreground">No market events yet.</p> : null}
          <div className="space-y-3">
            {events.map((event) => (
              <div key={event.id} className="rounded-xl border bg-background/40 p-3">
                <p className="text-sm font-medium">{event.title}</p>
                <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{event.summary || "No summary"}</p>
                <p className="mt-2 text-xs text-cyan-200">{safeDate(event.created_at)} · score {event.importance_score}</p>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
