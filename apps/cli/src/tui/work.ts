import ora, { type Ora } from "ora";
import { c } from "./theme.js";

const VERBS = [
  "Cooking",
  "Finding",
  "Thinking",
  "Reading",
  "Tracing",
  "Planning",
  "Diving",
] as const;

export type WorkKind = "agent" | "scan" | "import" | "login" | "model";

const LABELS: Record<WorkKind, string> = {
  agent: "Cooking",
  scan: "Scanning",
  import: "Importing",
  login: "Signing in",
  model: "Checking model",
};

export function startWork(kind: WorkKind, detail?: string): Ora {
  const label = LABELS[kind] || "Working";
  const text = detail ? `${label} · ${detail}` : `${label}…`;
  return ora({
    text: c.muted(text),
    color: "cyan",
    spinner: "dots",
  }).start();
}

/** Rotate cooking/finding verbs while a long agent turn runs. */
export function startAgentPulse(onVerb?: (verb: string) => void): {
  stop: (ok?: boolean, msg?: string) => void;
  set: (msg: string) => void;
} {
  let i = 0;
  const spin = ora({
    text: c.muted(`${VERBS[0]}…`),
    color: "cyan",
    spinner: "dots",
  }).start();

  const timer = setInterval(() => {
    i = (i + 1) % VERBS.length;
    const verb = VERBS[i];
    spin.text = c.muted(`${verb}…`);
    onVerb?.(verb);
  }, 1600);

  return {
    set(msg: string) {
      spin.text = c.muted(msg);
    },
    stop(ok = true, msg?: string) {
      clearInterval(timer);
      if (ok) spin.succeed(c.ok(msg || "Done"));
      else spin.fail(c.bad(msg || "Failed"));
    },
  };
}
