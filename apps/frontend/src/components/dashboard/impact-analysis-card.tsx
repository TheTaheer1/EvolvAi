"use client";

import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";

import { ScoreBadge } from "@/components/shared/score-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ImpactAnalysis } from "@/types/impact-analysis";

export function ImpactAnalysisCard({ impact }: { impact?: ImpactAnalysis | null }) {
  const chartData = impact
    ? [
        { metric: "Business", value: impact.business_impact },
        { metric: "Urgency", value: impact.urgency },
        { metric: "Confidence", value: impact.confidence },
        { metric: "Opportunity", value: impact.opportunity_score },
        { metric: "Low risk", value: 1 - impact.risk_score }
      ]
    : [];
  const breakdown = impact
    ? Object.entries(impact.impact_breakdown || {}).map(([name, value]) => ({ name: name.replaceAll("_", " "), value }))
    : [];

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
          <CardTitle>Impact analysis</CardTitle>
          <div className="flex flex-wrap gap-2">
            <ScoreBadge label="Business" value={impact?.business_impact} />
            <ScoreBadge label="Urgency" value={impact?.urgency} />
            <ScoreBadge label="Confidence" value={impact?.confidence} />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!impact ? (
          <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">Impact analysis pending.</div>
        ) : (
          <div className="grid min-w-0 gap-6 2xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div className="h-64 min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={chartData}>
                  <PolarGrid stroke="rgba(148,163,184,0.25)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: "#cbd5e1", fontSize: 11 }} />
                  <Radar dataKey="value" stroke="#67e8f9" fill="#67e8f9" fillOpacity={0.25} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div className="min-w-0">
              <div className="mb-3 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Priority</span>
                <span className="font-semibold text-cyan-100">{impact.final_priority}</span>
              </div>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={breakdown} layout="vertical" margin={{ left: 18, right: 8 }}>
                    <XAxis type="number" domain={[0, 1]} hide />
                    <YAxis type="category" dataKey="name" width={120} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip formatter={(value) => `${Math.round(Number(value) * 100)}%`} />
                    <Bar dataKey="value" fill="#22d3ee" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
