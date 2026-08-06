import * as vscode from "vscode";

function apiUrl(): string {
  return vscode.workspace.getConfiguration("veridexs").get<string>("apiUrl", "http://localhost:8000").replace(/\/$/, "");
}

async function call(path: string, method = "GET", body?: unknown): Promise<void> {
  const response = await fetch(`${apiUrl()}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.text();
  const document = await vscode.workspace.openTextDocument({ language: "json", content: payload });
  await vscode.window.showTextDocument(document, { preview: false });
}

export function activate(context: vscode.ExtensionContext): void {
  const repositoryId = async (): Promise<string | undefined> => vscode.window.showInputBox({ prompt: "veridexs repository ID" });
  context.subscriptions.push(
    vscode.commands.registerCommand("veridexs.explain", async () => { const id = await repositoryId(); if (id) await call(`/repositories/${id}/intelligence`); }),
    vscode.commands.registerCommand("veridexs.chat", async () => {
      const id = await repositoryId();
      const question = id ? await vscode.window.showInputBox({ prompt: "Ask grounded question about codebase" }) : undefined;
      if (id && question) await call(`/repositories/${id}/chat`, "POST", { question });
    }),
    vscode.commands.registerCommand("veridexs.review", async () => { const id = await repositoryId(); if (id) await call(`/repositories/${id}/review`); }),
    vscode.commands.registerCommand("veridexs.health", async () => { const id = await repositoryId(); if (id) await call(`/repositories/${id}/health`); }),
    vscode.commands.registerCommand("veridexs.plan", async () => {
      const id = await repositoryId();
      const request = id ? await vscode.window.showInputBox({ prompt: "What should veridexs plan?" }) : undefined;
      if (id && request) await call(`/repositories/${id}/plans`, "POST", { request });
    }),
    vscode.commands.registerCommand("veridexs.memory", async () => { const id = await repositoryId(); if (id) await call(`/repositories/${id}/memory`); }),
  );
}


export function deactivate(): void {}
