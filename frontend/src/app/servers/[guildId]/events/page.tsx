"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { EventSheet } from "@/components/app/event-sheet";
import { EventStream } from "@/components/app/event-stream";
import { useGuild } from "@/components/app/guild-shell";
import { Empty, ErrorState, LoadingRows, PageTitle, Panel } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { EVENT_TITLE, SEVERITY } from "@/lib/format";
import type { SecurityEvent, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

const LEVELS: Severity[] = ["critical", "high", "medium", "low"];

export default function EventsPage() {
  const { guild } = useGuild();
  const [levels, setLevels] = useState<Severity[]>([]);
  const [type, setType] = useState("all");
  const [older, setOlder] = useState<SecurityEvent[]>([]);
  const [cursor, setCursor] = useState<number | null | undefined>(undefined);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selected, setSelected] = useState<SecurityEvent | null>(null);

  const filters = { severity: levels, type: type === "all" ? undefined : type, limit: 50 };
  const key = `${guild.id}-${levels.join(",")}-${type}`;
  const page = useApi(() => api.events(guild.id, filters), key);
  const [pageKey, setPageKey] = useState(key);
  if (pageKey !== key) {
    // Filters changed: start the pagination over (render-time reset, no effect needed).
    setPageKey(key);
    setOlder([]);
    setCursor(undefined);
  }
  const nextCursor = cursor === undefined ? page.data?.next_before_id ?? null : cursor;
  const events = [...(page.data?.items ?? []), ...older];

  async function loadMore() {
    if (!nextCursor) return;
    setLoadingMore(true);
    try {
      const more = await api.events(guild.id, { ...filters, before_id: nextCursor });
      setOlder((current) => [...current, ...more.items]);
      setCursor(more.next_before_id);
    } finally {
      setLoadingMore(false);
    }
  }

  const toggle = (level: Severity) => setLevels((current) => (current.includes(level) ? current.filter((l) => l !== level) : [...current, level]));

  return (
    <>
      <PageTitle title="Events" description="Every detection, what the rule engine decided, and what was done." />
      <Panel
        title={`${events.length}${nextCursor ? "+" : ""} events`}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-1" role="group" aria-label="Severity filter">
              {LEVELS.map((level) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => toggle(level)}
                  aria-pressed={levels.includes(level)}
                  className={cn("rounded border px-2 py-1 font-mono text-[10.5px] uppercase transition-colors", levels.includes(level) ? "" : "border-border text-muted-foreground hover:text-foreground")}
                  style={levels.includes(level) ? { color: SEVERITY[level].color, borderColor: SEVERITY[level].color, background: `color-mix(in oklch, ${SEVERITY[level].color} 12%, transparent)` } : undefined}
                >
                  {SEVERITY[level].label}
                </button>
              ))}
            </div>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger size="sm" className="w-[190px]" aria-label="Event type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All event types</SelectItem>
                {Object.entries(EVENT_TITLE).map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        }
      >
        {page.loading ? (
          <LoadingRows rows={8} />
        ) : page.error ? (
          <div className="p-4"><ErrorState message={page.error} onRetry={page.reload} /></div>
        ) : events.length ? (
          <>
            <EventStream events={events} onSelect={setSelected} />
            {nextCursor ? (
              <div className="p-3 text-center">
                <Button variant="outline" size="sm" onClick={loadMore} disabled={loadingMore}>
                  {loadingMore ? <Loader2 className="animate-spin" /> : null}Load older events
                </Button>
              </div>
            ) : null}
          </>
        ) : (
          <Empty title="No events match" description={levels.length || type !== "all" ? "Try clearing the filters." : "Nothing has been detected yet."} />
        )}
      </Panel>
      <EventSheet event={selected} onClose={() => setSelected(null)} />
    </>
  );
}
