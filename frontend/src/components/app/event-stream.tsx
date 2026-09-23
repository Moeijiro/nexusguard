"use client";

import { ChevronRight } from "lucide-react";
import { SeverityBadge, SeverityRail } from "@/components/app/severity";
import { clock, dayLabel, title } from "@/lib/format";
import type { SecurityEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * The chronological stream:
 *   22:41  Mass mention blocked      HIGH
 *          User: example · Action: Message deleted
 */
export function EventStream({
  events,
  onSelect,
  freshIds,
  dense = false,
}: {
  events: SecurityEvent[];
  onSelect: (event: SecurityEvent) => void;
  freshIds?: Set<number>;
  dense?: boolean;
}) {
  return (
    <ol>
      {events.map((event, index) => {
        const day = dayLabel(event.created_at);
        const header = index === 0 || dayLabel(events[index - 1].created_at) !== day;
        return (
          <li key={event.id}>
            {header ? (
              <div className="sticky top-0 z-10 border-b bg-card/95 px-4 py-1.5 font-mono text-[10.5px] tracking-[0.14em] text-muted-foreground uppercase backdrop-blur">
                {day}
              </div>
            ) : null}
            <button
              type="button"
              onClick={() => onSelect(event)}
              className={cn(
                "group relative grid w-full grid-cols-[52px_minmax(0,1fr)_auto] items-start gap-3 border-b px-4 text-left transition-colors hover:bg-accent/50",
                dense ? "py-2.5" : "py-3",
                freshIds?.has(event.id) && "animate-in fade-in slide-in-from-top-1 bg-signal/5 duration-500",
              )}
            >
              <SeverityRail severity={event.severity} />
              <time dateTime={event.created_at} className="pt-0.5 font-mono text-[12.5px] text-muted-foreground tabular">
                {clock(event.created_at)}
              </time>
              <span className="min-w-0">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{title(event.type, event.summary)}</span>
                  {event.simulated ? <span className="font-mono text-[10px] text-chart-2 uppercase">sim</span> : null}
                </span>
                <span className="mt-0.5 block truncate text-[13px] text-muted-foreground">{event.summary}</span>
                <span className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[11.5px] text-muted-foreground">
                  {event.username ? <span>User: <span className="text-foreground/85">{event.username}</span></span> : null}
                  {event.channel_name ? <span>#{event.channel_name}</span> : null}
                  <span>Action: <span className="text-foreground/85">{event.action_taken}</span></span>
                </span>
              </span>
              <span className="flex items-center gap-1.5 pt-0.5">
                <SeverityBadge severity={event.severity} />
                <ChevronRight className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
