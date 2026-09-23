"use client";

import { useState } from "react";
import { Check, ChevronDown, Clock, Gavel, History, Inbox, ShieldMinus, UserX } from "lucide-react";
import { toast } from "sonner";
import { useGuild } from "@/components/app/guild-shell";
import { SeverityBadge } from "@/components/app/severity";
import { Empty, ErrorState, LoadingRows, Mono, PageTitle, Panel } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { dateTime, timeAgo } from "@/lib/format";
import type { Flag } from "@/lib/types";
import { cn } from "@/lib/utils";

const SOURCE = { automatic: "Automatic", dashboard: "Dashboard", command: "Slash command" } as const;
const STATUS_TONE: Record<string, string> = { done: "text-signal", simulated: "text-chart-2", failed: "text-destructive" };

function ReviewQueue() {
  const { guild } = useGuild();
  const flags = useApi(() => api.flags(guild.id), `flags-${guild.id}`);
  const [busy, setBusy] = useState<number | null>(null);

  async function resolve(flag: Flag, action: "dismiss" | "timeout" | "restrict" | "kick", minutes?: number) {
    if (action === "kick" && !window.confirm(`Kick ${flag.username ?? flag.user_id}?`)) return;
    setBusy(flag.id);
    try {
      await api.resolveFlag(guild.id, flag.id, action, minutes);
      flags.mutate((current) => current.filter((f) => f.id !== flag.id));
      toast.success(action === "dismiss" ? "Flag dismissed" : `Action applied to ${flag.username ?? "member"}`, {
        description: guild.is_demo ? "Simulated — demo servers never reach Discord." : undefined,
      });
    } catch (err) {
      toast.error("Couldn't resolve the flag", { description: (err as Error).message });
    } finally {
      setBusy(null);
    }
  }

  return (
    <Panel title={`Review queue · ${flags.data?.length ?? 0} open`} description="Members a rule flagged for a human decision — usually new accounts or privileged role grants.">
      {flags.loading ? <LoadingRows /> : flags.error ? <div className="p-4"><ErrorState message={flags.error} onRetry={flags.reload} /></div> : flags.data?.length ? (
        <ul className="divide-y">
          {flags.data.map((flag) => (
            <li key={flag.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2 text-sm font-medium">{flag.username ?? "Unknown member"} <SeverityBadge severity={flag.severity} /></p>
                <p className="mt-0.5 text-[13px] text-muted-foreground">{flag.reason}</p>
                <Mono className="text-muted-foreground">{flag.user_id} · {timeAgo(flag.created_at)}</Mono>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={() => resolve(flag, "dismiss")} disabled={busy === flag.id}><Check />Looks fine</Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" disabled={busy === flag.id}>Take action<ChevronDown data-icon="inline-end" /></Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onSelect={() => resolve(flag, "timeout", 60)}><Clock />Timeout for 1 hour</DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => resolve(flag, "timeout", 1440)}><Clock />Timeout for 24 hours</DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => resolve(flag, "restrict")} disabled={!guild.restricted_role_id}><ShieldMinus />Assign restricted role</DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem variant="destructive" onSelect={() => resolve(flag, "kick")}><UserX />Kick</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </li>
          ))}
        </ul>
      ) : <Empty icon={Inbox} title="Nothing to review" description="Flags from the account-age and privileged-role modules land here." />}
    </Panel>
  );
}

function ModerationLog() {
  const { guild } = useGuild();
  const log = useApi(() => api.moderation(guild.id), `moderation-${guild.id}`);
  return (
    <Panel title="Moderation log" description="Every warning, timeout, role restriction and kick performed through NexusGuard.">
      {log.loading ? <LoadingRows /> : log.error ? <div className="p-4"><ErrorState message={log.error} /></div> : log.data?.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b text-left font-mono text-[10.5px] tracking-[0.1em] text-muted-foreground uppercase">
                <th scope="col" className="px-4 py-2.5 font-medium">Time</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Action</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Member</th>
                <th scope="col" className="px-3 py-2.5 font-medium">By</th>
                <th scope="col" className="px-3 py-2.5 font-medium">Reason</th>
                <th scope="col" className="px-4 py-2.5 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {log.data.map((entry) => (
                <tr key={entry.id} className="hover:bg-accent/40">
                  <td className="px-4 py-2.5 whitespace-nowrap"><Mono className="text-muted-foreground" >{dateTime(entry.created_at)}</Mono></td>
                  <td className="px-3 py-2.5 font-medium capitalize">{entry.action}</td>
                  <td className="px-3 py-2.5">{entry.target_name ?? entry.target_id}</td>
                  <td className="px-3 py-2.5 text-muted-foreground">
                    {entry.moderator_name}
                    <span className="ml-1.5 font-mono text-[10.5px] uppercase">{SOURCE[entry.source]}</span>
                  </td>
                  <td className="max-w-[320px] truncate px-3 py-2.5 text-muted-foreground" title={entry.reason ?? ""}>{entry.reason ?? "—"}</td>
                  <td className={cn("px-4 py-2.5 text-right font-mono text-[11px] uppercase", STATUS_TONE[entry.status] ?? "text-muted-foreground")}>{entry.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Empty icon={Gavel} title="No moderation yet" />}
    </Panel>
  );
}

function AuditTrail() {
  const { guild } = useGuild();
  const audit = useApi(() => api.audit(guild.id), `audit-${guild.id}`);
  return (
    <Panel title="Configuration audit" description="Who changed rules, settings and raid mode.">
      {audit.loading ? <LoadingRows /> : audit.data?.length ? (
        <ul className="divide-y">
          {audit.data.map((entry) => (
            <li key={entry.id} className="grid grid-cols-1 gap-1 px-4 py-3 sm:grid-cols-[180px_minmax(0,1fr)] sm:gap-4">
              <Mono className="text-muted-foreground">{dateTime(entry.created_at)}</Mono>
              <div className="min-w-0 text-sm">
                <p><span className="font-medium">{entry.actor_name}</span> <Mono className="text-signal">{entry.action}</Mono>{entry.target ? <span className="text-muted-foreground"> · {entry.target}</span> : null}</p>
                {Object.keys(entry.changes).length ? (
                  <pre className="mt-1.5 overflow-x-auto rounded border bg-background/60 px-2.5 py-1.5 font-mono text-[11px] text-muted-foreground">{JSON.stringify(entry.changes)}</pre>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : <Empty icon={History} title="No configuration changes yet" />}
    </Panel>
  );
}

export default function ModerationPage() {
  return (
    <>
      <PageTitle title="Moderation" description="Review flagged members, and see every action NexusGuard took or was asked to take." />
      <Tabs defaultValue="review">
        <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <TabsList>
            <TabsTrigger value="review"><Inbox />Review queue</TabsTrigger>
            <TabsTrigger value="log"><Gavel />Moderation log</TabsTrigger>
            <TabsTrigger value="audit"><History />Config audit</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="review" className="mt-4"><ReviewQueue /></TabsContent>
        <TabsContent value="log" className="mt-4"><ModerationLog /></TabsContent>
        <TabsContent value="audit" className="mt-4"><AuditTrail /></TabsContent>
      </Tabs>
    </>
  );
}

