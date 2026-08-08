import fs from "node:fs";
import path from "node:path";
import { globSync } from "glob";
import { chatCompletion } from "../llm/client.js";
import { saveHealth, saveIntelligence } from "../db/repos.js";

const SKIP_DIRS = new Set([
  "node_modules",
  ".git",
  "dist",
  "build",
  ".next",
  "coverage",
  "__pycache__",
  ".venv",
  "venv",
  ".otter",
]);

const EXT_LANG: Record<string, string> = {
  ".ts": "TypeScript",
  ".tsx": "TypeScript",
  ".js": "JavaScript",
  ".jsx": "JavaScript",
  ".py": "Python",
  ".go": "Go",
  ".rs": "Rust",
  ".java": "Java",
  ".rb": "Ruby",
  ".php": "PHP",
  ".cs": "C#",
  ".cpp": "C++",
  ".c": "C",
  ".md": "Markdown",
  ".json": "JSON",
  ".yml": "YAML",
  ".yaml": "YAML",
  ".toml": "TOML",
  ".sql": "SQL",
};

function walkFiles(root: string, limit = 400): string[] {
  const files: string[] = [];
  const walk = (dir: string) => {
    if (files.length >= limit) return;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const ent of entries) {
      if (files.length >= limit) break;
      if (ent.name.startsWith(".") && ent.name !== ".github") {
        if (ent.isDirectory()) continue;
      }
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        if (SKIP_DIRS.has(ent.name)) continue;
        walk(full);
      } else if (ent.isFile()) {
        files.push(path.relative(root, full).replace(/\\/g, "/"));
      }
    }
  };
  walk(root);
  return files;
}

function countLanguages(files: string[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const f of files) {
    const ext = path.extname(f).toLowerCase();
    const lang = EXT_LANG[ext];
    if (!lang) continue;
    counts[lang] = (counts[lang] || 0) + 1;
  }
  return counts;
}

function findTodos(root: string, files: string[]): Array<{ file: string; line: number; text: string }> {
  const hits: Array<{ file: string; line: number; text: string }> = [];
  const re = /(?:^|[^A-Za-z])(TODO|FIXME|HACK|XXX)\b/;
  for (const rel of files.slice(0, 200)) {
    const full = path.join(root, rel);
    let content: string;
    try {
      const stat = fs.statSync(full);
      if (stat.size > 200_000) continue;
      content = fs.readFileSync(full, "utf8");
    } catch {
      continue;
    }
    const lines = content.split(/\r?\n/);
    lines.forEach((line, i) => {
      if (!re.test(line) || hits.length >= 50) return;
      // Skip meta lines that only define the detector pattern itself.
      if (line.includes("TODO|FIXME") || line.includes("TODO/FIXME")) return;
      hits.push({ file: rel, line: i + 1, text: line.trim().slice(0, 160) });
    });
  }
  return hits;
}

function detectManifests(root: string): string[] {
  const names = [
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
  ];
  return names.filter((n) => fs.existsSync(path.join(root, n)));
}

export async function scanRepository(
  repositoryId: string,
  root: string,
  opts?: { useLlm?: boolean },
): Promise<{
  summary: string;
  languages: Record<string, number>;
  tree: string[];
  health: { score: number; findings: unknown[]; summary: string };
}> {
  const files = walkFiles(root);
  const languages = countLanguages(files);
  const tree = files.slice(0, 80);
  const manifests = detectManifests(root);
  const todos = findTodos(root, files);

  let summary = `Repository at ${root} with ${files.length} tracked files. Languages: ${
    Object.entries(languages)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([k, v]) => `${k} (${v})`)
      .join(", ") || "unknown"
  }. Manifests: ${manifests.join(", ") || "none"}.`;

  if (opts?.useLlm !== false) {
    try {
      const llmSummary = await chatCompletion([
        {
          role: "system",
          content:
            "You are Otter, an engineering-intelligence assistant. Summarize this repository in 2-4 sentences for a developer.",
        },
        {
          role: "user",
          content: `Path: ${root}\nManifests: ${manifests.join(", ")}\nLanguages: ${JSON.stringify(languages)}\nSample files:\n${tree.slice(0, 40).join("\n")}`,
        },
      ]);
      if (llmSummary) summary = llmSummary;
    } catch {
      /* keep heuristic summary */
    }
  }

  saveIntelligence(repositoryId, { summary, languages, tree, raw: { manifests, fileCount: files.length } });

  const findings: unknown[] = [];
  if (!fs.existsSync(path.join(root, "README.md"))) {
    findings.push({ severity: "medium", message: "Missing README.md" });
  }
  if (!manifests.some((m) => m.includes("lock") || m === "go.mod" || m === "Cargo.toml")) {
    findings.push({ severity: "low", message: "No lockfile detected" });
  }
  for (const t of todos.slice(0, 15)) {
    findings.push({
      severity: "info",
      message: `${t.file}:${t.line} ${t.text}`,
    });
  }

  let score = 80;
  score -= findings.filter((f) => (f as { severity: string }).severity === "medium").length * 8;
  score -= findings.filter((f) => (f as { severity: string }).severity === "low").length * 3;
  score = Math.max(10, Math.min(100, score));

  const healthSummary = `Health score ${score}/100 with ${findings.length} findings (${todos.length} TODO/FIXME markers).`;
  const health = { score, findings, summary: healthSummary };
  saveHealth(repositoryId, health);

  return { summary, languages, tree, health };
}

export function readRepoContext(root: string, maxFiles = 12): string {
  const patterns = [
    "README.md",
    "package.json",
    "pyproject.toml",
    "src/**/*.{ts,tsx,js,py}",
    "app/**/*.{ts,tsx,js,py}",
  ];
  const picked: string[] = [];
  for (const pattern of patterns) {
    const matches = globSync(pattern, {
      cwd: root,
      nodir: true,
      ignore: ["**/node_modules/**", "**/.git/**", "**/dist/**"],
    });
    for (const m of matches) {
      if (picked.length >= maxFiles) break;
      if (!picked.includes(m)) picked.push(m);
    }
  }
  const chunks: string[] = [];
  for (const rel of picked) {
    const full = path.join(root, rel);
    try {
      const text = fs.readFileSync(full, "utf8");
      chunks.push(`--- ${rel}\n${text.slice(0, 4000)}`);
    } catch {
      /* skip */
    }
  }
  return chunks.join("\n\n");
}
