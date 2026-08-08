import readline from "node:readline";
import { simpleGit } from "simple-git";
import { runAgent } from "../agent/loop.js";
import { saveCodeTask, type RepositoryRow } from "../db/repos.js";
import { newId } from "../db/index.js";
import { createPullRequest, parseGithubUrl } from "../git/repos.js";
import { planChange } from "./workspace.js";
import { c } from "../tui/theme.js";
import { startAgentPulse, startWork } from "../tui/work.js";

export type CreateOptions = {
  root: string;
  repo: RepositoryRow;
  request: string;
  openPr?: boolean;
  autoApprove?: boolean;
};

async function confirm(question: string): Promise<boolean> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const answer = await new Promise<string>((resolve) => rl.question(`${question} [y/N] `, resolve));
  rl.close();
  return /^y(es)?$/i.test(answer.trim());
}

export async function createAndMaybePr(opts: CreateOptions): Promise<{ taskId: string; prUrl?: string }> {
  const taskId = newId("task_");
  saveCodeTask({
    id: taskId,
    repository_id: opts.repo.id,
    request: opts.request,
    status: "planning",
  });

  const planSpin = startWork("scan", "planning");
  const plan = await planChange(opts.repo, opts.root, opts.request);
  planSpin.succeed(c.ok(`Plan ${plan.id}`));
  console.log(plan.content);
  console.log();

  const ok = opts.autoApprove || (await confirm("Apply this plan with the coding agent?"));
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

  const pulse = startAgentPulse();
  let saw = false;
  try {
    await runAgent(
      `Implement this request using the plan. Keep changes minimal.\n\nRequest:\n${opts.request}\n\nPlan:\n${plan.content}`,
      {
        root: opts.root,
        autoApprove: opts.autoApprove,
        onEvent: (msg) => {
          if (!saw) {
            pulse.stop(true, "Cooking");
            saw = true;
          }
          console.log(msg);
        },
      },
    );
    if (!saw) pulse.stop(true, "Applied");
    else console.log(c.ok("✔ Changes applied"));
  } catch (err) {
    pulse.stop(false, err instanceof Error ? err.message : String(err));
    throw err;
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
    (!opts.autoApprove && (await confirm("Open a pull request on GitHub?")));

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
    throw new Error("No local changes to include in a PR.");
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
    spin.succeed(c.ok(`PR opened`));
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
