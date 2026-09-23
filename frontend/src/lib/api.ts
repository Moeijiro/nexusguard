/** The dashboard's only way to the API. The session is an HttpOnly cookie. */

import type {
  AuditEntry,
  EventPage,
  Flag,
  GuildDetail,
  GuildSummary,
  Mode,
  ModerationEntry,
  Overview,
  Resource,
  Rule,
  SecurityEvent,
  Severity,
  User,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      credentials: "include",
      cache: "no-store",
      headers: init.body ? { "Content-Type": "application/json" } : undefined,
      ...init,
    });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the NexusGuard API.");
  }
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(response.status, error?.code ?? "error", error?.message ?? response.statusText);
  }
  return payload as T;
}

const json = (body: unknown) => JSON.stringify(body);
const g = (id: string) => `/api/guilds/${id}`;

export const api = {
  mode: () => request<Mode>("/api/auth/mode"),
  me: () => request<User>("/api/me"),
  demoLogin: () => request<User>("/api/auth/demo", { method: "POST" }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  loginUrl: `${API_BASE}/api/auth/login`,

  guilds: () => request<GuildSummary[]>("/api/guilds"),
  guild: (id: string) => request<GuildDetail>(g(id)),
  overview: (id: string) => request<Overview>(`${g(id)}/overview`),
  resources: (id: string) => request<{ channels: Resource[]; roles: Resource[] }>(`${g(id)}/resources`),
  saveSettings: (id: string, body: { alert_channel_id?: string | null; restricted_role_id?: string | null }) =>
    request<GuildDetail>(`${g(id)}/settings`, { method: "PATCH", body: json(body) }),
  raidMode: (id: string, enabled: boolean, minutes?: number) =>
    request<GuildDetail>(`${g(id)}/raid-mode`, { method: "POST", body: json({ enabled, minutes }) }),

  rules: (id: string) => request<Rule[]>(`${g(id)}/rules`),
  saveRule: (id: string, module: string, body: Record<string, unknown>) =>
    request<Rule>(`${g(id)}/rules/${module}`, { method: "PUT", body: json(body) }),

  events: (id: string, params: { severity?: Severity[]; type?: string; after_id?: number; before_id?: number; limit?: number } = {}) => {
    const search = new URLSearchParams();
    params.severity?.forEach((s) => search.append("severity", s));
    if (params.type) search.set("type", params.type);
    if (params.after_id !== undefined) search.set("after_id", String(params.after_id));
    if (params.before_id !== undefined) search.set("before_id", String(params.before_id));
    if (params.limit) search.set("limit", String(params.limit));
    const q = search.toString();
    return request<EventPage>(`${g(id)}/events${q ? `?${q}` : ""}`);
  },
  event: (id: string, eventId: number) => request<SecurityEvent>(`${g(id)}/events/${eventId}`),
  moderation: (id: string) => request<ModerationEntry[]>(`${g(id)}/moderation`),
  flags: (id: string, status: "open" | "all" = "open") => request<Flag[]>(`${g(id)}/flags?status=${status}`),
  resolveFlag: (id: string, flagId: number, action: "dismiss" | "timeout" | "restrict" | "kick", minutes?: number) =>
    request<Flag>(`${g(id)}/flags/${flagId}/resolve`, { method: "POST", body: json({ action, minutes }) }),
  audit: (id: string) => request<AuditEntry[]>(`${g(id)}/audit`),
};
