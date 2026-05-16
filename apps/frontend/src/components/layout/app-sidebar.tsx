"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bell, BrainCircuit, FolderGit2, GitPullRequest, LayoutDashboard, RadioTower, Settings, Wrench } from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/workflows", label: "Workflows", icon: Activity },
  { href: "/market-events", label: "Market Events", icon: RadioTower },
  { href: "/repositories", label: "Repositories", icon: FolderGit2 },
  { href: "/decisions", label: "Decisions", icon: BrainCircuit },
  { href: "/prs", label: "PR Center", icon: GitPullRequest },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/debug", label: "Debug", icon: Wrench }
];

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden min-h-screen w-72 border-r bg-background/50 p-4 backdrop-blur lg:block">
      <Link href="/dashboard" className="mb-8 flex items-center gap-3 rounded-2xl border bg-card/70 p-4">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Bell className="h-5 w-5" />
        </div>
        <div>
          <p className="font-semibold">EvolvAI</p>
          <p className="text-xs text-muted-foreground">SaaS evolution OS</p>
        </div>
      </Link>
      <nav className="space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground",
                active && "bg-primary/15 text-cyan-100"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
