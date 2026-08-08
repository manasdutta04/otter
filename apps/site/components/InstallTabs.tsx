"use client";

import {
  CodeBlockCommand,
  convertNpmCommand,
  type PackageManager,
} from "./CodeBlockCommand";
import { CLI_INSTALL_NPM, DOCKER_PULL } from "../lib/urls";

type InstallTabsProps = {
  className?: string;
  size?: "hero" | "docs";
  /** Include Docker pull as a first tab (landing / self-host). */
  showDocker?: boolean;
  defaultTab?: PackageManager;
};

/**
 * Otter install surface on top of the ncdai-style CodeBlockCommand
 * (https://github.com/ncdai/chanhdai.com).
 */
export function InstallTabs({
  className,
  size = "hero",
  showDocker = false,
  defaultTab,
}: InstallTabsProps) {
  const converted = convertNpmCommand(CLI_INSTALL_NPM);

  return (
    <CodeBlockCommand
      className={className}
      size={size}
      defaultTab={defaultTab ?? (showDocker ? "docker" : "npm")}
      docker={showDocker ? DOCKER_PULL : undefined}
      pnpm={converted.pnpm}
      yarn={converted.yarn}
      npm={converted.npm}
      bun={converted.bun}
    />
  );
}
