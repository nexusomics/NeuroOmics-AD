/** API client with JWT auth, error normalization and upload/download helpers. */
import type {
  Analysis, Artifact, Dataset, DrugCandidate, Project, ProjectSummary, TokenResponse, User,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";
const TOKEN_KEY = "neuroomics_access_token";
const REFRESH_KEY = "neuroomics_refresh_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/**
 * Sandbox-safe storage: in embedded previews (sandboxed iframes without
 * same-origin) `localStorage` throws a SecurityError and would crash the app
 * on boot. We fall back to an in-memory store so the UI still works there;
 * in a normal browser tab tokens persist as usual.
 */
const memoryStore = new Map<string, string>();
const storage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return memoryStore.get(key) ?? null;
    }
  },
  set(key: string, value: string) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      memoryStore.set(key, value);
    }
  },
  remove(key: string) {
    try {
      window.localStorage.removeItem(key);
    } catch {
      memoryStore.delete(key);
    }
  },
};

export const authStore = {
  get token() {
    return storage.get(TOKEN_KEY);
  },
  get refresh() {
    return storage.get(REFRESH_KEY);
  },
  set(tokens: { access_token: string; refresh_token: string }) {
    storage.set(TOKEN_KEY, tokens.access_token);
    storage.set(REFRESH_KEY, tokens.refresh_token);
  },
  clear() {
    storage.remove(TOKEN_KEY);
    storage.remove(REFRESH_KEY);
  },
};

async function raw<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = authStore.token;
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && retry && authStore.refresh) {
    const ok = await tryRefresh();
    if (ok) return raw<T>(path, options, false);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function tryRefresh(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: authStore.refresh }),
    });
    if (!res.ok) return false;
    const tokens = await res.json();
    authStore.set(tokens);
    return true;
  } catch {
    return false;
  }
}

export const api = {
  raw: <T = unknown>(path: string, options: RequestInit = {}) => raw<T>(path, options),
  // auth
  register: (data: { email: string; password: string; full_name: string; organization?: string }) =>
    raw("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (email: string, password: string) =>
    raw<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => raw<User>("/auth/me"),
  updateMe: (data: { full_name?: string; organization?: string }) =>
    raw<User>("/auth/me", { method: "PATCH", body: JSON.stringify(data) }),
  changePassword: (data: { old_password: string; new_password: string }) =>
    raw<{ message: string }>("/auth/me/change-password", { method: "POST", body: JSON.stringify(data) }),

  // projects
  projects: () => raw<Project[]>("/projects"),
  project: (id: string) => raw<Project>(`/projects/${id}`),
  createProject: (data: Partial<Project>) => raw<Project>("/projects", { method: "POST", body: JSON.stringify(data) }),
  projectSummary: (id: string) => raw<ProjectSummary>(`/projects/${id}/summary`),

  // datasets
  datasets: (projectId: string) => raw<Dataset[]>(`/datasets?project_id=${projectId}`),
  uploadDataset: (projectId: string, data: { name: string; omics_type: string; platform?: string }, file: File) => {
    const fd = new FormData();
    fd.append("project_id", projectId);
    fd.append("name", data.name);
    fd.append("omics_type", data.omics_type);
    fd.append("platform", data.platform || "");
    fd.append("file", file);
    return raw<Dataset>("/datasets", { method: "POST", body: fd });
  },

  // analyses
  analyses: (projectId: string) => raw<Analysis[]>(`/analyses?project_id=${projectId}`),
  analysis: (id: string) => raw<Analysis>(`/analyses/${id}`),
  createAnalysis: (projectId: string, data: { name: string; analysis_type: string; config: Record<string, unknown> }) =>
    raw<Analysis>(`/analyses/${projectId}/create`, { method: "POST", body: JSON.stringify(data) }),
  analysisResult: (id: string) => raw<unknown>(`/analyses/${id}/result`),
  artifacts: (id: string) => raw<Artifact[]>(`/analyses/${id}/artifacts`),
  artifactUrl: (analysisId: string, artifactId: string) => `${API_BASE}/analyses/${analysisId}/artifacts/${artifactId}/download`,

  // omics (sync)
  differentialExpression: (data: Record<string, unknown>) =>
    raw("/omics/differential-expression", { method: "POST", body: JSON.stringify(data) }),
  preprocessing: (data: Record<string, unknown>) => raw("/omics/preprocessing", { method: "POST", body: JSON.stringify(data) }),
  enrichment: (data: Record<string, unknown>) => raw("/omics/enrichment", { method: "POST", body: JSON.stringify(data) }),
  network: (data: Record<string, unknown>) => raw("/omics/network", { method: "POST", body: JSON.stringify(data) }),
  metaAnalysis: (data: Record<string, unknown>) => raw("/omics/meta-analysis", { method: "POST", body: JSON.stringify(data) }),
  deconvolution: (data: Record<string, unknown>) => raw("/omics/deconvolution", { method: "POST", body: JSON.stringify(data) }),
  integration: (data: Record<string, unknown>) => raw("/omics/integration", { method: "POST", body: JSON.stringify(data) }),

  // ml
  trainML: (data: Record<string, unknown>) => raw("/ml/train", { method: "POST", body: JSON.stringify(data) }),
  mlAlgorithms: () => raw<Record<string, unknown>>("/ml/algorithms"),
  trainedModels: () => raw<{ models: { key: string; algorithm: string; metrics: Record<string, number> }[] }>("/ml/trained"),

  // drugs
  drugPipeline: (data: Record<string, unknown>) => raw("/drugs/pipeline", { method: "POST", body: JSON.stringify(data) }),
  saveDrugPipeline: (projectId: string, data: Record<string, unknown>) =>
    raw(`/drugs/pipeline/${projectId}/save`, { method: "POST", body: JSON.stringify(data) }),
  drugCandidates: (projectId: string) => raw<DrugCandidate[]>(`/drugs/candidates?project_id=${projectId}`),
  drugTargetMap: (data: { gene_list: string[] }) => raw("/drugs/drug-target-map", { method: "POST", body: JSON.stringify(data) }),
  drugCombinations: (data: { gene_list: string[]; top_n: number }) =>
    raw("/drugs/combinations", { method: "POST", body: JSON.stringify(data) }),
  drugSearch: (q: string) => raw(`/drugs/search?query=${encodeURIComponent(q)}`),
  knowledgeBase: () => raw<{ n_drugs: number; drugs: { key: string; name: string; targets: string[]; fda_status: string }[] }>("/drugs/knowledge-base"),

  // reports
  generateReport: (data: { analysis_ids: string[]; formats: string[]; title?: string; dpi?: number }) =>
    raw("/reports/generate", { method: "POST", body: JSON.stringify(data) }),
  reportUrl: (analysisId: string, filename: string) => `${API_BASE}/reports/download/${analysisId}/${filename}`,

  // assistant
  assistantChat: (data: { message: string; project_id?: string; analysis_ids?: string[]; history?: { role: string; content: string }[] }) =>
    raw<{ reply: string; mode: string; context?: unknown; model?: string }>("/assistant/chat", { method: "POST", body: JSON.stringify(data) }),
  manuscript: (data: { analysis_ids: string[]; include_discussion?: boolean; include_methods?: boolean }) =>
    raw("/assistant/manuscript", { method: "POST", body: JSON.stringify(data) }),

  // admin
  adminUsers: () => raw<User[]>("/admin/users"),
  adminStats: () => raw<Record<string, unknown>>("/admin/stats"),
};

export function downloadUrl(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}


export type {
  User, Project, ProjectSummary, Dataset, Analysis, Artifact, DrugCandidate, MLResult, EnrichmentRow, Sankey, TokenResponse,
} from "./types";
