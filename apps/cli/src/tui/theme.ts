import chalk from "chalk";

/** Shipwell-like polish; Otter river palette (teal, not purple clone). */
export const c = {
  brand: chalk.hex("#5EEAD4"), // teal
  brandBright: chalk.hex("#99F6E4").bold,
  accent: chalk.hex("#FBBF24"),
  muted: chalk.hex("#94A3B8"),
  text: chalk.hex("#E2E8F0"),
  dim: chalk.hex("#64748B"),
  ok: chalk.hex("#4ADE80"),
  bad: chalk.hex("#F87171"),
  border: chalk.hex("#334155"),
  label: chalk.hex("#67E8F9"),
};

export function visibleWidth(s: string): number {
  // strip ANSI
  return s.replace(/\u001b\[[0-9;]*m/g, "").length;
}

export function pad(s: string, width: number): string {
  const w = visibleWidth(s);
  if (w >= width) return s;
  return s + " ".repeat(width - w);
}

export function truncate(s: string, width: number): string {
  if (visibleWidth(s) <= width) return s;
  const plain = s.replace(/\u001b\[[0-9;]*m/g, "");
  return plain.slice(0, Math.max(0, width - 1)) + "…";
}
