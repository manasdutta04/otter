#!/usr/bin/env node
import { apiRequest, clearSession, loadConfig, loginWithBrowser, printJson, saveConfig } from "./client.js";

function usage(): never {
  console.log(`🦦 Otter CLI — engineering intelligence

Usage:
  otter login
  otter logout
  otter health
  otter repos list
  otter repos import <github-url>
  otter repos status <repository-id>
  otter analyze <repository-id>
  otter chat <repository-id> <question>
  otter plan <repository-id> <request>
  otter health-report <repository-id>
  otter review <repository-id>
  otter architect <repository-id>
  otter docs <repository-id>

Environment:
  OTTER_API_URL   API base (default http://localhost:8000)
  OTTER_SESSION   Session token (optional override)
`);
  process.exit(1);
}

async function main(): Promise<void> {
  const [, , command, ...rest] = process.argv;
  if (!command || command === "--help" || command === "-h") usage();

  try {
    if (command === "login") {
      const session = await loginWithBrowser();
      const config = loadConfig();
      saveConfig({ ...config, session });
      console.log("Logged in. Session saved to ~/.otter/config.json");
      return;
    }

    if (command === "logout") {
      clearSession();
      console.log("Logged out.");
      return;
    }

    if (command === "health") {
      printJson(await apiRequest("/health"));
      return;
    }

    if (command === "repos") {
      const sub = rest[0];
      if (sub === "list") {
        printJson(await apiRequest("/repositories"));
        return;
      }
      if (sub === "import") {
        const url = rest[1];
        if (!url) throw new Error("Usage: otter repos import <github-url>");
        printJson(await apiRequest("/repositories", { method: "POST", body: { url } }));
        return;
      }
      if (sub === "status") {
        const id = rest[1];
        if (!id) throw new Error("Usage: otter repos status <repository-id>");
        printJson(await apiRequest(`/repositories/${id}/import-status`));
        return;
      }
      throw new Error("Usage: otter repos list|import|status");
    }

    const id = rest[0];
    if (!id && !["health"].includes(command)) {
      throw new Error(`Missing repository id for \`${command}\``);
    }

    switch (command) {
      case "analyze":
        printJson(await apiRequest(`/repositories/${id}/intelligence`));
        break;
      case "chat": {
        const question = rest.slice(1).join(" ").trim();
        if (!question) throw new Error('Usage: otter chat <repository-id> "question"');
        printJson(await apiRequest(`/repositories/${id}/chat`, { method: "POST", body: { question } }));
        break;
      }
      case "plan": {
        const request = rest.slice(1).join(" ").trim();
        if (!request) throw new Error('Usage: otter plan <repository-id> "request"');
        printJson(await apiRequest(`/repositories/${id}/plans`, { method: "POST", body: { request } }));
        break;
      }
      case "health-report":
        printJson(await apiRequest(`/repositories/${id}/health`));
        break;
      case "review":
        printJson(await apiRequest(`/repositories/${id}/review`));
        break;
      case "architect":
        printJson(await apiRequest(`/repositories/${id}/architecture`));
        break;
      case "docs":
        printJson(await apiRequest(`/repositories/${id}/documents`));
        break;
      default:
        usage();
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

void main();
