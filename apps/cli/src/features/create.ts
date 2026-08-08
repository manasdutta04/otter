import { simpleGit } from "simple-git";
import { runAgent } from "../agent/loop.js";
import { saveCodeTask, type RepositoryRow } from "../db/repos.js";
import { newId } from "../db/index.js";
import { createPullRequest, parseGithubUrl } from "../git/repos.js";
import { planChange } from "./workspace.js";
import { c } from "../tui/theme.js";
import { startWork } from "../tui/work.js";
import { confirmYn } from "../tui/prompt.js";

export type CreateOptions = {
  root: string;
  repo: RepositoryRow;
  request: string;
  openPr?: boolean;
  autoApprove?: boolean;
};

export async function createAndMaybePr(opts: CreateOptions): Promise<{ taskId: string; prUrl?: string }> {
  const taskId = newId("task_");
  saveCodeTask({
    id: taskId,
    repository_id: opts.repo.id,
    request: opts.request,
    status: "planning",
  });

  const planSpin = startWork("scan", "planning");
  let plan: { id: string; content: string };
  try {
    plan = await planChange(opts.repo, opts.root, opts.request);
    planSpin.succeed(c.ok(`Plan ${plan.id}`));
  } catch (err) {
    planSpin.fail(c.bad(err instanceof Error ? err.message : String(err)));
    throw err;
  }

  console.log(plan.content);
  console.log();

  // Engineer stages: plan → human approval → implement → validate (git dirty check)
  console.log(c.dim("Stage: await approval → implement → validate"));

  // --pr implies apply+PR; one confirm covers both unless --yes
  const applyLabel = opts.openPr
    ? "Approve plan and implement (then open PR)?"
    : "Approve plan and implement with the coding agent?";
  const ok = opts.autoApprove || (await confirmYn(applyLabel, false));
  if (!ok) {
    saveCodeTask({
      id: taskId,
      repository_id: opts.repo.id,
      request: opts.request,
      status: "cancelled",
    });
    console.log(c.dim("Cancelled."));
    return { taskId };
  }

  saveCodeTask({
    id: taskId,
    repository_id: opts.repo.id,
    request: opts.request,
    status: "implementing",
  });

  // After the plan confirm, never ask per-tool — that caused yy spam and blocked PRs.
  const autoApprove = true;

  console.log(
    c.muted(
      opts.openPr
        ? "Implementing (prefer edit tools; writes auto-approved) · then opening PR…"
        : "Implementing (prefer edit tools; writes auto-approved)…",
    ),
  );

  const git = simpleGit(opts.root);
  const before = await git.status();
  const beforeKey = new Set(before.files.map((f) => f.path));

  try {
    await runAgent(
      `Implement this request using the plan. Keep changes minimal and correct for THIS repo's real file layout.\n` +
        `Prefer the edit tool (old_string → new_string) over write/full-file rewrites whenever possible.\n` +
        `First glob/read existing server files (often server/routes.ts — NOT src/server unless it exists).\n` +
        `Emit valid JSON tool calls only (double quotes, never \\').\n\n` +
        `Stages already completed: understand → plan → approved.\n` +
        `Current stage: implement → then we validate via git status.\n\n` +
        `Request:\n${opts.request}\n\nPlan:\n${plan.content}`,
      {
        root: opts.root,
        autoApprove,
        onEvent: (msg) => console.log(msg),
      },
    );
  } catch (err) {
    console.log(c.bad(`✖ ${err instanceof Error ? err.message : String(err)}`));
    throw err;
  }

  const after = await git.status();
  const changed = after.files.filter((f) => !beforeKey.has(f.path) || f.working_dir !== " ");
  // Also count any dirty/staged files vs clean
  const dirty = after.files.length > 0;

  if (!dirty) {
    console.log(
      c.bad(
        "✖ No files were changed. The model likely emitted invalid tool JSON or wrong paths. Try /create again.",
      ),
    );
    saveCodeTask({
      id: taskId,
      repository_id: opts.repo.id,
      request: opts.request,
      status: "failed",
    });
    throw new Error("No local changes after coding agent — cannot open PR.");
  }

  console.log(c.ok(`✔ Changes applied (${after.files.length} file(s))`));
  for (const f of after.files.slice(0, 12)) {
    console.log(c.dim(`  ${f.path}`));
  }

  saveCodeTask({
    id: taskId,
    repository_id: opts.repo.id,
    request: opts.request,
    status: "applied",
  });

  let prUrl: string | undefined;
  const wantPr =
    opts.openPr ||
    (!opts.autoApprove && (await confirmYn("Open a pull request on GitHub?", false)));

  if (wantPr) {
    prUrl = await openPrForRepo(opts.repo, opts.root, opts.request, plan.content, taskId);
  } else {
    console.log(c.dim("Tip: run /pr to open a pull request for current changes."));
  }

  return { taskId, prUrl };
}

export async function openPrForRepo(
  repo: RepositoryRow,
  root: string,
  title: string,
  body: string,
  taskId?: string,
): Promise<string> {
  if (!repo.full_name || repo.url.startsWith("file://")) {
    throw new Error("PR needs a GitHub import. Use /import owner/repo first.");
  }

  const git = simpleGit(root);
  const status = await git.status();
  if (status.files.length === 0) {
    throw new Error(
      "No local changes to include in a PR. Re-run /create with a clearer request, or edit files first.",
    );
  }

  const { owner, repo: name } = parseGithubUrl(repo.full_name);
  const branch = `otter/task-${(taskId || newId("")).slice(-8)}`;
  const spin = startWork("import", "opening PR");
  try {
    const url = await createPullRequest({
      localPath: root,
      owner,
      repo: name,
      branch,
      title: title.slice(0, 72),
      body: `Created by Otter CLI 🦦\n\n## Summary\n${title}\n\n## Details\n${body.slice(0, 4000)}`,
    });
    spin.succeed(c.ok("PR opened"));
    console.log(c.brand(url));
    if (taskId) {
      saveCodeTask({
        id: taskId,
        repository_id: repo.id,
        request: title,
        status: "pr_opened",
        branch,
        pr_url: url,
      });
    }
    return url;
  } catch (err) {
    spin.fail(c.bad(err instanceof Error ? err.message : String(err)));
    throw err;
  }
}
