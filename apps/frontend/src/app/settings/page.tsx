"use client";

import { useDashboard } from "@/hooks/use-dashboard";
import { API_URL, DEMO_MODE, SOCKET_URL } from "@/lib/constants";
import { useDashboardStore } from "@/store/dashboard-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";

export default function SettingsPage() {
  useDashboard();
  const environment = useDashboardStore((state) => state.environment);
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card><CardHeader><CardTitle>Environment</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><p>API URL: <span className="text-cyan-200">{API_URL}</span></p><p>Socket URL: <span className="text-cyan-200">{SOCKET_URL}</span></p><p>Demo mode: <StatusBadge status={DEMO_MODE ? "ok" : "failed"} /></p><p>Backend env: {String(environment.app_env || "development")}</p></CardContent></Card>
      <Card><CardHeader><CardTitle>Safety Flags</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><p>Real PR creation: <StatusBadge status={environment.real_prs_enabled ? "enabled" : "disabled"} /></p><p>Code execution: <StatusBadge status={environment.code_execution_enabled ? "enabled" : "disabled"} /></p><p>External writes: <StatusBadge status={environment.external_writes_enabled ? "enabled" : "disabled"} /></p><p className="text-muted-foreground">Secret values are intentionally never displayed in the frontend.</p></CardContent></Card>
    </div>
  );
}
