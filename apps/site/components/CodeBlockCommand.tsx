"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
  type SVGProps,
} from "react";

export type PackageManager = "docker" | "prompt" | "pnpm" | "yarn" | "npm" | "bun";

const STORAGE_KEY = "packageManager";

function readStoredManager(fallback: PackageManager): PackageManager {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;
    const value = JSON.parse(raw) as string;
    if (
      value === "docker" ||
      value === "prompt" ||
      value === "pnpm" ||
      value === "yarn" ||
      value === "npm" ||
      value === "bun"
    ) {
      return value;
    }
  } catch {
    /* ignore */
  }
  return fallback;
}

export type CodeBlockCommandProps = {
  /** Optional Docker install command (Otter extension of the ncdai model). */
  docker?: string;
  /** Natural language instruction for AI agents. */
  prompt?: string;
  pnpm?: string;
  yarn?: string;
  npm?: string;
  bun?: string;
  className?: string;
  size?: "hero" | "docs";
  /** Preferred tab when nothing is stored yet. */
  defaultTab?: PackageManager;
  onCopySuccess?: (data: { packageManager: PackageManager; command: string }) => void;
  onCopyError?: (error: Error) => void;
};

/**
 * Package-manager command block modeled on
 * https://github.com/ncdai/chanhdai.com `CodeBlockCommand`
 * (tabs + icons + copy + persisted preference).
 */
export function CodeBlockCommand({
  docker,
  prompt,
  pnpm,
  yarn,
  npm,
  bun,
  className,
  size = "hero",
  defaultTab,
  onCopySuccess,
  onCopyError,
}: CodeBlockCommandProps) {
  const tabs = useMemo(
    () => ({ docker, prompt, pnpm, yarn, npm, bun }),
    [docker, prompt, pnpm, yarn, npm, bun],
  );

  const tabsFiltered = useMemo(
    () => Object.entries(tabs).filter(([, value]) => !!value) as Array<[PackageManager, string]>,
    [tabs],
  );

  const initial =
    defaultTab && tabs[defaultTab]
      ? defaultTab
      : (tabsFiltered[0]?.[0] ?? "npm");

  const [packageManager, setPackageManager] = useState<PackageManager>(initial);
  const [hydrated, setHydrated] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "done" | "error">("idle");

  useEffect(() => {
    const stored = readStoredManager(initial);
    const next = tabs[stored] ? stored : initial;
    setPackageManager(next);
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hydrate once from storage
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!tabs[packageManager]) {
      setPackageManager(initial);
    }
  }, [hydrated, tabs, packageManager, initial]);

  const select = useCallback((value: PackageManager) => {
    setPackageManager(value);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } catch {
      /* ignore */
    }
  }, []);

  const activeCommand = tabs[packageManager] || "";

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(activeCommand);
      setCopyState("done");
      onCopySuccess?.({ packageManager, command: activeCommand });
      window.setTimeout(() => setCopyState("idle"), 1600);
    } catch (err) {
      setCopyState("error");
      onCopyError?.(err instanceof Error ? err : new Error(String(err)));
      window.setTimeout(() => setCopyState("idle"), 1600);
    }
  }

  return (
    <div
      className={`cbc cbc-${size} ${className ?? ""}`.trim()}
      data-slot="code-block-command"
    >
      <div className="cbc-toolbar">
        <div className="cbc-tabs" role="tablist" aria-label="Package managers">
          <span className="cbc-pm-icon" aria-hidden>
            {getIconForPackageManager(packageManager)}
          </span>
          {tabsFiltered.map(([key]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={packageManager === key}
              className={`cbc-tab${packageManager === key ? " is-active" : ""}`}
              onClick={() => select(key)}
            >
              {key}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="cbc-copy"
          onClick={onCopy}
          aria-label="Copy"
          title="Copy"
        >
          {copyState === "done" ? <CheckIcon /> : copyState === "error" ? <XIcon /> : <CopyIcon />}
        </button>
      </div>

      {tabsFiltered.map(([key, value]) =>
        packageManager === key ? (
          <pre key={key} className="cbc-pre" data-pm={key} role="tabpanel">
            <code className="cbc-code" data-language="bash">
              {key !== "prompt" && key !== "docker" ? (
                <span className="cbc-prompt-char">$ </span>
              ) : null}
              {value}
            </code>
          </pre>
        ) : null,
      )}
    </div>
  );
}

export type ConvertNpmCommandResult = {
  pnpm: string;
  yarn: string;
  npm: string;
  bun: string;
};

/** Same conversion rules as ncdai/chanhdai.com `convertNpmCommand`, plus `npm i`. */
export function convertNpmCommand(npmCommand: string): ConvertNpmCommandResult {
  if (npmCommand.startsWith("npm install") || npmCommand.startsWith("npm i ")) {
    const rest = npmCommand.replace(/^npm (install|i)\s+/, "");
    const global = /(?:^|\s)-g(?:\s|$)/.test(` ${rest} `) || rest.includes("--global");
    const pkg = rest.replace(/(?:^|\s)(-g|--global)\s*/g, " ").trim();
    if (global) {
      return {
        pnpm: `pnpm add -g ${pkg}`,
        yarn: `yarn global add ${pkg}`,
        npm: npmCommand.startsWith("npm i ") ? `npm i -g ${pkg}` : `npm install -g ${pkg}`,
        bun: `bun add -g ${pkg}`,
      };
    }
    return {
      pnpm: `pnpm add ${pkg}`,
      yarn: `yarn add ${pkg}`,
      npm: npmCommand,
      bun: `bun add ${pkg}`,
    };
  }

  if (npmCommand.startsWith("npx create-")) {
    return {
      pnpm: npmCommand.replace("npx create-", "pnpm create "),
      yarn: npmCommand.replace("npx create-", "yarn create "),
      npm: npmCommand,
      bun: npmCommand.replace("npx", "bunx --bun"),
    };
  }

  if (npmCommand.startsWith("npm create")) {
    return {
      pnpm: npmCommand.replace("npm create", "pnpm create"),
      yarn: npmCommand.replace("npm create", "yarn create"),
      npm: npmCommand,
      bun: npmCommand.replace("npm create", "bun create"),
    };
  }

  if (npmCommand.startsWith("npx")) {
    return {
      pnpm: npmCommand.replace("npx", "pnpm dlx"),
      yarn: npmCommand.replace("npx", "yarn dlx"),
      npm: npmCommand,
      bun: npmCommand.replace("npx", "bunx --bun"),
    };
  }

  if (npmCommand.startsWith("npm run")) {
    return {
      pnpm: npmCommand.replace("npm run", "pnpm"),
      yarn: npmCommand.replace("npm run", "yarn"),
      npm: npmCommand,
      bun: npmCommand.replace("npm run", "bun"),
    };
  }

  return {
    pnpm: npmCommand,
    yarn: npmCommand,
    npm: npmCommand,
    bun: npmCommand,
  };
}

function getIconForPackageManager(manager: PackageManager): ReactNode {
  switch (manager) {
    case "docker":
      return <DockerGlyph />;
    case "prompt":
      return <AlignLeftIcon />;
    case "pnpm":
      return <PnpmGlyph />;
    case "yarn":
      return <YarnGlyph />;
    case "npm":
      return <NpmGlyph />;
    case "bun":
      return <BunGlyph />;
    default:
      return <TerminalIcon />;
  }
}

function svgProps(props?: SVGProps<SVGSVGElement>): SVGProps<SVGSVGElement> {
  return {
    width: 16,
    height: 16,
    viewBox: "0 0 24 24",
    fill: "currentColor",
    "aria-hidden": true,
    ...props,
  };
}

function CopyIcon() {
  return (
    <svg {...svgProps()} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg {...svgProps()} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg {...svgProps()} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

function AlignLeftIcon() {
  return (
    <svg {...svgProps()} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 6H3M15 12H3M17 18H3" />
    </svg>
  );
}

function TerminalIcon() {
  return (
    <svg {...svgProps()} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m4 17 6-5-6-5M12 19h8" />
    </svg>
  );
}

function PnpmGlyph() {
  return (
    <svg {...svgProps()} viewBox="0 0 24 24">
      <path d="M0 0v7.5h7.5V0zm8.25 0v7.5h7.498V0zm8.25 0v7.5H24V0zM8.25 8.25v7.5h7.498v-7.5zm8.25 0v7.5H24v-7.5zM0 16.5V24h7.5v-7.5zm8.25 0V24h7.498v-7.5zm8.25 0V24H24v-7.5z" />
    </svg>
  );
}

function YarnGlyph() {
  return (
    <svg {...svgProps()} viewBox="0 0 24 24">
      <path d="M12 0C5.375 0 0 5.375 0 12s5.375 12 12 12 12-5.375 12-12S18.625 0 12 0zm.768 4.105c.183 0 .363.053.525.157.125.083.287.185.755 1.154.31-.088.468-.042.551-.019.204.056.366.19.463.375.477.917.542 2.553.334 3.605-.241 1.232-.755 2.029-1.131 2.576.324.329.778.899 1.117 1.825.278.774.31 1.478.273 2.015a5.51 5.51 0 0 0 .602-.329c.593-.366 1.487-.917 2.553-.931.714-.009 1.269.445 1.353 1.103a1.23 1.23 0 0 1-.945 1.362c-.649.158-.95.278-1.821.843-1.232.797-2.539 1.242-3.012 1.39a1.686 1.686 0 0 1-.704.343c-.737.181-3.266.315-3.466.315h-.046c-.783 0-1.214-.241-1.45-.491-.658.329-1.51.19-2.122-.134a1.078 1.078 0 0 1-.58-1.153 1.243 1.243 0 0 1-.153-.195c-.162-.25-.528-.936-.454-1.946.056-.723.556-1.367.88-1.71a5.522 5.522 0 0 1 .408-2.256c.306-.727.885-1.348 1.32-1.737-.32-.537-.644-1.367-.329-2.21.227-.602.412-.936.82-1.08h-.005c.199-.074.389-.153.486-.259a3.418 3.418 0 0 1 2.298-1.103c.037-.093.079-.185.125-.283.31-.658.639-1.029 1.024-1.168a.94.94 0 0 1 .328-.06z" />
    </svg>
  );
}

function NpmGlyph() {
  return (
    <svg {...svgProps()} viewBox="0 0 24 24">
      <path d="M1.763 0C.786 0 0 .786 0 1.763v20.474C0 23.214.786 24 1.763 24h20.474c.977 0 1.763-.786 1.763-1.763V1.763C24 .786 23.214 0 22.237 0zM5.13 5.323l13.837.019-.009 13.836h-3.464l.01-10.382h-3.456L12.04 19.17H5.113z" />
    </svg>
  );
}

function BunGlyph() {
  return (
    <svg {...svgProps()} viewBox="0 0 24 24">
      <path d="M12 22.596c6.628 0 12-4.338 12-9.688 0-3.318-2.057-6.248-5.219-7.986-1.286-.715-2.297-1.357-3.139-1.89C14.058 2.025 13.08 1.404 12 1.404c-1.097 0-2.334.785-3.966 1.821a49.92 49.92 0 0 1-2.816 1.697C2.057 6.66 0 9.59 0 12.908c0 5.35 5.372 9.687 12 9.687v.001Z" />
    </svg>
  );
}

function DockerGlyph() {
  return (
    <svg {...svgProps()} viewBox="0 0 24 24">
      <path d="M4.82 17.11c-.1 0-.17-.03-.25-.07-.5-.32-.1-2.12.53-3.57.54-1.23 1.48-2.25 2.5-2.55.2-.06.33.02.38.12.05.1 0 .28-.15.42-.68.66-1.2 1.66-1.45 2.6-.3 1.1-.2 1.95.1 2.15.05.03.1.05.16.05.2 0 .45-.18.7-.48.4-.48.82-1.25 1.05-1.9.1-.3.35-.4.55-.25.2.15.25.42.15.72-.35 1.05-1.05 2.2-1.85 2.7-.35.22-.75.31-1.07.31-.3 0-.55-.08-.75-.15zm14.7-1.05c-.95 1.55-2.7 2.4-5.05 2.4H4.55c-.35 0-.55-.25-.45-.55.55-1.65 1.85-2.7 3.55-2.85.15-.02.3.08.35.22.4 1.05 1.15 1.7 2.05 1.7.55 0 1.05-.25 1.45-.7.35-.4.55-.9.6-1.4.02-.2.2-.35.4-.32 1.75.25 3.15 1.15 3.95 2.45.12.2.02.45-.2.55-.25.15-.5.3-.78.45-.12.06-.18.2-.12.32.06.12.2.18.32.12.35-.15.65-.35.95-.55.15-.1.35-.05.45.1.1.15.05.35-.1.45zM9.2 11.85h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35H9.2c-.2 0-.35-.15-.35-.35v-1.55c0-.2.15-.35.35-.35zm-2.25 0h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35H6.95c-.2 0-.35-.15-.35-.35v-1.55c0-.2.15-.35.35-.35zm-2.25 0h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35H4.7c-.2 0-.35-.15-.35-.35v-1.55c0-.2.15-.35.35-.35zm4.5-2.25h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35H9.2c-.2 0-.35-.15-.35-.35V9.95c0-.2.15-.35.35-.35zm-2.25 0h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35H6.95c-.2 0-.35-.15-.35-.35V9.95c0-.2.15-.35.35-.35zm4.5 2.25h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35h-1.55c-.2 0-.35-.15-.35-.35v-1.55c0-.2.15-.35.35-.35zm0-2.25h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35h-1.55c-.2 0-.35-.15-.35-.35V9.95c0-.2.15-.35.35-.35zm0-2.25h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35h-1.55c-.2 0-.35-.15-.35-.35V7.7c0-.2.15-.35.35-.35zm-2.25 2.25h1.55c.2 0 .35.15.35.35v1.55c0 .2-.15.35-.35.35H9.2c-.2 0-.35-.15-.35-.35V9.95c0-.2.15-.35.35-.35z" />
    </svg>
  );
}
