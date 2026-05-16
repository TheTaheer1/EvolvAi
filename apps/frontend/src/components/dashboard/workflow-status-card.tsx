"use client";

import { Activity, CheckCircle2, CircleAlert, RadioTower } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboardStore } from "@/store/dashboard-store";

const metricCards = [
  { key: "active_workflows", label: "Active workflows", icon: Activity },
  { key: "completed_workflows", label: "Completed", icon: CheckCircle2 },
  { key: "failed_workflows", label: "Failed", icon: CircleAlert },
  { key: "market_events", label: "Market events", icon: RadioTower }
] as const;

export function WorkflowStatusCard() {
  const metrics = useDashboardStore((state) => state.metrics);
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metricCards.map((metric) => {
        const Icon = metric.icon;
        return (
          <Card key={metric.key}>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between text-sm text-muted-foreground">
                {metric.label}
                <Icon className="h-4 w-4 text-cyan-200" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{metrics[metric.key]}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
