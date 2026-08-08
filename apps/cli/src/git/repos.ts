import fs from "node:fs";
import path from "node:path";
import { simpleGit } from "simple-git";
import { Octokit } from "@octokit/rest";
import {
  getLinkedRepoId,
  getRepository,
  getRepositoryByPath,
  linkProject,
  listRepositories,
  upsertRepository,
  type RepositoryRow,
} from "../db/repos.js";
import { newId } from "../db/index.js";
import { loadConfig, requireAuth, reposRoot, saveConfig } from "../config.js";

export function parseGithubUrl(input: string): { owner: string; repo: string; url: string } {
  const cleaned = input.trim().replace(/\.git$/, "");
  const https = cleaned.match(/^https?:\/\/github\.com\/([^/]+)\/([^/]+)/i);
  if (https) {
    return { owner: https[1], repo: https[2], url: `https://github.com/${https[1]}/${https[2]}` };
  }
  const ssh = cleaned.match(/^git@github\.com:([^/]+)\/([^/]+)/i);
  if (ssh) {
    return { owner: ssh[1], repo: ssh[2], url: `https://github.com/${ssh[1]}/${ssh[2]}` };
  }
  const short = cleaned.match(/^([^/]+)\/([^/]+)$/);
  if (short) {
    return { owner: short[1], repo: short[2], url: `https://github.com/${short[1]}/${short[2]}` };
  }
  throw new Error(`Unrecognized GitHub URL: ${input}`);
}

export async function importRepository(githubUrl: string, cwd = process.cwd()): Promise<RepositoryRow> {
  const auth = requireAuth();
  const { owner, repo, url } = parseGithubUrl(githubUrl);
  const id = newId("repo_");
  const localPath = path.join(reposRoot(), id);
  fs.mkdirSync(localPath, { recursive: true });

  const cloneUrl = `https://x-access-token:${auth.accessToken}@github.com/${owner}/${repo}.git`;
  const git = simpleGit();
  await git.clone(cloneUrl, localPath, ["--depth", "1"]);

  const localGit = simpleGit(localPath);
  await localGit.remote(["set-url", "origin", `https://github.com/${owner}/${repo}.git`]);

  const row = upsertRepository({
    id,
    url,
    full_name: `${owner}/${repo}`,
    local_path: localPath,
    status: "imported",
  });
  // Link both the caller's cwd and the clone path so later ensureProjectRepo works.
  linkProject(cwd, row.id);
  linkProject(localPath, row.id);
  const cfg = loadConfig();
  cfg.activeRepoId = row.id;
  saveConfig(cfg);
  return row;
}

export function resolveWorkRoot(explicitPath?: string): { root: string; repositoryId?: string } {
  if (explicitPath) {
    const resolved = path.resolve(explicitPath);
    const byPath = getRepositoryByPath(resolved);
    return { root: resolved, repositoryId: byPath?.id };
  }

  const cwd = process.cwd();
  const linked = getLinkedRepoId(cwd);
  if (linked) {
    const repo = getRepository(linked);
    if (repo) return { root: repo.local_path, repositoryId: repo.id };
  }

  const active = loadConfig().activeRepoId;
  if (active) {
    const repo = getRepository(active);
    if (repo) return { root: repo.local_path, repositoryId: repo.id };
  }

  if (fs.existsSync(path.join(cwd, ".git")) || fs.existsSync(path.join(cwd, "package.json"))) {
    const byPath = getRepositoryByPath(cwd);
    return { root: cwd, repositoryId: byPath?.id };
  }

  const repos = listRepositories();
  if (repos[0]) return { root: repos[0].local_path, repositoryId: repos[0].id };
  return { root: cwd };
}

export function ensureProjectRepo(cwd = process.cwd()): RepositoryRow {
  const resolved = path.resolve(cwd);

  // Prefer exact path match (imported clones live under ~/.otter/repos/...).
  const byPath = getRepositoryByPath(resolved);
  if (byPath) {
    linkProject(resolved, byPath.id);
    return byPath;
  }

  const linked = getLinkedRepoId(resolved) || getLinkedRepoId(cwd);
  if (linked) {
    const existing = getRepository(linked);
    if (existing) return existing;
  }

  const active = loadConfig().activeRepoId;
  if (active) {
    const repo = getRepository(active);
    if (repo && path.resolve(repo.local_path) === resolved) return repo;
  }

  const row = upsertRepository({
    url: `file://${resolved}`,
    full_name: path.basename(resolved),
    local_path: resolved,
    status: "local",
  });
  linkProject(resolved, row.id);
  return row;
}

export async function createPullRequest(opts: {
  localPath: string;
  owner: string;
  repo: string;
  branch: string;
  title: string;
  body: string;
  base?: string;
}): Promise<string> {
  const auth = requireAuth();
  const git = simpleGit(opts.localPath);

  // Prefer remote default branch when base not specified.
  let base = opts.base;
  if (!base) {
    try {
      const remote = await new Octokit({
        auth: auth.accessToken,
        userAgent: "otter-engg",
      }).repos.get({ owner: opts.owner, repo: opts.repo });
      base = remote.data.default_branch || "main";
    } catch {
      base = "main";
    }
  }

  const branches = await git.branchLocal();
  if (branches.all.includes(opts.branch)) {
    await git.checkout(opts.branch);
  } else {
    await git.checkoutLocalBranch(opts.branch);
  }
  await git.add(".");
  const status = await git.status();
  if (status.files.length === 0 && status.staged.length === 0) {
    throw new Error("No changes to commit for PR");
  }
  const commitMsg = `otter: ${opts.title}`.slice(0, 72);
  await git.commit(commitMsg);

  const remoteUrl = `https://x-access-token:${auth.accessToken}@github.com/${opts.owner}/${opts.repo}.git`;
  await git.push(remoteUrl, opts.branch, ["-u"]);

  const octokit = new Octokit({ auth: auth.accessToken, userAgent: "otter-engg" });
  try {
    const pr = await octokit.pulls.create({
      owner: opts.owner,
      repo: opts.repo,
      title: opts.title,
      head: opts.branch,
      base,
      body: opts.body,
    });
    return pr.data.html_url;
  } catch (err) {
    // Fallback if default branch guess was wrong
    if (base !== "master") {
      const pr = await octokit.pulls.create({
        owner: opts.owner,
        repo: opts.repo,
        title: opts.title,
        head: opts.branch,
        base: "master",
        body: opts.body,
      });
      return pr.data.html_url;
    }
    throw err;
  }
}
