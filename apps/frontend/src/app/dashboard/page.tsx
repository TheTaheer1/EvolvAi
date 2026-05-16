"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Code2,
  Database,
  FolderSearch,
  GitPullRequestArrow,
  Loader2,
  Play,
  RadioTower,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  WifiOff
} from "lucide-react";

import { GeneratedArtifactsPanel } from "@/components/dashboard/generated-artifacts-panel";
import { ImpactAnalysisCard } from "@/components/dashboard/impact-analysis-card";
import { LiveLogPanel } from "@/components/dashboard/live-log-panel";
import { PrPreviewCard } from "@/components/dashboard/pr-preview-card";
import { VerificationReportCard } from "@/components/dashboard/verification-report-card";
import { WorkflowStatusCard } from "@/components/dashboard/workflow-status-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboard } from "@/hooks/use-dashboard";
import { apiClient } from "@/lib/api-client";
import { safeDate } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboard-store";
import type { LiveEventIngestResponse } from "@/types/external-event";
import type { MarketEvent } from "@/types/market-event";
import type { RepositoryAnalysis } from "@/types/repository";
import type { Workflow } from "@/types/workflow";

const quickQueries = [
  "AI SaaS automation stars:>500",
  "RAG SaaS assistant stars:>500",
  "AI meeting summarization stars:>100",
  "AI compliance audit logs stars:>100",
  "workflow automation AI stars:>500"
];
const hnKeywordChips = [
  "ai, saas, agent, automation",
  "llm, rag, developer tools",
  "startup, productivity, workflow",
  "security, compliance, audit",
  ""
];
const hnFeeds = ["top", "new", "best", "show", "ask", "jobs"] as const;
type LiveSignalProvider = "github" | "hacker_news";

const terminalStatuses = new Set(["completed", "failed", "cancelled", "no_action_needed"]);
const agentNames = [
  { label: "Watcher", key: "watcher" },
  { label: "Research", key: "research" },
  { label: "Strategy", key: "strategy" },
  { label: "Planner", key: "planner" },
  { label: "Execution", key: "execution" },
  { label: "Verification", key: "verification" },
  { label: "PR", key: "pr" }
];

function envEnabled(environment: Record<string, unknown>, key: string) {
  return String(environment[key]) === "true";
}

function statusVariant(ok: boolean, riskyEnabled = false): BadgeProps["variant"] {
  if (riskyEnabled && ok) return "warning";
  return ok ? "success" : "muted";
}

function workflowProgress(workflow?: Workflow | null) {
  if (!workflow) return 0;
  if (workflow.status === "completed" || workflow.status === "no_action_needed") return 100;
  if (workflow.status === "failed" || workflow.status === "cancelled") return 100;
  if (workflow.status === "running") return 58;
  if (workflow.status === "queued") return 18;
  return 0;
}

function agentPreviewStatus(workflow: Workflow | null | undefined, agentKey: string) {
  if (!workflow) return "pending";
  if (workflow.status === "completed" || workflow.status === "no_action_needed") return "completed";
  if (workflow.status === "failed" || workflow.status === "cancelled") return "stopped";
  if (workflow.status === "queued" || workflow.status === "pending") return "pending";
  const current = String(workflow.current_agent || "").toLowerCase();
  const currentIndex = agentNames.findIndex((agent) => current.includes(agent.key));
  const agentIndex = agentNames.findIndex((agent) => agent.key === agentKey);
  if (currentIndex === -1) return "running";
  if (agentIndex < currentIndex) return "completed";
  if (agentIndex === currentIndex) return "running";
  return "pending";
}

function eventMeta(event: MarketEvent) {
  const raw = event.raw_payload || {};
  if (event.source === "hacker_news") {
    const score = raw.score;
    const comments = raw.descendants;
    const by = raw.by;
    return [score !== undefined ? `${score} points` : null, comments !== undefined ? `${comments} comments` : null, by ? `by ${String(by)}` : null]
      .filter(Boolean)
      .join(" · ");
  }
  const stars = raw.stargazers_count ?? raw.stars;
  const forks = raw.forks_count ?? raw.forks;
  const language = raw.language;
  return [stars ? `${stars} stars` : null, forks ? `${forks} forks` : null, language ? String(language) : null]
    .filter(Boolean)
    .join(" · ");
}

function SystemCard({
  title,
  value,
  detail,
  icon: Icon,
  variant = "muted"
}: {
  title: string;
  value: string;
  detail: string;
  icon: typeof Bot;
  variant?: BadgeProps["variant"];
}) {
  return (
    <Card>
      <CardContent className="flex items-start gap-3 p-4">
        <div className="rounded-lg border bg-background/50 p-2">
          <Icon className="h-4 w-4 text-cyan-200" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs text-muted-foreground">{title}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <Badge variant={variant}>{value}</Badge>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{detail}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { loading, error, refresh } = useDashboard();
  const socketConnected = useDashboardStore((state) => state.socketConnected);
  const environment = useDashboardStore((state) => state.environment);
  const activeWorkflow = useDashboardStore((state) => state.activeWorkflow);
  const latestImpactAnalysis = useDashboardStore((state) => state.latestImpactAnalysis);
  const latestArtifacts = useDashboardStore((state) => state.latestArtifacts);
  const latestPRPreview = useDashboardStore((state) => state.latestPRPreview);
  const verificationReport = useDashboardStore((state) => state.verificationReport);
  const workflows = useDashboardStore((state) => state.workflows);
  const marketEvents = useDashboardStore((state) => state.marketEvents);
  const upsertWorkflow = useDashboardStore((state) => state.upsertWorkflow);
  const [githubQuery, setGithubQuery] = useState("AI SaaS automation stars:>500");
  const [liveProvider, setLiveProvider] = useState<LiveSignalProvider>("github");
  const [hnFeed, setHnFeed] = useState<(typeof hnFeeds)[number]>("top");
  const [hnKeywords, setHnKeywords] = useState("ai, saas, agent, automation");
  const [hnMinScore, setHnMinScore] = useState(20);
  const [maxResults, setMaxResults] = useState(5);
  const [reliableRunning, setReliableRunning] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [liveEventMessage, setLiveEventMessage] = useState<string | null>(null);
  const [liveIngestion, setLiveIngestion] = useState<LiveEventIngestResponse | null>(null);
  const [latestRepositoryAnalysis, setLatestRepositoryAnalysis] = useState<RepositoryAnalysis | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const latestLiveEvents = useMemo(
    () => marketEvents.filter((event) => event.source !== "controlled_demo").slice(0, 6),
    [marketEvents]
  );
  const provider = String(environment.llm_provider || "groq");
  const model = String(environment.llm_model || "llama-3.3-70b-versatile");
  const liveAiEnabled = envEnabled(environment, "live_ai_outputs_enabled");
  const githubIngestionEnabled = envEnabled(environment, "github_ingestion_enabled");
  const hnIngestionEnabled = envEnabled(environment, "hn_ingestion_enabled");
  const githubConfigured = envEnabled(environment, "github_configured");
  const realPrEnabled = envEnabled(environment, "real_prs_enabled");
  const codeExecutionEnabled = envEnabled(environment, "code_execution_enabled");
  const externalWritesEnabled = envEnabled(environment, "external_writes_enabled");

  useEffect(() => {
    let cancelled = false;
    apiClient.repositoryAnalyses(1)
      .then((analyses) => {
        if (!cancelled) setLatestRepositoryAnalysis(analyses[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) setLatestRepositoryAnalysis(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!activeWorkflow) return;
    if (terminalStatuses.has(activeWorkflow.status) && socketConnected) return;
    const interval = window.setInterval(() => {
      apiClient.workflow(activeWorkflow.id)
        .then(upsertWorkflow)
        .catch(() => undefined);
    }, socketConnected ? 5000 : 3000);
    return () => window.clearInterval(interval);
  }, [activeWorkflow, socketConnected, upsertWorkflow]);

  async function runReliableDemo() {
    setReliableRunning(true);
    setActionError(null);
    try {
      const workflow = await apiClient.triggerScenario("ai-meeting-summary", "fast");
      upsertWorkflow(workflow);
      router.push(`/workflows/${workflow.id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Reliable demo could not start. Check backend and seed data.");
    } finally {
      setReliableRunning(false);
    }
  }

  async function ingestGithubSignals() {
    setIngesting(true);
    setLiveEventMessage(null);
    setActionError(null);
    try {
      const response = await apiClient.ingestGithubEvents(githubQuery, maxResults, false);
      setLiveIngestion(response);
      const duplicateText = response.events_skipped
        ? ` ${response.events_skipped} duplicate signal(s) were skipped.`
        : "";
      const warningText = response.warnings?.length ? ` ${response.warnings[0]}` : "";
      setLiveEventMessage(
        `GitHub ingestion ${response.status}: ${response.events_found} found, ${response.events_created} created.${duplicateText}${warningText}`
      );
      await refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "GitHub ingestion failed safely.";
      setLiveEventMessage(
        message.toLowerCase().includes("rate")
          ? "GitHub rate limit reached. Use Reliable Demo or try again later."
          : message
      );
    } finally {
      setIngesting(false);
    }
  }

  async function ingestHackerNewsSignals() {
    setIngesting(true);
    setLiveEventMessage(null);
    setActionError(null);
    try {
      const keywords = hnKeywords.trim()
        ? hnKeywords.split(",").map((item) => item.trim()).filter(Boolean)
        : [];
      const response = await apiClient.ingestHackerNewsEvents({
        feed: hnFeed,
        max_results: maxResults,
        keywords,
        min_score: hnMinScore,
        trigger_workflows: false
      });
      setLiveIngestion(response);
      const skippedText = response.events_skipped
        ? ` ${response.events_skipped} story signal(s) were skipped, filtered, or deduped.`
        : "";
      const warningText = response.warnings?.length ? ` ${response.warnings[0]}` : "";
      setLiveEventMessage(
        `Hacker News ingestion ${response.status}: ${response.events_found} checked, ${response.events_created} created.${skippedText}${warningText}`
      );
      await refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Hacker News ingestion failed safely.";
      setLiveEventMessage(
        message.toLowerCase().includes("timeout")
          ? "Hacker News request timed out. Use Reliable Demo or try again later."
          : message
      );
    } finally {
      setIngesting(false);
    }
  }

  async function ingestSelectedLiveSignals() {
    if (liveProvider === "hacker_news") {
      await ingestHackerNewsSignals();
      return;
    }
    await ingestGithubSignals();
  }

  async function triggerLiveEvent(eventId: string) {
    setActionError(null);
    try {
      const workflow = await apiClient.triggerWorkflowFromMarketEvent(eventId);
      upsertWorkflow(workflow);
      router.push(`/workflows/${workflow.id}`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to trigger live event workflow. Try again.");
    }
  }

  return (
    <div className="min-w-0 space-y-6 overflow-x-hidden">
      <section className="overflow-hidden rounded-2xl border bg-card/70 shadow-glow">
        <div className="grid gap-6 p-6 md:p-8 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)] xl:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap gap-2">
              <Badge>Multi-Agent</Badge>
              <Badge>Live Signals</Badge>
              <Badge>LLM Hybrid</Badge>
              <Badge>Safe Preview</Badge>
              <Badge>PR Guardrails</Badge>
            </div>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight md:text-6xl">EvolvAI</h1>
            <p className="mt-4 max-w-3xl text-lg text-muted-foreground">
              Autonomous SaaS evolution powered by live market signals, multi-agent reasoning, safe artifact generation, and PR previews.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button size="lg" onClick={() => void runReliableDemo()} disabled={reliableRunning}>
                {reliableRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                Run Reliable Demo
              </Button>
              <Button size="lg" variant="outline" onClick={() => void ingestSelectedLiveSignals()} disabled={ingesting}>
                {ingesting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RadioTower className="mr-2 h-4 w-4" />}
                Ingest Live Signals
              </Button>
            </div>
            <p className="mt-4 text-sm text-emerald-100">
              Real PR creation, code execution, and external write actions are disabled by default.
            </p>
          </div>
          <Card>
            <CardHeader><CardTitle className="text-base">2-minute story</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p><span className="text-foreground">1.</span> Watch a controlled or live market signal.</p>
              <p><span className="text-foreground">2.</span> Run seven agents: watcher, research, strategy, planning, execution, verification, PR.</p>
              <p><span className="text-foreground">3.</span> Review generated artifacts, impact, explainability, and safety-gated PR preview.</p>
              <div className="rounded-lg border bg-emerald-300/10 p-3 text-emerald-100">
                Fallback mode keeps the demo reliable when LLMs or external APIs are rate-limited.
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {loading ? <Skeleton className="h-24 w-full" /> : null}
      {error ? (
        <Alert className="border-red-400/30 bg-red-950/20">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Backend unavailable</AlertTitle>
          <AlertDescription>Backend unavailable. Start Docker Compose and refresh. Details: {error}</AlertDescription>
          <Button className="mt-3" size="sm" variant="outline" onClick={() => void refresh()}>Retry</Button>
        </Alert>
      ) : null}
      {actionError ? (
        <Alert className="border-amber-400/30 bg-amber-950/20">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Action needs attention</AlertTitle>
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      ) : null}
      {!socketConnected ? (
        <Alert className="border-cyan-400/30 bg-cyan-950/20">
          <WifiOff className="h-4 w-4" />
          <AlertTitle>Realtime disconnected</AlertTitle>
          <AlertDescription>Realtime disconnected. Polling for updates through REST so the demo can continue.</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-6">
        <SystemCard icon={Bot} title="LLM Provider" value={`${provider} / ${model}`} detail="Structured outputs with fallback." variant={liveAiEnabled ? "default" : "muted"} />
        <SystemCard icon={Sparkles} title="Live AI" value={liveAiEnabled ? "Enabled" : "Disabled"} detail="Fallback remains available." variant={liveAiEnabled ? "default" : "muted"} />
        <SystemCard icon={RadioTower} title="Live Ingestion" value={(githubIngestionEnabled || hnIngestionEnabled) ? "Enabled" : "Disabled"} detail={githubConfigured ? "GitHub token configured; HN no key." : "GitHub unauthenticated; HN no key."} variant={(githubIngestionEnabled || hnIngestionEnabled) ? "default" : "muted"} />
        <SystemCard icon={GitPullRequestArrow} title="Real PR Creation" value={realPrEnabled ? "Enabled" : "Disabled"} detail="Disabled is safe for judging." variant={statusVariant(!realPrEnabled, realPrEnabled)} />
        <SystemCard icon={Code2} title="Code Execution" value={codeExecutionEnabled ? "Enabled" : "Disabled"} detail="Generated code is never run." variant={statusVariant(!codeExecutionEnabled, codeExecutionEnabled)} />
        <SystemCard icon={ShieldCheck} title="External Writes" value={externalWritesEnabled ? "Enabled" : "Disabled"} detail="Draft PR requires opt-in." variant={statusVariant(!externalWritesEnabled, externalWritesEnabled)} />
      </div>

      <WorkflowStatusCard />

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="border-cyan-300/30">
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>Reliable Demo</CardTitle>
                <p className="mt-2 text-sm text-muted-foreground">
                  Run EvolvAI with controlled market data. Best for live judging.
                </p>
              </div>
              <Badge variant="success">Recommended</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Uses controlled demo data so the full workflow works even if external APIs are rate-limited.
            </p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="muted">Always available</Badge>
              <Badge variant="muted">Uses fallback if LLM/API fails</Badge>
              <Badge variant="muted">ai-meeting-summary</Badge>
              <Badge variant="muted">fast mode</Badge>
            </div>
            <Button className="w-full" onClick={() => void runReliableDemo()} disabled={reliableRunning}>
              {reliableRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              Run Reliable Demo
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Run Live Signal Demo</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              Ingest real GitHub repository trends or Hacker News technology stories and run EvolvAI on a live market event.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-2 rounded-xl border bg-background/40 p-1">
              <button
                type="button"
                onClick={() => setLiveProvider("github")}
                className={`rounded-lg px-3 py-2 text-sm transition ${liveProvider === "github" ? "bg-cyan-300 text-slate-950" : "text-muted-foreground hover:text-cyan-100"}`}
              >
                GitHub Repositories
              </button>
              <button
                type="button"
                onClick={() => setLiveProvider("hacker_news")}
                className={`rounded-lg px-3 py-2 text-sm transition ${liveProvider === "hacker_news" ? "bg-cyan-300 text-slate-950" : "text-muted-foreground hover:text-cyan-100"}`}
              >
                Hacker News
              </button>
            </div>
            {!githubConfigured && liveProvider === "github" ? (
              <p className="rounded-lg border bg-amber-300/10 p-3 text-sm text-amber-100">
                Using unauthenticated GitHub requests. Rate limits may be lower.
              </p>
            ) : null}
            {liveProvider === "hacker_news" ? (
              <p className="rounded-lg border bg-emerald-300/10 p-3 text-sm text-emerald-100">
                Hacker News requires no API key. EvolvAI stores stories as external market signals, never as instructions.
              </p>
            ) : null}
            {liveProvider === "github" ? (
              <>
                <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_120px]">
                  <Input value={githubQuery} onChange={(event) => setGithubQuery(event.target.value)} aria-label="GitHub search query" />
                  <Input
                    type="number"
                    min={1}
                    max={10}
                    value={maxResults}
                    onChange={(event) => setMaxResults(Math.max(1, Math.min(10, Number(event.target.value) || 5)))}
                    aria-label="max results"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {quickQueries.map((query) => (
                    <button
                      key={query}
                      type="button"
                      onClick={() => setGithubQuery(query)}
                      className="rounded-full border bg-muted px-3 py-1 text-xs text-muted-foreground transition hover:border-cyan-300 hover:text-cyan-100"
                    >
                      {query}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <>
                <div className="grid gap-3 sm:grid-cols-3">
                  <select
                    value={hnFeed}
                    onChange={(event) => setHnFeed(event.target.value as typeof hnFeed)}
                    className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                    aria-label="Hacker News feed"
                  >
                    {hnFeeds.map((feed) => <option key={feed} value={feed}>{feed}</option>)}
                  </select>
                  <Input
                    type="number"
                    min={1}
                    max={20}
                    value={maxResults}
                    onChange={(event) => setMaxResults(Math.max(1, Math.min(20, Number(event.target.value) || 10)))}
                    aria-label="max stories"
                  />
                  <Input
                    type="number"
                    min={0}
                    value={hnMinScore}
                    onChange={(event) => setHnMinScore(Math.max(0, Number(event.target.value) || 0))}
                    aria-label="minimum Hacker News score"
                  />
                </div>
                <Input value={hnKeywords} onChange={(event) => setHnKeywords(event.target.value)} aria-label="Hacker News keywords" />
                <div className="flex flex-wrap gap-2">
                  {hnKeywordChips.map((keywords) => (
                    <button
                      key={keywords || "no-keyword-filter"}
                      type="button"
                      onClick={() => setHnKeywords(keywords)}
                      className="rounded-full border bg-muted px-3 py-1 text-xs text-muted-foreground transition hover:border-cyan-300 hover:text-cyan-100"
                    >
                      {keywords || "no keyword filter"}
                    </button>
                  ))}
                </div>
              </>
            )}
            <Button className="w-full" variant="outline" onClick={() => void ingestSelectedLiveSignals()} disabled={ingesting}>
              {ingesting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RadioTower className="mr-2 h-4 w-4" />}
              {liveProvider === "github" ? "Ingest GitHub Signals" : "Ingest Hacker News Stories"}
            </Button>
            {liveEventMessage ? <p className="text-sm text-cyan-100">{liveEventMessage}</p> : null}
            {liveIngestion ? (
              <div className="grid gap-2 text-sm sm:grid-cols-3">
                <div className="rounded-lg border bg-background/40 p-3"><p className="text-muted-foreground">Found</p><p className="text-2xl font-semibold">{liveIngestion.events_found}</p></div>
                <div className="rounded-lg border bg-background/40 p-3"><p className="text-muted-foreground">Created</p><p className="text-2xl font-semibold">{liveIngestion.events_created}</p></div>
                <div className="rounded-lg border bg-background/40 p-3"><p className="text-muted-foreground">Skipped</p><p className="text-2xl font-semibold">{liveIngestion.events_skipped}</p></div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Active Workflow</CardTitle>
              <p className="mt-2 text-sm text-muted-foreground">
                Live progress is shown through Socket.IO. If realtime drops, this panel polls workflow status.
              </p>
            </div>
            {activeWorkflow ? <Button asChild size="sm" variant="outline"><Link href={`/workflows/${activeWorkflow.id}`}>View details</Link></Button> : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {!activeWorkflow ? (
            <p className="text-sm text-muted-foreground">No active workflow yet. Start with Run Reliable Demo.</p>
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-4">
                <div><p className="text-xs text-muted-foreground">Status</p><Badge>{activeWorkflow.status}</Badge></div>
                <div><p className="text-xs text-muted-foreground">Trigger</p><p className="truncate text-sm">{activeWorkflow.trigger_type}</p></div>
                <div><p className="text-xs text-muted-foreground">Source</p><p className="truncate text-sm">{activeWorkflow.trigger_source}</p></div>
                <div><p className="text-xs text-muted-foreground">Current agent</p><p className="truncate text-sm">{activeWorkflow.current_agent || "-"}</p></div>
              </div>
              <Progress value={workflowProgress(activeWorkflow)} />
              {activeWorkflow.status === "queued" ? (
                <p className="text-sm text-amber-100">Workflow is queued. Make sure the Celery worker is running.</p>
              ) : null}
              {activeWorkflow.status === "failed" ? (
                <p className="text-sm text-red-300">{activeWorkflow.error_message || "Workflow failed. Check logs for details."}</p>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Agent Pipeline Preview</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Seven agents run in order. Each agent can use live LLM output or deterministic fallback, and the workflow keeps moving when a provider is unavailable.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-7">
            {agentNames.map((agent) => {
              const status = agentPreviewStatus(activeWorkflow, agent.key);
              return (
                <div key={agent.key} className="rounded-xl border bg-background/40 p-3">
                  <p className="font-medium">{agent.label}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge variant={status === "completed" ? "success" : status === "running" ? "default" : status === "stopped" ? "destructive" : "muted"}>
                      {status}
                    </Badge>
                    <Badge variant={status === "completed" ? "warning" : "muted"}>
                      {status === "completed" ? "LLM/Fallback" : "ready"}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)]">
        <Card>
          <CardHeader><CardTitle>Recent Workflows</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {workflows.length === 0 ? <p className="text-sm text-muted-foreground">No workflows yet. Run Reliable Demo to create one.</p> : null}
            {workflows.slice(0, 6).map((workflow) => (
              <div key={workflow.id} className="grid gap-3 rounded-lg border bg-background/40 p-3 md:grid-cols-[1fr_auto] md:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={workflow.status === "completed" ? "success" : workflow.status === "failed" ? "destructive" : "default"}>{workflow.status}</Badge>
                    <Badge variant="muted">{workflow.trigger_source}</Badge>
                  </div>
                  <p className="mt-2 truncate text-sm font-medium">{workflow.trigger_type}</p>
                  <p className="text-xs text-muted-foreground">{safeDate(workflow.created_at)}</p>
                </div>
                <Button asChild size="sm" variant="outline"><Link href={`/workflows/${workflow.id}`}>View details</Link></Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>PR Safety</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3 rounded-lg border bg-emerald-300/10 p-3">
              <span>Real PR creation</span><Badge variant={realPrEnabled ? "warning" : "success"}>{realPrEnabled ? "enabled" : "disabled"}</Badge>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-lg border bg-emerald-300/10 p-3">
              <span>Code execution</span><Badge variant={codeExecutionEnabled ? "warning" : "success"}>{codeExecutionEnabled ? "enabled" : "disabled"}</Badge>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-lg border bg-emerald-300/10 p-3">
              <span>External write actions</span><Badge variant={externalWritesEnabled ? "warning" : "success"}>{externalWritesEnabled ? "enabled" : "disabled"}</Badge>
            </div>
            <p className="text-muted-foreground">
              Draft PR opening requires explicit opt-in, passing verification, safe generated artifacts, and GitHub credentials.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><RadioTower className="h-5 w-5 text-cyan-300" /> Live Events</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {latestLiveEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No live external events yet. Ingest GitHub or Hacker News signals, or use the reliable demo path.</p>
          ) : null}
          <div className="grid gap-3 xl:grid-cols-2">
            {latestLiveEvents.map((event) => (
              <div key={event.id} className="rounded-lg border bg-background/40 p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge>{event.source === "github" ? "GitHub" : event.source === "hacker_news" ? "Hacker News" : event.source}</Badge>
                  <Badge variant="muted">{event.event_type}</Badge>
                  <Badge variant="muted">{Math.round(event.importance_score * 100)}% importance</Badge>
                </div>
                <p className="mt-3 font-medium">{event.title}</p>
                <p className="mt-1 line-clamp-3 text-sm text-muted-foreground">{event.summary || "No summary available."}</p>
                {eventMeta(event) ? <p className="mt-2 text-xs text-cyan-100">{eventMeta(event)}</p> : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  {event.url ? <Button asChild size="sm" variant="outline"><a href={event.url} target="_blank" rel="noreferrer">Open source</a></Button> : null}
                  <Button size="sm" onClick={() => void triggerLiveEvent(event.id)}>Run Workflow</Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid min-w-0 gap-6 2xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
        <ImpactAnalysisCard impact={latestImpactAnalysis} />
        <LiveLogPanel />
      </div>

      <div className="grid min-w-0 gap-6 2xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.9fr)]">
        <GeneratedArtifactsPanel artifacts={latestArtifacts} />
        <div className="min-w-0 space-y-6">
          <VerificationReportCard report={verificationReport} />
          <PrPreviewCard preview={latestPRPreview} workflowId={latestPRPreview?.workflow_id} />
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><FolderSearch className="h-5 w-5 text-cyan-300" /> Repository Intelligence</CardTitle></CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Read-only repository analysis detects stack, important files, and suggested touchpoints without modifying source code.
            </p>
            {latestRepositoryAnalysis ? (
              <div className="flex flex-wrap gap-2 text-sm">
                <Badge>{latestRepositoryAnalysis.status}</Badge>
                <Badge variant="muted">{latestRepositoryAnalysis.owner}/{latestRepositoryAnalysis.repo}</Badge>
                <Badge variant="muted">{latestRepositoryAnalysis.analyzed_file_count} files analyzed</Badge>
                {latestRepositoryAnalysis.detected_stack.slice(0, 5).map((item) => <Badge key={item} variant="muted">{item}</Badge>)}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No repository analysis has been run yet.</p>
            )}
          </div>
          <Button asChild variant="outline"><Link href="/repositories">Open Repository Analysis</Link></Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-sm"><CheckCircle2 className="h-4 w-4" />Safe fallback</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">Fallback used to keep workflow reliable is a normal degraded mode, not a demo failure.</CardContent></Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-sm"><Database className="h-4 w-4" />Persistent state</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">PostgreSQL stores events, decisions, explainability, artifacts, verification, and PR previews.</CardContent></Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-sm"><RefreshCcw className="h-4 w-4" />REST polling</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">If Socket.IO disconnects, the dashboard keeps polling active workflow state.</CardContent></Card>
      </div>
    </div>
  );
}
