"use client";

import { useEffect, useMemo, useState } from "react";

type CopyCommandProps = {
  /** Fixed command. If omitted with useComposeUrl, builds from current origin. */
  command?: string;
  /** Build: docker compose -f {origin}/docker-compose.yml up -d */
  useComposeUrl?: boolean;
  className?: string;
  /** button = whole control is the command (landing); block = code box with Copy */
  variant?: "button" | "block";
};

function buildComposeCommand(origin: string) {
  return `docker compose -f ${origin}/docker-compose.yml up -d`;
}

export function CopyCommand({
  command: commandProp,
  useComposeUrl = false,
  className,
  variant = "block",
}: CopyCommandProps) {
  const [origin, setOrigin] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  const command = useMemo(() => {
    if (commandProp) return commandProp;
    if (useComposeUrl && origin) return buildComposeCommand(origin);
    if (useComposeUrl) return "docker compose -f <site>/docker-compose.yml up -d";
    return "";
  }, [commandProp, useComposeUrl, origin]);

  async function onCopy() {
    if (!command || command.includes("<site>")) return;
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  if (variant === "button") {
    return (
      <button
        type="button"
        className={`copy-command-pill ${className ?? ""}`.trim()}
        onClick={onCopy}
        title="Click to copy"
        aria-label="Copy Docker run command"
      >
        <code className="copy-command-pill-text">{command}</code>
        <span className="copy-command-pill-action">{copied ? "Copied" : "Copy"}</span>
      </button>
    );
  }

  return (
    <div className={`copy-command ${className ?? ""}`.trim()}>
      <pre>
        <code>{command}</code>
      </pre>
      <button type="button" className="copy-command-btn" onClick={onCopy}>
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}
