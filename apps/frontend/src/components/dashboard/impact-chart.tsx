"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboardStore } from "@/store/dashboard-store";

export function ImpactChart() {
  const decisions = useDashboardStore((state) => state.decisions);
  const data = decisions.length
    ? decisions.slice(0, 6).map((decision, index) => ({ name: `D${decisions.length - index}`, impact: decision.impact_score }))
    : [
        { name: "Watcher", impact: 0.35 },
        { name: "Research", impact: 0.5 },
        { name: "Strategy", impact: 0.82 }
      ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Impact Signal</CardTitle>
      </CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" domain={[0, 1]} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 12 }} />
            <Bar dataKey="impact" fill="#22d3ee" radius={[10, 10, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
