"use client";

import { useEffect } from "react";

import { EVENTS, LIVE_EVENTS } from "@/lib/event-names";
import { getSocket } from "@/lib/socket-client";
import { useDashboardStore } from "@/store/dashboard-store";
import { useWorkflowStore } from "@/store/workflow-store";
import type { LiveEvent } from "@/types/api";

function isAgentExecutionEvent(event: LiveEvent) {
  return Boolean(
    event.agent_name &&
      typeof event.id === "string" &&
      ("input_state" in event || "output_state" in event || "started_at" in event || "completed_at" in event)
  );
}

export function useSocket(workflowId?: string) {
  const setSocketConnected = useDashboardStore((state) => state.setSocketConnected);
  const addEvent = useDashboardStore((state) => state.addEvent);
  const updateWorkflowFromEvent = useWorkflowStore((state) => state.updateWorkflowFromEvent);
  const upsertAgentExecution = useWorkflowStore((state) => state.upsertAgentExecution);
  const addLog = useWorkflowStore((state) => state.addLog);
  const addArtifact = useWorkflowStore((state) => state.addArtifact);
  const setImpactAnalysis = useWorkflowStore((state) => state.setImpactAnalysis);
  const setVerificationReport = useWorkflowStore((state) => state.setVerificationReport);
  const setPRPreview = useWorkflowStore((state) => state.setPRPreview);

  useEffect(() => {
    const socket = getSocket();

    const onConnect = () => setSocketConnected(true);
    const onDisconnect = () => setSocketConnected(false);
    const handlers = LIVE_EVENTS.map((eventName) => {
      const handler = (payload: unknown) => {
        if (!payload || typeof payload !== "object") {
          if (process.env.NODE_ENV === "development") console.warn("Malformed socket event", eventName, payload);
          return;
        }
        const event = payload as LiveEvent;
        addEvent({ ...event, event_name: String(event.event_name || eventName) });
        if (String(eventName).startsWith("workflow.")) {
          updateWorkflowFromEvent(event as never);
        }
        if (
          (eventName === EVENTS.AGENT_STARTED ||
            eventName === EVENTS.AGENT_UPDATED ||
            eventName === EVENTS.AGENT_COMPLETED ||
            eventName === EVENTS.AGENT_FAILED) &&
          isAgentExecutionEvent(event)
        ) {
          upsertAgentExecution(event as never);
        }
        if (eventName === EVENTS.LOG_CREATED) {
          addLog(event as never);
        }
        if (eventName === EVENTS.ARTIFACT_GENERATED) {
          addArtifact(event as never);
        }
        if (eventName === EVENTS.IMPACT_CREATED) {
          setImpactAnalysis(event as never);
        }
        if (eventName === EVENTS.VERIFICATION_COMPLETED) {
          setVerificationReport(event as never);
        }
        if (
          eventName === EVENTS.PR_CREATED ||
          eventName === EVENTS.PR_PREVIEW_CREATED ||
          eventName === EVENTS.PR_OPENED ||
          eventName === EVENTS.PR_FAILED
        ) {
          setPRPreview(event as never);
        }
      };
      socket.on(eventName, handler);
      return { eventName, handler };
    });

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    if (!socket.connected) socket.connect();
    if (workflowId) socket.emit(EVENTS.WORKFLOW_JOIN, { workflow_id: workflowId });

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      handlers.forEach(({ eventName, handler }) => socket.off(eventName, handler));
    };
  }, [
    addArtifact,
    addEvent,
    addLog,
    setImpactAnalysis,
    setPRPreview,
    setSocketConnected,
    setVerificationReport,
    updateWorkflowFromEvent,
    upsertAgentExecution,
    workflowId
  ]);
}
