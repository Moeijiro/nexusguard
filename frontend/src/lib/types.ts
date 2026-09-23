/** Mirrors the FastAPI response models. */

export type Severity = "low" | "medium" | "high" | "critical";

export interface User {
  id: number;
  discord_id: string;
  username: string;
  global_name: string | null;
  avatar_url: string | null;
  is_demo: boolean;
}

export interface Mode {
  discord_login: boolean;
  demo: boolean;
  bot_invite_url: string | null;
}

export interface GuildSummary {
  id: string;
  name: string;
  icon_url: string | null;
  member_count: number;
  is_demo: boolean;
  bot_present: boolean;
  raid_mode: boolean;
  modules_enabled: number;
  modules_total: number;
  events_today: number;
}

export interface RaidMode {
  enabled: boolean;
  since: string | null;
  until: string | null;
  reason: string | null;
  by: string | null;
}

export interface GuildDetail extends GuildSummary {
  alert_channel_id: string | null;
  restricted_role_id: string | null;
  raid: RaidMode;
  bot_invite_url: string | null;
}

export interface ActionResult {
  action: string;
  status: "done" | "simulated" | "skipped" | "suppressed" | "failed";
  detail: string;
}

export interface SecurityEvent {
  id: number;
  type: string;
  module: string;
  severity: Severity;
  summary: string;
  user_id: string | null;
  username: string | null;
  channel_id: string | null;
  channel_name: string | null;
  action_taken: string;
  actions: ActionResult[];
  notes: string[];
  metadata: Record<string, unknown>;
  simulated: boolean;
  created_at: string;
}

export interface EventPage {
  items: SecurityEvent[];
  next_before_id: number | null;
}

export interface ActivityPoint {
  hour: string;
  messages: number;
  joins: number;
  events: number;
}

export interface ModuleStatus {
  module: string;
  name: string;
  enabled: boolean;
}

export interface Overview {
  guild: GuildDetail;
  protection: { enabled: number; total: number; modules: ModuleStatus[] };
  stats: { events_today: number; users_flagged: number; active_rules: number; actions_today: number; open_flags: number };
  severity_today: Record<Severity, number>;
  activity: ActivityPoint[];
  recent_events: SecurityEvent[];
}

export interface Rule {
  module: string;
  name: string;
  description: string;
  enabled: boolean;
  params: Record<string, unknown> & { actions: string[] };
  allowed_actions: string[];
  updated_at: string | null;
  updated_by: string | null;
}

export interface Resource {
  id: string;
  name: string;
  kind: "text" | "announcement" | "role";
  position: number;
  assignable: boolean;
  color: number | null;
}

export interface ModerationEntry {
  id: number;
  action: string;
  target_id: string;
  target_name: string | null;
  moderator_name: string;
  source: "automatic" | "dashboard" | "command";
  reason: string | null;
  status: string;
  event_id: number | null;
  created_at: string;
}

export interface Flag {
  id: number;
  user_id: string;
  username: string | null;
  reason: string;
  severity: Severity;
  status: "open" | "dismissed" | "actioned";
  event_id: number | null;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface AuditEntry {
  id: number;
  actor_name: string;
  action: string;
  target: string | null;
  changes: Record<string, unknown>;
  created_at: string;
}
