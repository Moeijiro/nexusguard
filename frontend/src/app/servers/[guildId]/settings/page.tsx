"use client";

import { useState } from "react";
import { Check, ExternalLink, Hash, Loader2, Shield, X } from "lucide-react";
import { toast } from "sonner";
import { useGuild } from "@/components/app/guild-shell";
import { Mono, PageTitle, Panel } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";

const NONE = "__none__";

const PERMISSIONS = [
  ["View Channels", "See the channels it protects"],
  ["Send Messages · Embed Links", "Moderator alerts and warnings"],
  ["Manage Messages", "Delete spam and mass-mention messages"],
  ["Moderate Members", "Timeouts"],
  ["Manage Roles", "Assign the restricted role (NexusGuard's role must be above it)"],
  ["Kick Members", "Only used if you set a rule to kick"],
  ["View Audit Log", "Attribute manual kicks, bans and timeouts"],
];

const INTENTS = [
  ["Server Members", true, "Member joins and role changes — raid, account-age and role detection"],
  ["Message Content", true, "The text the spam and mention detectors read"],
  ["Guilds · Guild Messages · Moderation", false, "Channels, roles, message events and audit-log events"],
] as const;

export default function SettingsPage() {
  const { guild, setGuild } = useGuild();
  const resources = useApi(() => api.resources(guild.id), `resources-${guild.id}`);
  const [channel, setChannel] = useState(guild.alert_channel_id ?? NONE);
  const [role, setRole] = useState(guild.restricted_role_id ?? NONE);
  const [busy, setBusy] = useState(false);
  const dirty = channel !== (guild.alert_channel_id ?? NONE) || role !== (guild.restricted_role_id ?? NONE);

  async function save() {
    setBusy(true);
    try {
      const next = await api.saveSettings(guild.id, {
        alert_channel_id: channel === NONE ? null : channel,
        restricted_role_id: role === NONE ? null : role,
      });
      setGuild(next);
      toast.success("Settings saved");
    } catch (err) {
      toast.error("Couldn't save settings", { description: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageTitle title="Settings" description="Where alerts go, which role restricts members, and what the bot needs." />
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Panel title="Alerts and restrictions" bodyClassName="space-y-5 p-4">
          <div className="space-y-2">
            <Label htmlFor="alert-channel">Moderator alert channel</Label>
            <Select value={channel} onValueChange={setChannel} disabled={resources.loading}>
              <SelectTrigger id="alert-channel" className="w-full"><SelectValue placeholder="Choose a channel" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>No alerts</SelectItem>
                {resources.data?.channels.map((c) => (
                  <SelectItem key={c.id} value={c.id}><Hash className="size-3.5" />{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">Raid alerts, critical events and anything a rule sends to moderators. Alerts never ping anyone.</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="restricted-role">Restricted role</Label>
            <Select value={role} onValueChange={setRole} disabled={resources.loading}>
              <SelectTrigger id="restricted-role" className="w-full"><SelectValue placeholder="Choose a role" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>None</SelectItem>
                {resources.data?.roles.map((r) => (
                  <SelectItem key={r.id} value={r.id} disabled={!r.assignable}>
                    <span className="size-2.5 rounded-full" style={{ background: r.color ? `#${r.color.toString(16).padStart(6, "0")}` : "var(--muted-foreground)" }} />
                    {r.name}{!r.assignable ? " (above NexusGuard)" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">Given to new members during raid mode and by rules set to restrict. Set its channel permissions to read-only in Discord.</p>
          </div>
          <div className="flex justify-end">
            <Button onClick={save} disabled={!dirty || busy}>{busy ? <Loader2 className="animate-spin" /> : null}Save settings</Button>
          </div>
        </Panel>

        <Panel title="Bot permissions" description="What NexusGuard asks for when it's invited, and why." bodyClassName="p-4">
          <ul className="space-y-2.5">
            {PERMISSIONS.map(([name, why]) => (
              <li key={name} className="flex gap-2.5 text-sm">
                <Check className="mt-0.5 size-4 shrink-0 text-signal" />
                <span><span className="font-medium">{name}</span><span className="text-muted-foreground"> — {why}</span></span>
              </li>
            ))}
            <li className="flex gap-2.5 text-sm">
              <X className="mt-0.5 size-4 shrink-0 text-destructive" />
              <span><span className="font-medium">Ban Members, Administrator</span><span className="text-muted-foreground"> — never requested</span></span>
            </li>
          </ul>
          {guild.bot_invite_url ? (
            <Button asChild variant="outline" size="sm" className="mt-4">
              <a href={guild.bot_invite_url} target="_blank" rel="noreferrer">Re-invite with these permissions<ExternalLink data-icon="inline-end" /></a>
            </Button>
          ) : null}
        </Panel>

        <Panel title="Gateway intents" description="Enable the two privileged intents in the Discord developer portal (Bot → Privileged Gateway Intents)." bodyClassName="divide-y">
          {INTENTS.map(([name, privileged, why]) => (
            <div key={name} className="flex items-start gap-3 px-4 py-3">
              <Shield className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="text-sm">
                <p className="font-medium">{name} {privileged ? <Mono className="ml-1 text-sev-medium">privileged</Mono> : null}</p>
                <p className="text-muted-foreground">{why}</p>
              </div>
            </div>
          ))}
        </Panel>

        <Panel title="Data kept" bodyClassName="space-y-2 p-4 text-sm text-muted-foreground">
          <p>Security events store the member ID and name, the channel, what was detected and what was done — plus up to 120 characters of the offending message.</p>
          <p>Ordinary messages are never stored: server activity is hourly counts only.</p>
          <p>Dashboard logins keep your Discord ID and name, and the list of servers you can manage. Your Discord token is not stored.</p>
        </Panel>
      </div>
    </>
  );
}
