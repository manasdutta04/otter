export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const GITHUB_LOGIN_URL = `${API_URL}/auth/github/login`;
export const REFRESH_INTERVAL_MS = 5000;

export type LlmProvider = "ollama" | "openai_compatible";

export type LlmSettings = {
  provider: LlmProvider;
  base_url: string;
  model: string;
  api_key_set: boolean;
  api_key_masked: string;
  free_failover: boolean;
  configured: boolean;
};

export type LlmTestResult = {
  ok: boolean;
  reachable: boolean;
  completion_ok: boolean;
  models: string[];
  model: string;
  provider: string;
  base_url: string;
  detail: string;
};

export type RepoStatus = "queued" | "cloning" | "ready" | "failed";
export type MemoryKind = "decision" | "convention" | "note";
export type PlanComplexity = "low" | "medium" | "high";
export type CodeTaskStatus =
  | "draft"
  | "ready_for_approval"
  | "patch_ready"
  | "approved"
  | "rejected"
  | "applied";

export type Repository = {
  id: string;
  url: string;
  name: string;
  status: RepoStatus;
  created_at: string;
  branch?: string | null;
  file_count: number;
  error?: string | null;
};

export type ImportStatus = {
  job_id: string;
  repository_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  attempt_count: number;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};

export type FolderIntelligence = {
  path: string;
  role: string;
  file_count: number;
  explanation?: string | null;
};

export type IntelligenceAnalysis = {
  summary_facts: string[];
  languages: string[];
  package_managers: string[];
  frameworks: string[];
  api_routes: { method: string; path: string; file: string; line?: number | null }[];
  databases: { orm: string; evidence: string; files: string[] }[];
  auth: { mechanism: string; files: string[]; notes: string }[];
  config_files: string[];
  ci: string[];
  docker: string[];
  testing: string[];
  folder_explanations: Record<string, string>;
};

export type Intelligence = {
  repository_id: string;
  summary: string;
  tech_stack: string[];
  folders: Array<FolderIntelligence | string>;
  entry_points: string[];
  architecture_signals: string[];
  analysis?: IntelligenceAnalysis | null;
  analyzed_at: string;
};

export type ChatResponse = {
  answer: string;
  sources: string[];
  primary_file?: string | null;
  primary_lines?: string | null;
  excerpt?: string | null;
};

export type Plan = {
  id: string;
  repository_id: string;
  request: string;
  title: string;
  complexity: PlanComplexity;
  summary: string;
  steps: string[];
  affected_files: string[];
  dependencies: string[];
  risks: string[];
  created_at: string;
};

export type Memory = {
  id: string;
  repository_id: string;
  kind: string;
  title: string;
  content: string;
  created_at: string;
};

export type Document = {
  id: string;
  repository_id: string;
  kind: string;
  title: string;
  content: string;
  created_at: string;
};

export type CodeTask = {
  id: string;
  repository_id: string;
  plan_id: string | null;
  request: string;
  status: CodeTaskStatus;
  proposed_summary: string;
  changed_files: string[];
  approval_note: string | null;
  created_at: string;
  approved_at: string | null;
  applied_at: string | null;
};

export type HealthReport = {
  repository_id: string;
  architecture_score: number;
  security_score: number;
  maintainability_score: number;
  performance_score: number;
  debt_score: number;
  documentation_score: number;
  dependency_score: number;
  complexity_score: number;
  findings: string[];
  analyzed_at: string;
};

export type ReviewFinding = {
  category: string;
  severity: "low" | "medium" | "high";
  title: string;
  file: string;
  line: number;
};

export type ReviewResult = {
  id: string;
  repository_id: string;
  findings: ReviewFinding[];
  created_at: string;
};

export type ArchitectureGraph = {
  repository_id: string;
  nodes: { id: string; label: string; kind: string; path: string }[];
  edges: { source: string; target: string; kind: string }[];
  generated_at: string;
};

export type ArchitectureAnalysis = {
  repository_id: string;
  score: number;
  findings: Record<string, unknown>[];
  created_at: string;
};

export type PerformanceReport = {
  repository_id: string;
  score: number;
  hotspots: Record<string, unknown>[];
  created_at: string;
};

export type TestResult = {
  passed: boolean;
  output: string;
};

export type PullRequestResult = {
  url: string;
  number: number;
  branch: string;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string | { msg?: string }[] };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return data.detail[0].msg;
  } catch {
    /* ignore */
  }
  return `Request failed (${response.status})`;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Could not reach the Otter API. If the API just restarted, wait a second and try again.",
      0,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  if (response.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  getMe: () => apiFetch<{ authenticated: boolean }>("/auth/me"),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),

  listRepositories: () => apiFetch<{ repositories: Repository[] }>("/repositories"),
  createRepository: (url: string) =>
    apiFetch<Repository>("/repositories", { method: "POST", body: JSON.stringify({ url }) }),
  getRepository: (id: string) => apiFetch<Repository>(`/repositories/${id}`),

  getIntelligence: (id: string) => apiFetch<Intelligence>(`/repositories/${id}/intelligence`),
  getArchitecture: (id: string) => apiFetch<ArchitectureGraph>(`/repositories/${id}/architecture`),
  getArchitectureAnalysis: (id: string) =>
    apiFetch<ArchitectureAnalysis>(`/repositories/${id}/architecture-analysis`),
  getPerformance: (id: string) => apiFetch<PerformanceReport>(`/repositories/${id}/performance`),
  getHealth: (id: string) => apiFetch<HealthReport>(`/repositories/${id}/health`),
  getReview: (id: string) => apiFetch<ReviewResult>(`/repositories/${id}/review`),

  chat: (id: string, question: string) =>
    apiFetch<ChatResponse>(`/repositories/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  listPlans: (id: string) => apiFetch<Plan[]>(`/repositories/${id}/plans`),
  createPlan: (id: string, request: string) =>
    apiFetch<Plan>(`/repositories/${id}/plans`, {
      method: "POST",
      body: JSON.stringify({ request }),
    }),

  listMemory: (id: string) => apiFetch<Memory[]>(`/repositories/${id}/memory`),
  createMemory: (id: string, payload: { kind: MemoryKind; title: string; content: string }) =>
    apiFetch<Memory>(`/repositories/${id}/memory`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listDocuments: (id: string) => apiFetch<Document[]>(`/repositories/${id}/documents`),
  generateOverview: (id: string) =>
    apiFetch<Document>(`/repositories/${id}/documents/overview`, { method: "POST" }),

  listCodeTasks: (id: string) => apiFetch<CodeTask[]>(`/repositories/${id}/code-tasks`),
  createCodeTask: (id: string, request: string, planId?: string) =>
    apiFetch<CodeTask>(`/repositories/${id}/code-tasks`, {
      method: "POST",
      body: JSON.stringify({ request, plan_id: planId ?? null }),
    }),
  approveCodeTask: (id: string, taskId: string, note?: string) =>
    apiFetch<CodeTask>(`/repositories/${id}/code-tasks/${taskId}/approve`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),
  rejectCodeTask: (id: string, taskId: string, note?: string) =>
    apiFetch<CodeTask>(`/repositories/${id}/code-tasks/${taskId}/reject`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),
  generateCodeTask: (id: string, taskId: string) =>
    apiFetch<CodeTask>(`/repositories/${id}/code-tasks/${taskId}/generate`, { method: "POST" }),
  applyCodeTask: (id: string, taskId: string) =>
    apiFetch<CodeTask>(`/repositories/${id}/code-tasks/${taskId}/apply`, { method: "POST" }),
  testCodeTask: (id: string, taskId: string) =>
    apiFetch<TestResult>(`/repositories/${id}/code-tasks/${taskId}/test`, { method: "POST" }),
  createPullRequest: (
    id: string,
    taskId: string,
    payload: { title: string; body: string; base?: string },
  ) =>
    apiFetch<PullRequestResult>(`/repositories/${id}/code-tasks/${taskId}/pull-request`, {
      method: "POST",
      body: JSON.stringify({ title: payload.title, body: payload.body, base: payload.base ?? "main" }),
    }),

  getImportStatus: (id: string) => apiFetch<ImportStatus>(`/repositories/${id}/import-status`),
  retryImport: (id: string) =>
    apiFetch<ImportStatus>(`/repositories/${id}/retry-import`, { method: "POST" }),

  getLlmSettings: () => apiFetch<LlmSettings>("/settings/llm"),
  saveLlmSettings: (payload: {
    provider: LlmProvider;
    base_url: string;
    model: string;
    api_key?: string | null;
    free_failover: boolean;
    keep_existing_key?: boolean;
  }) =>
    apiFetch<LlmSettings>("/settings/llm", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  listLlmModels: () => apiFetch<{ models: string[]; provider: string; base_url: string }>("/settings/llm/models"),
  testLlmSettings: () => apiFetch<LlmTestResult>("/settings/llm/test", { method: "POST" }),
};
