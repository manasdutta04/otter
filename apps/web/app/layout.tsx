import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Otter — Local workspace",
  description: "Self-hosted engineering intelligence. Import repos, plan changes, and ship with approval.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
