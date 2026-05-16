import { Badge, type BadgeProps } from "@/components/ui/badge";
import { formatStatus } from "@/lib/utils";

export function StatusBadge({ status }: { status?: string | null }) {
  const value = status || "unknown";
  let variant: BadgeProps["variant"] = "muted";
  if (["completed", "opened", "ok"].includes(value)) variant = "success";
  if (["queued", "running", "planned", "draft", "generated", "verified"].includes(value)) variant = "default";
  if (["pending", "no_action_needed"].includes(value)) variant = "warning";
  if (["failed", "cancelled", "unavailable", "blocked", "rejected"].includes(value)) variant = "destructive";
  return <Badge variant={variant}>{formatStatus(value)}</Badge>;
}
