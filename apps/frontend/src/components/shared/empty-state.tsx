import { Inbox } from "lucide-react";

export function EmptyState({ title, message }: { title: string; message?: string }) {
  return (
    <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
      <Inbox className="mx-auto mb-3 h-5 w-5" />
      <p className="font-medium text-foreground">{title}</p>
      {message ? <p className="mt-1">{message}</p> : null}
    </div>
  );
}
