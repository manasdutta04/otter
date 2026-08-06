import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Otter 🦦 — Engineering intelligence",
  description: "Import repositories, understand codebases, plan changes, and ship with confidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
