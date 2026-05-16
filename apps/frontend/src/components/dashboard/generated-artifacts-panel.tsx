"use client";

import { FileCode2 } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GeneratedArtifact } from "@/types/generated-artifact";

export function GeneratedArtifactsPanel({ artifacts }: { artifacts: GeneratedArtifact[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(artifacts[0]?.id ?? null);
  const selected = artifacts.find((artifact) => artifact.id === selectedId) || artifacts[0];

  return (
    <Card className="overflow-hidden">
      <CardHeader><CardTitle className="flex items-center gap-2"><FileCode2 className="h-5 w-5 text-cyan-300" />Generated artifacts</CardTitle></CardHeader>
      <CardContent>
        {artifacts.length === 0 ? (
          <EmptyState title="No artifacts yet" message="Execution Agent will generate preview-only files inside generated_runs." />
        ) : (
          <div className="grid min-w-0 gap-4 2xl:grid-cols-[minmax(220px,0.65fr)_minmax(0,1.35fr)]">
            <div className="max-h-[520px] min-w-0 space-y-2 overflow-y-auto pr-1">
              {artifacts.map((artifact) => (
                <button
                  key={artifact.id}
                  type="button"
                  onClick={() => setSelectedId(artifact.id)}
                  className="w-full min-w-0 rounded-lg border bg-background/40 p-3 text-left hover:border-cyan-300/70"
                >
                  <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <p className="break-words text-sm font-medium">{artifact.file_path}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{artifact.description}</p>
                    </div>
                    <div className="shrink-0"><StatusBadge status={artifact.status} /></div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5"><Badge variant="muted">{artifact.artifact_type}</Badge><Badge variant="muted">{artifact.language || "text"}</Badge></div>
                </button>
              ))}
            </div>
            <div className="min-w-0">
              <div className="mb-2 flex min-w-0 items-center justify-between gap-2">
                <p className="min-w-0 break-words text-sm font-medium">{selected?.file_path}</p>
                {selected ? <Button className="shrink-0" variant="outline" size="sm" onClick={() => void navigator.clipboard?.writeText(selected.content)}>Copy</Button> : null}
              </div>
              <pre className="max-h-[520px] max-w-full overflow-auto rounded-lg border bg-slate-950 p-4 text-xs leading-relaxed text-slate-100">
                <code className="block min-w-0 whitespace-pre-wrap break-words">{selected?.content || ""}</code>
              </pre>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
