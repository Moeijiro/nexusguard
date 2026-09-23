"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, CircleCheck, CircleDashed, Radio } from "lucide-react";
import { ActivityChart } from "@/components/app/activity-chart";
import { EventSheet } from "@/components/app/event-sheet";
import { EventStream } from "@/components/app/event-stream";
import { useGuild } from "@/components/app/guild-shell";
import { Empty, ErrorState, PageLoading, PageTitle, Panel, Stat } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { SEVERITY } from "@/lib/format";
import type { SecurityEvent, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

const POLL_MS = 4000;

/** Polls for events newer than the newest one on screen and prepends them. */
function useLiveEvents(guildId: string, initial: SecurityEvent[] | undefined) {
  const [events, setEvents] = useState<SecurityEvent[] | null>(null);
  const [fresh, setFresh] = useState<Set<number>>(new Set());
  const [live, setLive] = useState(true);
  const newest = useRef(0);

  const list = events ?? initial ?? [];
  const newestId = list[0]?.id;
  useEffect(() => {
    if (newestId !== undefined) newest.current = newestId;
  }, [newestId]);

  useEffect(() => {
    if (!live) return;
    const timer = setInterval(async () => {
      try {
        const page = await api.events(guildId, { after_id: newest.current, limit: 20 });
        if (page.items.length) {
          setEvents((current) => [...page.items, ...(current ?? initial ?? [])].slice(0, 40));
          setFresh(new Set(page.items.map((e) => e.id)));
        }
      } catch {
        /* keep the last good stream; the next poll retries */
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [guildId, live, initial]);

  return { events: list, fresh, live, setLive };
}

export default function OverviewPage() {
  const { guild } = useGuild();
  const overview = useApi(() => api.overview(guild.id), `overview-${guild.id}-${guild.raid.enabled}`);
  const stream = useLiveEvents(guild.id, overview.data?.recent_events);
  const [selected, setSelected] = useState<SecurityEvent | null>(null);

  if (overview.loading) return <PageLoading />;
  if (overview.error || !overview.data) return <ErrorState message={overview.error ?? "Couldn't load the overview."} onRetry={overview.reload} />;
  const { protection, stats, severity_today, activity } = overview.data;
  const base = `/servers/${guild.id}`;

  return (
    <>
      <PageTitle title={guild.name} description="Security status for the last 24 hours" />

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,2fr)]">
        <Panel title="Security status" bodyClassName="p-4">
          <p className="font-mono text-3xl font-semibold tabular">
            <span className={protection.enabled === protection.total ? "text-signal" : ""}>{protection.enabled}</span>
            <span className="text-muted-foreground"> / {protection.total}</span>
          </p>
          <p className="mt-1 text-sm text-muted-foreground">protection modules enabled</p>
          <ul className="mt-4 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
            {protection.modules.map((m) => (
              <li key={m.module} className={cn("flex items-center gap-2 text-[13px]", !m.enabled && "text-muted-foreground")}>
                {m.enabled ? <CircleCheck className="size-3.5 text-signal" /> : <CircleDashed className="size-3.5" />}
                {m.name}
              </li>
            ))}
          </ul>
          <Button asChild variant="link" className="mt-3 h-auto px-0 text-signal">
            <Link href={`${base}/rules`}>Configure rules<ArrowRight data-icon="inline-end" /></Link>
          </Button>
        </Panel>

        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          <Stat label="Events · 24 h" value={stats.events_today} hint={`${severity_today.critical + severity_today.high} high or critical`} />
          <Stat label="Users flagged" value={stats.users_flagged} hint={`${stats.open_flags} awaiting review`} tone={stats.open_flags ? "var(--sev-medium)" : undefined} />
          <Stat label="Active rules" value={stats.active_rules} hint={`of ${protection.total}`} />
          <Stat label="Actions · 24 h" value={stats.actions_today} hint="warnings, timeouts, roles, kicks" />
          <div className="col-span-2 rounded-lg border bg-card px-4 py-3.5 xl:col-span-4">
            <p className="font-mono text-[10.5px] tracking-[0.12em] text-muted-foreground uppercase">Severity · 24 h</p>
            <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-muted" role="img" aria-label="Events by severity">
              {(["critical", "high", "medium", "low"] as Severity[]).map((s) =>
                severity_today[s] ? <span key={s} style={{ flexGrow: severity_today[s], background: SEVERITY[s].color }} /> : null,
              )}
            </div>
            <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11.5px]">
              {(["critical", "high", "medium", "low"] as Severity[]).map((s) => (
                <span key={s} className="flex items-center gap-1.5 text-muted-foreground">
                  <span className="size-2 rounded-full" style={{ background: SEVERITY[s].color }} />
                  {SEVERITY[s].label} <span className="text-foreground tabular">{severity_today[s]}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
        <Panel
          title="Event stream"
          description="Newest first · updates every few seconds"
          action={
            <button
              type="button"
              onClick={() => stream.setLive(!stream.live)}
              className={cn("flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10.5px] uppercase", stream.live ? "border-signal/40 text-signal" : "text-muted-foreground")}
              aria-pressed={stream.live}
            >
              <Radio className={cn("size-3", stream.live && "animate-pulse")} />
              {stream.live ? "Live" : "Paused"}
            </button>
          }
          bodyClassName="max-h-[560px] overflow-y-auto"
        >
          {stream.events.length ? (
            <EventStream events={stream.events} freshIds={stream.fresh} onSelect={setSelected} />
          ) : (
            <Empty title="No events yet" description="When a rule fires, it shows up here with what NexusGuard did about it." />
          )}
          <div className="border-t p-3 text-center">
            <Button asChild variant="ghost" size="sm"><Link href={`${base}/events`}>Open the full event log<ArrowRight data-icon="inline-end" /></Link></Button>
          </div>
        </Panel>
        <Panel title="Server activity" description="Messages and joins per hour, with security events" bodyClassName="p-4">
          <ActivityChart points={activity} />
        </Panel>
      </div>

      <EventSheet event={selected} onClose={() => setSelected(null)} />
    </>
  );
}
