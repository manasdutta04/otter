import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { globSync } from "glob";

export type ToolName = "read" | "write" | "edit" | "bash" | "glob" | "grep";

export type ToolCall = {
  name: ToolName;
  arguments: Record<string, string>;
};

export const TOOL_SPECS = [
  {
    type: "function" as const,
    function: {
      name: "read",
      description: "Read a file relative to the workspace root",
      parameters: {
        type: "object",
        properties: { path: { type: "string" } },
        required: ["path"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "write",
      description: "Write full contents to a file (creates parents)",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string" },
          content: { type: "string" },
        },
        required: ["path", "content"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "edit",
      description: "Replace exact old_string with new_string in a file",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string" },
          old_string: { type: "string" },
          new_string: { type: "string" },
        },
        required: ["path", "old_string", "new_string"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "bash",
      description: "Run a shell command in the workspace",
      parameters: {
        type: "object",
        properties: { command: { type: "string" } },
        required: ["command"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "glob",
      description: "Find files by glob pattern",
      parameters: {
        type: "object",
        properties: { pattern: { type: "string" } },
        required: ["pattern"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "grep",
      description: "Search file contents for a regex/string",
      parameters: {
        type: "object",
        properties: {
          pattern: { type: "string" },
          glob: { type: "string" },
        },
        required: ["pattern"],
      },
    },
  },
];

function resolveSafe(root: string, rel: string): string {
  const full = path.resolve(root, rel);
  const rootResolved = path.resolve(root);
  if (!full.startsWith(rootResolved + path.sep) && full !== rootResolved) {
    throw new Error(`Path escapes workspace: ${rel}`);
  }
  return full;
}

export function runTool(
  root: string,
  call: ToolCall,
  opts?: { allowWrite?: boolean },
): string {
  const allowWrite = opts?.allowWrite !== false;
  switch (call.name) {
    case "read": {
      const full = resolveSafe(root, call.arguments.path);
      return fs.readFileSync(full, "utf8").slice(0, 100_000);
    }
    case "write": {
      if (!allowWrite) throw new Error("Writes disabled");
      const full = resolveSafe(root, call.arguments.path);
      fs.mkdirSync(path.dirname(full), { recursive: true });
      fs.writeFileSync(full, call.arguments.content ?? "", "utf8");
      return `Wrote ${call.arguments.path}`;
    }
    case "edit": {
      if (!allowWrite) throw new Error("Writes disabled");
      const full = resolveSafe(root, call.arguments.path);
      const cur = fs.readFileSync(full, "utf8");
      const old = call.arguments.old_string ?? "";
      const neu = call.arguments.new_string ?? "";
      if (!cur.includes(old)) throw new Error("old_string not found");
      fs.writeFileSync(full, cur.replace(old, neu), "utf8");
      return `Edited ${call.arguments.path}`;
    }
    case "bash": {
      const cmd = call.arguments.command;
      if (!cmd) throw new Error("Missing command");
      try {
        const out = execSync(cmd, {
          cwd: root,
          encoding: "utf8",
          timeout: 120_000,
          maxBuffer: 2_000_000,
          shell: process.platform === "win32" ? "powershell.exe" : "/bin/bash",
        });
        return out.slice(0, 50_000) || "(no output)";
      } catch (err) {
        const e = err as { stdout?: string; stderr?: string; message?: string };
        return `Command failed:\n${e.stdout || ""}\n${e.stderr || e.message || ""}`.slice(0, 50_000);
      }
    }
    case "glob": {
      const matches = globSync(call.arguments.pattern || "**/*", {
        cwd: root,
        nodir: true,
        ignore: ["**/node_modules/**", "**/.git/**"],
      });
      return matches.slice(0, 200).join("\n") || "(no matches)";
    }
    case "grep": {
      const pattern = call.arguments.pattern;
      const g = call.arguments.glob || "**/*.{ts,tsx,js,jsx,py,md,json}";
      const files = globSync(g, {
        cwd: root,
        nodir: true,
        ignore: ["**/node_modules/**", "**/.git/**", "**/dist/**"],
      });
      const re = new RegExp(pattern, "i");
      const lines: string[] = [];
      for (const rel of files.slice(0, 100)) {
        let text: string;
        try {
          text = fs.readFileSync(path.join(root, rel), "utf8");
        } catch {
          continue;
        }
        text.split(/\r?\n/).forEach((line, i) => {
          if (re.test(line) && lines.length < 80) {
            lines.push(`${rel}:${i + 1}: ${line.trim().slice(0, 200)}`);
          }
        });
      }
      return lines.join("\n") || "(no matches)";
    }
    default:
      throw new Error(`Unknown tool`);
  }
}
