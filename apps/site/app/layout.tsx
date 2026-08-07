import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Otter — Easily understand & change codebases",
  description:
    "Otter is engineering intelligence you self-host. Import repos, plan changes, and ship approval-gated patches with Docker + your own model.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
