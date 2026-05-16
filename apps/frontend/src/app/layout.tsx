import type { Metadata } from "next";

import { Shell } from "@/components/layout/shell";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "EvolvAI",
  description: "Autonomous SaaS evolution platform foundation"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
