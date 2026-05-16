import { Badge, type BadgeProps } from "@/components/ui/badge";

export function ScoreBadge({ label, value }: { label: string; value?: number | null }) {
  const score = typeof value === "number" ? Math.round(value * 100) : null;
  const variant: BadgeProps["variant"] = score === null ? "muted" : score >= 80 ? "success" : score >= 60 ? "default" : "warning";
  return (
    <Badge variant={variant}>
      {label}: {score === null ? "pending" : `${score}%`}
    </Badge>
  );
}
