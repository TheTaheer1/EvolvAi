"use client";

import { Wifi, WifiOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDashboardStore } from "@/store/dashboard-store";

export function Topbar() {
  const connected = useDashboardStore((state) => state.socketConnected);
  return (
    <header className="sticky top-0 z-30 flex min-w-0 items-center justify-between gap-4 border-b bg-background/70 px-4 py-3 backdrop-blur md:px-8">
      <div className="min-w-0">
        <h1 className="truncate text-lg font-semibold">Autonomous SaaS Evolution Foundation</h1>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <Badge variant={connected ? "success" : "destructive"}>
          {connected ? <Wifi className="mr-1 h-3 w-3" /> : <WifiOff className="mr-1 h-3 w-3" />}
          Socket {connected ? "connected" : "offline"}
        </Badge>
        <Button variant="outline" size="sm" asChild>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API Docs</a>
        </Button>
      </div>
    </header>
  );
}
