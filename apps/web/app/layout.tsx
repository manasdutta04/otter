import type { Metadata } from "next";
import "./globals.css";

const OTTER_FAVICON =
  "data:image/svg+xml," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🦦</text></svg>`,
  );

export const metadata: Metadata = {
  title: "Otter — Local workspace",
  description: "Self-hosted engineering intelligence. Import repos, plan changes, and ship with approval.",
  icons: {
    icon: [{ url: OTTER_FAVICON, type: "image/svg+xml" }],
    shortcut: OTTER_FAVICON,
    apple: OTTER_FAVICON,
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
