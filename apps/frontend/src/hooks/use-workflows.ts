"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { useWorkflowStore } from "@/store/workflow-store";

export function useWorkflows() {
  const workflows = useWorkflowStore((state) => state.workflows);
  const setWorkflows = useWorkflowStore((state) => state.setWorkflows);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setWorkflows(await apiClient.workflows());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load workflows");
    } finally {
      setLoading(false);
    }
  }, [setWorkflows]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { workflows, loading, error, refresh };
}
