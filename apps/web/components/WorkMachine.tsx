"use client";

import { useEffect, useState } from "react";

type WorkMachineMode = "import" | "coding" | "model";

type WorkMachineProps = {
  mode: WorkMachineMode;
  /** Coarse status when known: queued | cloning | running | busy */
  status?: string;
  label?: string;
  compact?: boolean;
};

const STAGES: Record<WorkMachineMode, string[]> = {
  import: ["Queue", "Pull", "Index", "Ready"],
  coding: ["Warm", "Plan", "Patch", "Ship"],
  model: ["Connect", "Probe", "Ready"],
};

const CHIPS: Record<WorkMachineMode, string[]> = {
  import: ["README.md", "src/main", "package.json", ".git/…", "lib/api", "Dockerfile"],
  coding: ["diff hunk", "ast walk", "patch.json", "tests", "summary", "verify"],
  model: ["/v1/models", "health", "latency", "tokens", "ready"],
};

function stageIndexForStatus(mode: WorkMachineMode, status?: string): number | null {
  if (!status) return null;
  if (mode === "import") {
    if (status === "queued") return 0;
    if (status === "cloning") return 1;
  }
  return null;
}

export function WorkMachine({ mode, status, label, compact = false }: WorkMachineProps) {
  const stages = STAGES[mode];
  const chips = CHIPS[mode];
  const mapped = stageIndexForStatus(mode, status);
  const [tick, setTick] = useState(mapped ?? 0);

  useEffect(() => {
    if (mapped !== null) {
      setTick(mapped);
      return;
    }
    const id = window.setInterval(() => {
      setTick((n) => (n + 1) % stages.length);
    }, 1400);
    return () => window.clearInterval(id);
  }, [mapped, stages.length]);

  const active = mapped !== null ? mapped : tick;
  const title =
    label ||
    (mode === "import"
      ? status === "queued"
        ? "Warming the import queue…"
        : "Pulling the repository…"
      : mode === "coding"
        ? "Otter is drafting the change…"
        : "Probing the model endpoint…");

  return (
    <div
      className={compact ? "work-machine work-machine-compact" : "work-machine"}
      role="status"
      aria-live="polite"
      aria-label={title}
    >
      <div className="work-machine-main">
        <div className="work-machine-core" aria-hidden>
          <span className="work-machine-ring work-machine-ring-a" />
          <span className="work-machine-ring work-machine-ring-b" />
          <span className="work-machine-hub">🦦</span>
        </div>

        <div className="work-machine-body">
          <p className="work-machine-title">{title}</p>
          <div className="work-machine-belt" aria-hidden>
            <div className="work-machine-belt-track">
              {[...chips, ...chips].map((chip, i) => (
                <span className="work-machine-chip" key={`${chip}-${i}`}>
                  {chip}
                </span>
              ))}
            </div>
          </div>
          <div className="work-machine-stages">
            {stages.map((stage, i) => (
              <span key={stage} className={i === active ? "work-machine-stage active" : "work-machine-stage"}>
                {stage}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
