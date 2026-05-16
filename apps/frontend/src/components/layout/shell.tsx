"use client";

import { ReactNode } from "react";

import { useSocket } from "@/hooks/use-socket";
import { AppSidebar } from "./app-sidebar";
import { Topbar } from "./topbar";

export function Shell({ children }: { children: ReactNode }) {
  useSocket();
  return (
    <div className="min-h-screen lg:flex">
      <AppSidebar />
      <div className="min-w-0 flex-1">
        <Topbar />
        <main className="p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
