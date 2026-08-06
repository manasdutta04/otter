import * as vscode from "vscode";

function apiUrl(): string {
  return vscode.workspace.getConfiguration("otter").get<string>("apiUrl", "http://localhost:8000").replace(/\/$/, "");
}

function session(): string {
  return vscode.workspace.getConfiguration("otter").get<string>("session", "") || process.env.OTTER_SESSION || "";
}

async function call(path: string, init?: RequestInit): Promise<void> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const token = session();
  if (token) {
    headers.Cookie = `otter_session=${token}`;
    headers["X-Otter-Session"] = token;
  }
  const response = await fetch(`${apiUrl()}${path}`, { ...init, headers });
  const text = await response.text();
  const doc = await vscode.workspace.openTextDocument({
    content: text,
    language: "json",
  });
  await vscode.window.showTextDocument(doc, { preview: false });
  if (!response.ok) {
    throw new Error(`Otter API ${response.status}`);
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const repositoryId = async (): Promise<string | undefined> =>
    vscode.window.showInputBox({ prompt: "Otter repository ID" });

  context.subscriptions.push(
    vscode.commands.registerCommand("otter.explain", async () => {
      const id = await repositoryId();
      if (id) await call(`/repositories/${id}/intelligence`);
    }),
    vscode.commands.registerCommand("otter.chat", async () => {
      const id = await repositoryId();
      const question = id ? await vscode.window.showInputBox({ prompt: "Ask Otter about this repository" }) : undefined;
      if (id && question) {
        await call(`/repositories/${id}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        });
      }
    }),
    vscode.commands.registerCommand("otter.review", async () => {
      const id = await repositoryId();
      if (id) await call(`/repositories/${id}/review`);
    }),
    vscode.commands.registerCommand("otter.health", async () => {
      const id = await repositoryId();
      if (id) await call(`/repositories/${id}/health`);
    }),
    vscode.commands.registerCommand("otter.plan", async () => {
      const id = await repositoryId();
      const request = id ? await vscode.window.showInputBox({ prompt: "What should Otter plan?" }) : undefined;
      if (id && request) {
        await call(`/repositories/${id}/plans`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ request }),
        });
      }
    }),
    vscode.commands.registerCommand("otter.memory", async () => {
      const id = await repositoryId();
      if (id) await call(`/repositories/${id}/memory`);
    }),
  );
}

export function deactivate(): void {}
