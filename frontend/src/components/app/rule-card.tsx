"use client";

import { useState } from "react";
import { Loader2, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import { ACTION_LABEL, timeAgo } from "@/lib/format";
import type { Rule } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Labels and bounds for each numeric setting — the API enforces the same bounds. */
const NUMBERS: Record<string, { label: string; unit: string; min: number; max: number }> = {
  max_messages: { label: "Messages", unit: "msgs", min: 2, max: 50 },
  max_repeats: { label: "Identical messages", unit: "times", min: 2, max: 20 },
  window_seconds: { label: "Within", unit: "sec", min: 2, max: 600 },
  max_mentions: { label: "Mentions per message", unit: "pings", min: 2, max: 50 },
  join_threshold: { label: "Joins", unit: "joins", min: 3, max: 500 },
  timeout_minutes: { label: "Timeout length", unit: "min", min: 1, max: 1440 },
  raid_mode_minutes: { label: "Raid mode lasts", unit: "min", min: 5, max: 1440 },
  min_account_age_hours: { label: "Accounts younger than", unit: "hours", min: 1, max: 2160 },
};

const SWITCHES: Record<string, { label: string; hint: string }> = {
  block_everyone: { label: "Block @everyone / @here", hint: "From members without moderator permissions" },
  auto_raid_mode: { label: "Enable raid mode automatically", hint: "When a join spike is detected" },
  restrict_new_members: { label: "Restrict new members in raid mode", hint: "Assigns the restricted role on join" },
};

type Draft = Record<string, unknown> & { enabled: boolean; actions: string[] };

function toDraft(rule: Rule): Draft {
  return { ...rule.params, enabled: rule.enabled, actions: [...rule.params.actions] };
}

export function RuleCard({ guildId, rule, onSaved, hasRestrictedRole, hasAlertChannel }: {
  guildId: string;
  rule: Rule;
  onSaved: (rule: Rule) => void;
  hasRestrictedRole: boolean;
  hasAlertChannel: boolean;
}) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(rule));
  const [saved, setSaved] = useState<Draft>(() => toDraft(rule));
  const [busy, setBusy] = useState(false);
  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const set = (patch: Partial<Draft>) => setDraft((current) => ({ ...current, ...patch }));

  async function save(next: Draft = draft) {
    setBusy(true);
    try {
      const updated = await api.saveRule(guildId, rule.module, next);
      const fresh = toDraft(updated);
      setDraft(fresh);
      setSaved(fresh);
      onSaved(updated);
      toast.success(`${rule.name} saved`, { description: "The bot picks up changes within a few seconds." });
    } catch (err) {
      toast.error(`Couldn't save ${rule.name}`, { description: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  const numbers = Object.keys(NUMBERS).filter((key) => key in rule.params);
  const switches = Object.keys(SWITCHES).filter((key) => key in rule.params);
  const warnings: string[] = [];
  if (draft.enabled && draft.actions.includes("restrict") && !hasRestrictedRole) warnings.push("No restricted role set — “Restricted role” will be skipped.");
  if (draft.enabled && draft.actions.includes("notify") && !hasAlertChannel) warnings.push("No alert channel set — alerts will be skipped.");
  if (draft.enabled && draft.restrict_new_members === true && !hasRestrictedRole) warnings.push("Raid-mode restrictions need a restricted role in Settings.");
  if (draft.actions.includes("kick")) warnings.push("Kick removes members automatically. Consider timeout first.");

  return (
    <article className={cn("flex flex-col rounded-lg border bg-card transition-colors", draft.enabled ? "border-signal/25" : "opacity-80")}>
      <header className="flex items-start gap-3 border-b px-4 py-3.5">
        <div className="min-w-0 flex-1">
          <h2 className="font-medium">{rule.name}</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">{rule.description}</p>
        </div>
        <Switch
          checked={draft.enabled}
          onCheckedChange={(enabled) => {
            const next = { ...draft, enabled };
            setDraft(next);
            save(next);
          }}
          aria-label={`${rule.name} enabled`}
          disabled={busy}
        />
      </header>

      <div className={cn("flex-1 space-y-4 px-4 py-4", !draft.enabled && "pointer-events-none opacity-50")} aria-disabled={!draft.enabled}>
        {numbers.length ? (
          <div className="grid grid-cols-2 gap-3">
            {numbers.map((key) => {
              const meta = NUMBERS[key];
              return (
                <label key={key} className="block space-y-1.5">
                  <span className="text-xs text-muted-foreground">{meta.label}</span>
                  <span className="flex items-center rounded-md border bg-background/60 focus-within:border-ring">
                    <Input
                      type="number"
                      min={meta.min}
                      max={meta.max}
                      value={String(draft[key] ?? "")}
                      onChange={(e) => set({ [key]: e.target.value === "" ? "" : Number(e.target.value) })}
                      className="h-8 border-0 bg-transparent font-mono tabular shadow-none focus-visible:ring-0 dark:bg-transparent"
                    />
                    <span className="pr-2.5 font-mono text-[10.5px] text-muted-foreground">{meta.unit}</span>
                  </span>
                </label>
              );
            })}
          </div>
        ) : null}

        {switches.map((key) => (
          <div key={key} className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm">{SWITCHES[key].label}</p>
              <p className="text-xs text-muted-foreground">{SWITCHES[key].hint}</p>
            </div>
            <Switch checked={Boolean(draft[key])} onCheckedChange={(value) => set({ [key]: value })} aria-label={SWITCHES[key].label} />
          </div>
        ))}

        <div>
          <p className="mb-2 text-xs text-muted-foreground">Actions <span className="text-muted-foreground/70">· event is always logged</span></p>
          <div className="flex flex-wrap gap-1.5">
            {rule.allowed_actions.map((action) => {
              const on = draft.actions.includes(action);
              return (
                <button
                  key={action}
                  type="button"
                  aria-pressed={on}
                  onClick={() => set({ actions: on ? draft.actions.filter((a) => a !== action) : [...draft.actions, action] })}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-xs transition-colors",
                    on ? (action === "kick" ? "border-sev-high/60 bg-sev-high/10 text-sev-high" : "border-signal/50 bg-signal/10 text-signal") : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {ACTION_LABEL[action] ?? action}
                </button>
              );
            })}
          </div>
        </div>

        {warnings.length ? (
          <ul className="space-y-1 text-xs text-sev-medium">{warnings.map((w) => <li key={w}>• {w}</li>)}</ul>
        ) : null}
      </div>

      <footer className="flex items-center gap-2 border-t px-4 py-2.5">
        <span className="min-w-0 flex-1 truncate font-mono text-[10.5px] text-muted-foreground">
          {rule.updated_by ? `Edited by ${rule.updated_by} · ${timeAgo(rule.updated_at)}` : "Default settings"}
        </span>
        {dirty ? (
          <>
            <Button variant="ghost" size="sm" onClick={() => setDraft(saved)} aria-label="Discard changes"><RotateCcw /></Button>
            <Button size="sm" onClick={() => save()} disabled={busy}>{busy ? <Loader2 className="animate-spin" /> : null}Save</Button>
          </>
        ) : null}
      </footer>
    </article>
  );
}
