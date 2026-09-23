"use client";

import { CircleSlash, Check, Clock, FlaskConical, TriangleAlert, X } from "lucide-react";
import { SeverityBadge } from "@/components/app/severity";
import { Mono } from "@/components/app/ui";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ACTION_LABEL, dateTime, title } from "@/lib/format";
import type { ActionResult, SecurityEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS: Record<ActionResult["status"], { icon: React.ComponentType<{ className?: string }>; className: string; label: string }> = {
  done: { icon: Check, className: "text-signal", label: "Done" },
  simulated: { icon: FlaskConical, className: "text-chart-2", label: "Simulated" },
  skipped: { icon: CircleSlash, className: "text-muted-foreground", label: "Skipped" },
  suppressed: { icon: Clock, className: "text-sev-medium", label: "Suppressed" },
  failed: { icon: X, className: "text-destructive", label: "Failed" },
};

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[110px_minmax(0,1fr)] gap-3 py-2 text-sm">
      <dt className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

export function EventSheet({ event, onClose }: { event: SecurityEvent | null; onClose: () => void }) {
  return (
    <Sheet open={event !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        {event ? (
          <>
            <SheetHeader className="border-b pb-4">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={event.severity} />
                {event.simulated ? <span className="rounded border border-chart-2/40 px-1.5 py-0.5 font-mono text-[10px] text-chart-2 uppercase">Simulated</span> : null}
              </div>
              <SheetTitle className="text-lg">{title(event.type, event.summary)}</SheetTitle>
              <SheetDescription>{event.summary}</SheetDescription>
            </SheetHeader>
            <div className="space-y-6 px-4 pb-8">
              <dl className="divide-y">
                <Row label="Time"><Mono>{dateTime(event.created_at)}</Mono></Row>
                <Row label="Type"><Mono>{event.type}</Mono></Row>
                <Row label="Module"><Mono>{event.module}</Mono></Row>
                {event.username ? <Row label="Member">{event.username} <Mono className="text-muted-foreground">{event.user_id}</Mono></Row> : null}
                {event.channel_id ? <Row label="Channel">#{event.channel_name ?? event.channel_id}</Row> : null}
                <Row label="Event ID"><Mono>{event.id}</Mono></Row>
              </dl>

              <div>
                <h3 className="mb-2 font-mono text-[11px] tracking-[0.12em] text-muted-foreground uppercase">Action engine</h3>
                {event.actions.length ? (
                  <ol className="space-y-1.5">
                    {event.actions.map((result, index) => {
                      const s = STATUS[result.status];
                      return (
                        <li key={index} className="flex items-start gap-2.5 rounded-md border bg-background/60 px-3 py-2 text-sm">
                          <s.icon className={cn("mt-0.5 size-4 shrink-0", s.className)} />
                          <div className="min-w-0 flex-1">
                            <p className="font-medium">{ACTION_LABEL[result.action] ?? result.action}</p>
                            <p className="text-xs text-muted-foreground">{result.detail}</p>
                          </div>
                          <span className={cn("font-mono text-[10.5px] uppercase", s.className)}>{s.label}</span>
                        </li>
                      );
                    })}
                  </ol>
                ) : (
                  <p className="text-sm text-muted-foreground">Logged only — no action configured for this event.</p>
                )}
              </div>

              {event.notes.length ? (
                <div>
                  <h3 className="mb-2 font-mono text-[11px] tracking-[0.12em] text-muted-foreground uppercase">Rule engine notes</h3>
                  <ul className="space-y-1.5">
                    {event.notes.map((note) => (
                      <li key={note} className="flex gap-2 text-sm"><TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-sev-medium" />{note}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div>
                <h3 className="mb-2 font-mono text-[11px] tracking-[0.12em] text-muted-foreground uppercase">Metadata</h3>
                <pre className="overflow-x-auto rounded-md border bg-background p-3 font-mono text-[11.5px] leading-relaxed text-muted-foreground">
                  {JSON.stringify(event.metadata, null, 2)}
                </pre>
              </div>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
