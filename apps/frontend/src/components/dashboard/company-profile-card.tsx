import { Building2, Goal, Layers3, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CompanyProfile } from "@/types/company-profile";

export function CompanyProfileCard({ profile, mode = "Controlled Demo Mode" }: { profile: CompanyProfile | null; mode?: string }) {
  if (!profile) {
    return (
      <Card>
        <CardHeader><CardTitle>Company profile</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">Seed data pending.</CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2"><Building2 className="h-5 w-5 text-cyan-300" />{profile.name}</CardTitle>
          <Badge variant="default">{mode}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <p className="text-muted-foreground">{profile.description}</p>
        <div className="grid min-w-0 gap-3 md:grid-cols-3">
          <div className="min-w-0">
            <p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground"><Layers3 className="h-3.5 w-3.5" />Modules</p>
            <div className="flex flex-wrap gap-1.5">{profile.product_modules.map((item) => <Badge key={item} variant="muted">{item}</Badge>)}</div>
          </div>
          <div className="min-w-0">
            <p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground"><Users className="h-3.5 w-3.5" />Users</p>
            <div className="flex flex-wrap gap-1.5">{profile.target_users.slice(0, 4).map((item) => <Badge key={item} variant="muted">{item}</Badge>)}</div>
          </div>
          <div className="min-w-0">
            <p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground"><Goal className="h-3.5 w-3.5" />Goals</p>
            <div className="flex flex-wrap gap-1.5">{profile.business_goals.slice(0, 3).map((item) => <Badge key={item} variant="muted">{item}</Badge>)}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
