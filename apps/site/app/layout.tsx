import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

const OTTER_FAVICON =
  "data:image/svg+xml," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🦦</text></svg>`,
  );

export const metadata: Metadata = {
  title: "Otter - Easily understand & change code",
  description:
    "Otter is engineering intelligence you self-host. Import repos, plan changes, and ship approval-gated patches with Docker or the npm CLI — and your own model.",
  icons: {
    icon: [{ url: OTTER_FAVICON, type: "image/svg+xml" }],
    shortcut: OTTER_FAVICON,
    apple: OTTER_FAVICON,
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
