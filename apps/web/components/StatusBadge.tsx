import type { RepoStatus, CodeTaskStatus } from "../lib/api";

type StatusBadgeProps = {
  status: RepoStatus | CodeTaskStatus | string;
};

const LABELS: Record<string, string> = {
  queued: "Queued",
  cloning: "Cloning",
  ready: "Ready",
  failed: "Failed",
  running: "Running",
  succeeded: "Succeeded",
  draft: "Draft",
  ready_for_approval: "Awaiting patch",
  patch_ready: "Patch ready",
  approved: "Approved",
  rejected: "Rejected",
  applied: "Applied",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const tone =
    status === "ready" || status === "succeeded" || status === "applied" || status === "approved"
      ? "ok"
      : status === "failed" || status === "rejected"
        ? "bad"
        : status === "cloning" || status === "running" || status === "queued"
          ? "live"
          : "neutral";

  return <span className={`status-badge status-${tone}`}>{LABELS[status] ?? status}</span>;
}
