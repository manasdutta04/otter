"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const GROUPS = [
  {
    label: "Understand",
    links: [
      { href: "", label: "Overview" },
      { href: "/intelligence", label: "Intelligence" },
      { href: "/chat", label: "Chat" },
      { href: "/health", label: "Health" },
      { href: "/review", label: "Review" },
    ],
  },
  {
    label: "Build",
    links: [
      { href: "/planner", label: "Planner" },
      { href: "/coding", label: "Coding" },
      { href: "/memory", label: "Memory" },
    ],
  },
  {
    label: "Project",
    links: [{ href: "/settings", label: "Settings" }],
  },
] as const;

type AppNavProps = {
  repositoryId: string;
  /** Render as vertical studio rail links instead of horizontal tabs. */
  variant?: "tabs" | "rail";
};

export function AppNav({ repositoryId, variant = "rail" }: AppNavProps) {
  const pathname = usePathname();
  const base = `/app/repositories/${repositoryId}`;

  if (variant === "tabs") {
    return (
      <nav className="app-nav" aria-label="Repository sections">
        {GROUPS.flatMap((group) =>
          group.links.map((link) => {
            const href = `${base}${link.href}`;
            const active = link.href === "" ? pathname === base : pathname.startsWith(href);
            return (
              <Link
                key={link.href}
                className={active ? "app-nav-link active" : "app-nav-link"}
                href={href}
                prefetch
                scroll={false}
              >
                {link.label}
              </Link>
            );
          }),
        )}
      </nav>
    );
  }

  return (
    <nav className="studio-rail-nav studio-rail-nav-repo" aria-label="Repository sections">
      {GROUPS.map((group) => (
        <div key={group.label} className="studio-rail-group">
          <p className="studio-rail-group-label">{group.label}</p>
          {group.links.map((link) => {
            const href = `${base}${link.href}`;
            const active = link.href === "" ? pathname === base : pathname.startsWith(href);
            return (
              <Link
                key={link.href}
                className={active ? "studio-rail-link active" : "studio-rail-link"}
                href={href}
                prefetch
                scroll={false}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
