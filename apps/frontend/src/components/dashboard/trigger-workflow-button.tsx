"use client";

import { useState } from "react";
import { Rocket } from "lucide-react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { useDashboardStore } from "@/store/dashboard-store";
import { useWorkflowStore } from "@/store/workflow-store";

export function TriggerWorkflowButton() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const addEvent = useDashboardStore((state) => state.addEvent);
  const updateWorkflow = useWorkflowStore((state) => state.updateWorkflowFromEvent);

  async function trigger() {
    setLoading(true);
    setError(null);
    try {
      const workflow = await apiClient.triggerWorkflow();
      updateWorkflow(workflow);
      addEvent({ event_name: "workflow.created", event_id: `manual:${workflow.id}`, ...workflow });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to trigger workflow");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <Button onClick={trigger} disabled={loading} size="lg" className="w-full md:w-auto">
        <Rocket className="mr-2 h-4 w-4" />
        {loading ? "Queueing demo workflow..." : "Trigger Demo Workflow"}
      </Button>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
    </div>
  );
}
