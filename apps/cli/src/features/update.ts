import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";
import { PACKAGE_VERSION } from "../config.js";

const execFileAsync = promisify(execFile);
export const CLI_PACKAGE = "@otter-engg/cli";

export async function fetchLatestCliVersion(): Promise<string> {
  const { stdout } = await execFileAsync(
    "npm",
    ["view", CLI_PACKAGE, "version"],
    {
      encoding: "utf8",
      shell: true,
      timeout: 30_000,
    },
  );
  const version = stdout.trim();
  if (!/^\d+\.\d+\.\d+/.test(version)) {
    throw new Error(`Could not read latest version from npm (got: ${version || "empty"})`);
  }
  return version;
}

export async function installLatestCli(): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const child = spawn("npm", ["i", "-g", `${CLI_PACKAGE}@latest`], {
      stdio: "inherit",
      shell: true,
    });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`npm install exited with code ${code ?? "unknown"}`));
    });
  });
}

export function currentCliVersion(): string {
  return PACKAGE_VERSION;
}
