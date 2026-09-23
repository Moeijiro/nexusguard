import type { Severity } from "./types";

const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/** 22:41 — the event stream's clock. Local time, 24-hour. */
export function clock(iso: string, seconds = false): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", ...(seconds ? { second: "2-digit" } : {}) });
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 45) return "just now";
  if (s < 3600) return relative.format(-Math.round(s / 60), "minute");
  if (s < 86_400) return relative.format(-Math.round(s / 3600), "hour");
  if (s < 7 * 86_400) return relative.format(-Math.round(s / 86_400), "day");
  return new Date(iso).toLocaleDateString("en", { month: "short", day: "numeric" });
}

export function dayLabel(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date(Date.now() - 86_400_000);
  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return date.toLocaleDateString("en", { weekday: "long", month: "short", day: "numeric" });
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "medium" });
}

export function compact(n: number): string {
  return new Intl.NumberFormat("en", { notation: n >= 10_000 ? "compact" : "standard" }).format(n);
}

export const SEVERITY: Record<Severity, { label: string; color: string; rank: number }> = {
  low: { label: "Low", color: "var(--sev-low)", rank: 0 },
  medium: { label: "Medium", color: "var(--sev-medium)", rank: 1 },
  high: { label: "High", color: "var(--sev-high)", rank: 2 },
  critical: { label: "Critical", color: "var(--sev-critical)", rank: 3 },
};

export const EVENT_TITLE: Record<string, string> = {
  spam_detected: "Spam detected",
  raid_detected: "Join spike detected",
  mass_mentions: "Mass mention blocked",
  suspicious_join: "Suspicious join",
  role_change: "Privileged role granted",
  moderation_action: "Moderation action",
};

export const ACTION_LABEL: Record<string, string> = {
  warn: "Warn",
  delete_message: "Delete message",
  timeout: "Timeout",
  restrict: "Restricted role",
  kick: "Kick",
  notify: "Alert moderators",
  flag: "Flag for review",
};

export function title(type: string, summary?: string): string {
  if (type === "moderation_action" && summary?.startsWith("Raid mode")) return summary.split(" by ")[0];
  return EVENT_TITLE[type] ?? type;
}
