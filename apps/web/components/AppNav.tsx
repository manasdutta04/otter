"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "", label: "Overview" },
  { href: "/intelligence", label: "Intelligence" },
  { href: "/chat", label: "Chat" },
  { href: "/planner", label: "Planner" },
  { href: "/memory", label: "Memory" },
  { href: "/health", label: "Health" },
  { href: "/review", label: "Review" },
  { href: "/coding", label: "Coding" },
  { href: "/settings", label: "Settings" },
] as const;

type AppNavProps = {
  repositoryId: string;
};

export function AppNav({ repositoryId }: AppNavProps) {
  const pathname = usePathname();
  const base = `/app/repositories/${repositoryId}`;

  return (
    <nav className="app-nav" aria-label="Repository sections">
      {LINKS.map((link) => {
        const href = `${base}${link.href}`;
        const active = link.href === "" ? pathname === base : pathname.startsWith(href);
        return (
          <Link key={link.href} className={active ? "app-nav-link active" : "app-nav-link"} href={href}>
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
