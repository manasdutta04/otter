"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
function apiUrl() {
    return vscode.workspace.getConfiguration("veridexs").get("apiUrl", "http://localhost:8000").replace(/\/$/, "");
}
async function call(path, method = "GET", body) {
    const response = await fetch(`${apiUrl()}${path}`, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
    });
    const payload = await response.text();
    const document = await vscode.workspace.openTextDocument({ language: "json", content: payload });
    await vscode.window.showTextDocument(document, { preview: false });
}
function activate(context) {
    const repositoryId = async () => vscode.window.showInputBox({ prompt: "veridexs repository ID" });
    context.subscriptions.push(vscode.commands.registerCommand("veridexs.explain", async () => { const id = await repositoryId(); if (id)
        await call(`/repositories/${id}/intelligence`); }), vscode.commands.registerCommand("veridexs.review", async () => { const id = await repositoryId(); if (id)
        await call(`/repositories/${id}/review`); }), vscode.commands.registerCommand("veridexs.plan", async () => {
        const id = await repositoryId();
        const request = id ? await vscode.window.showInputBox({ prompt: "What should veridexs plan?" }) : undefined;
        if (id && request)
            await call(`/repositories/${id}/plans`, "POST", { request });
    }));
}
function deactivate() { }
//# sourceMappingURL=extension.js.map