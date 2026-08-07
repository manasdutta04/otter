"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type LlmSettings } from "../lib/api";

export function ModelStatusChip() {
  const [settings, setSettings] = useState<LlmSettings | null>(null);
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const current = await api.getLlmSettings();
        if (cancelled) return;
        setSettings(current);
        const test = await api.testLlmSettings();
        if (!cancelled) setOk(test.ok);
      } catch {
        if (!cancelled) {
          setSettings(null);
          setOk(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const label = settings?.model || "Configure model";
  const tone = ok === true ? "ok" : ok === false ? "bad" : "muted";
  const provider =
    settings?.provider === "ollama"
      ? "Ollama"
      : settings?.provider === "openai_compatible"
        ? "OpenAI-compat"
        : null;

  return (
    <Link href="/app/models" className={`model-chip model-chip-${tone}`} title="Model Providers">
      <span className="model-chip-dot" aria-hidden />
      <span className="model-chip-text">
        {provider ? <span className="model-chip-provider">{provider}</span> : null}
        <span className="model-chip-label">{label}</span>
      </span>
    </Link>
  );
}
