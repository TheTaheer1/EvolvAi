"use client";

import { useCallback, useEffect, useState } from "react";
import { FolderSearch } from "lucide-react";

import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api-client";
import { safeDate } from "@/lib/utils";
import type { RepositoryAnalysis } from "@/types/repository";

export default function RepositoriesPage() {
  const [owner, setOwner] = useState("vercel");
  const [repo, setRepo] = useState("next.js");
  const [branch, setBranch] = useState("canary");
  const [analyses, setAnalyses] = useState<RepositoryAnalysis[]>([]);
  const [selected, setSelected] = useState<RepositoryAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [attachWorkflowId, setAttachWorkflowId] = useState("");
  const [attachMessage, setAttachMessage] = useState<string | null>(null);

  const loadAnalyses = useCallback(async () => {
    try {
      const latest = await apiClient.repositoryAnalyses();
      setAnalyses(latest);
      if (!selected && latest[0]) {
        const detail = await apiClient.repositoryAnalysis(latest[0].id);
        setSelected(detail);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load repository analyses");
    }
  }, [selected]);

  useEffect(() => {
    void loadAnalyses();
  }, [loadAnalyses]);

  async function analyze() {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const analysis = await apiClient.analyzeRepository(owner.trim(), repo.trim(), branch.trim() || "main");
      setSelected(analysis);
      setMessage(`Analyzed ${analysis.owner}/${analysis.repo}: ${analysis.analyzed_file_count} files selected.`);
      await loadAnalyses();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Repository analysis failed safely");
    } finally {
      setLoading(false);
    }
  }

  async function selectAnalysis(id: string) {
    setError(null);
    setAttachMessage(null);
    try {
      setSelected(await apiClient.repositoryAnalysis(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load analysis detail");
    }
  }

  async function attachToWorkflow() {
    if (!selected || !attachWorkflowId.trim()) return;
    setError(null);
    setAttachMessage(null);
    try {
      await apiClient.attachRepositoryAnalysis(selected.id, attachWorkflowId.trim());
      setAttachMessage("Repository context attached to workflow. Open the workflow detail page to see the Codebase Context panel.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to attach repository context");
    }
  }

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderSearch className="h-5 w-5 text-primary" />
            Repository Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_160px_auto]">
            <Input value={owner} onChange={(event) => setOwner(event.target.value)} aria-label="GitHub owner" placeholder="owner" />
            <Input value={repo} onChange={(event) => setRepo(event.target.value)} aria-label="GitHub repository" placeholder="repo" />
            <Input value={branch} onChange={(event) => setBranch(event.target.value)} aria-label="branch" placeholder="branch" />
            <Button onClick={() => void analyze()} disabled={loading || !owner.trim() || !repo.trim()}>
              {loading ? "Analyzing..." : "Analyze Repository"}
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">
            Read-only scan. EvolvAI reads public GitHub metadata/tree data, excludes secrets and large files, and never writes to the repository.
          </p>
          {message ? <p className="text-sm text-cyan-100">{message}</p> : null}
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
        </CardContent>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card>
          <CardHeader><CardTitle>Latest Analyses</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {analyses.length === 0 ? <p className="text-sm text-muted-foreground">No repository analyses yet.</p> : null}
            {analyses.map((analysis) => (
              <button
                key={analysis.id}
                type="button"
                onClick={() => void selectAnalysis(analysis.id)}
                className="w-full rounded-xl border bg-background/40 p-3 text-left transition hover:border-primary"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="min-w-0 truncate font-medium">{analysis.owner}/{analysis.repo}</p>
                  <StatusBadge status={analysis.status} />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{analysis.branch} · {safeDate(analysis.created_at)}</p>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Analysis Detail</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {!selected ? <p className="text-sm text-muted-foreground">Select or run an analysis.</p> : null}
            {selected ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={selected.status} />
                  <Badge variant="muted">{selected.file_count} files found</Badge>
                  <Badge variant="muted">{selected.analyzed_file_count} analyzed</Badge>
                  {selected.repo_url ? <Button asChild size="sm" variant="outline"><a href={selected.repo_url} target="_blank" rel="noreferrer">Open repo</a></Button> : null}
                </div>
                <p className="text-sm text-muted-foreground">{selected.summary || selected.error_message}</p>
                <div className="flex flex-wrap gap-2">
                  {selected.detected_stack.map((item) => <Badge key={item}>{item}</Badge>)}
                </div>
                <div className="rounded-xl border bg-background/40 p-3">
                  <p className="text-sm font-medium">Attach to workflow</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    This adds read-only codebase context to Planner, Execution, and PR preview without modifying repository files.
                  </p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                    <Input
                      value={attachWorkflowId}
                      onChange={(event) => setAttachWorkflowId(event.target.value)}
                      placeholder="workflow UUID"
                      aria-label="workflow id"
                    />
                    <Button onClick={() => void attachToWorkflow()} disabled={!attachWorkflowId.trim()}>Attach</Button>
                  </div>
                  {attachMessage ? <p className="mt-2 text-sm text-cyan-100">{attachMessage}</p> : null}
                </div>
                <div className="grid gap-3">
                  {(selected.files || []).slice(0, 18).map((file) => (
                    <div key={file.id} className="rounded-xl border bg-background/40 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="min-w-0 break-all font-mono text-sm text-cyan-100">{file.path}</p>
                        <Badge variant="muted">{Math.round(file.importance_score * 100)}%</Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{file.file_type || "file"} · {file.language || "unknown"} · {file.size_bytes ?? "?"} bytes</p>
                      <p className="mt-2 text-sm text-muted-foreground">{file.summary}</p>
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
