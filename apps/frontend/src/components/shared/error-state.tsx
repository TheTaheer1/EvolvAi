import { AlertCircle } from "lucide-react";

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-400/30 bg-red-950/20 p-4 text-sm text-red-100">
      <div className="flex items-center gap-2 font-medium">
        <AlertCircle className="h-4 w-4" />
        Something needs attention
      </div>
      <p className="mt-2 text-red-100/80">{message}</p>
    </div>
  );
}
