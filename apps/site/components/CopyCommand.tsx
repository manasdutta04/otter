"use client";

import { useState } from "react";

type CopyCommandProps = {
  command: string;
  className?: string;
  label?: string;
};

export function CopyCommand({ command, className, label = "Copy" }: CopyCommandProps) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className={`copy-command ${className ?? ""}`.trim()}>
      <pre>
        <code>{command}</code>
      </pre>
      <button type="button" className="copy-command-btn" onClick={onCopy}>
        {copied ? "Copied" : label}
      </button>
    </div>
  );
}
