import type { Metadata } from "next";
import "./globals.css";
import "./workspace.css";

export const metadata: Metadata = {
	title: "veridexs — Engineering intelligence",
	description: "Understand your codebase in minutes.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
	return <html lang="en"><body>{children}</body></html>;
}
