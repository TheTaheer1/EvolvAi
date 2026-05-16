"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { useDashboardStore } from "@/store/dashboard-store";

export function useDashboard() {
  const setLiveState = useDashboardStore((state) => state.setLiveState);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [liveState, demoState] = await Promise.all([apiClient.liveState(), apiClient.demoState()]);
      const selectedScenarioKey = useDashboardStore.getState().selectedScenarioKey;
      setLiveState({
        metrics: liveState.summary,
        companyProfile: demoState.company_profile,
        scenarios: demoState.scenarios,
        selectedScenarioKey: selectedScenarioKey ?? demoState.scenarios[0]?.scenario_key ?? null,
        activeWorkflow: demoState.latest_workflows[0] ?? liveState.workflows[0] ?? null,
        latestArtifacts: demoState.latest_generated_artifacts,
        latestImpactAnalysis: demoState.latest_impact_analysis ?? null,
        latestPRPreview: demoState.latest_pr_preview ?? null,
        verificationReport: demoState.latest_verification_report ?? null,
        workflows: liveState.workflows,
        logs: liveState.logs,
        decisions: liveState.decisions,
        pullRequests: liveState.pull_requests,
        marketEvents: liveState.market_events,
        environment: { ...liveState.environment, ...demoState.environment }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [setLiveState]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { loading, error, refresh };
}
