"use client";

import { useState } from "react";
import { Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { GuildDetail } from "@/lib/types";

export function RaidModeBanner({ guild }: { guild: GuildDetail }) {
  if (!guild.raid.enabled) return null;
  return (
    <div role="status" className="border-b border-sev-critical/40 bg-sev-critical/10">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm sm:px-6">
        <span className="relative flex size-2.5">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-sev-critical opacity-60" />
          <span className="relative inline-flex size-2.5 rounded-full bg-sev-critical" />
        </span>
        <span className="font-mono text-[12px] font-semibold tracking-[0.14em] text-sev-critical uppercase">Raid mode active</span>
        <span className="text-muted-foreground">
          {guild.raid.reason ?? "Enabled"} · by {guild.raid.by ?? "unknown"} · {timeAgo(guild.raid.since)}
          {guild.raid.until ? ` · ends ${new Date(guild.raid.until).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}` : " · until turned off"}
        </span>
      </div>
    </div>
  );
}

export function RaidModeButton({ guild, onChange }: { guild: GuildDetail; onChange: (guild: GuildDetail) => void }) {
  const [open, setOpen] = useState(false);
  const [minutes, setMinutes] = useState("30");
  const [busy, setBusy] = useState(false);
  const enabled = guild.raid.enabled;

  async function apply() {
    setBusy(true);
    try {
      const next = await api.raidMode(guild.id, !enabled, !enabled && minutes !== "0" ? Number(minutes) : undefined);
      onChange(next);
      toast[enabled ? "success" : "warning"](enabled ? "Raid mode disabled" : "Raid mode enabled", {
        description: next.alert_channel_id ? "Moderators were alerted." : "No alert channel is configured.",
      });
      setOpen(false);
    } catch (err) {
      toast.error("Couldn't change raid mode", { description: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button
        variant={enabled ? "destructive" : "outline"}
        onClick={() => setOpen(true)}
        className={enabled ? "" : "border-sev-critical/40 text-sev-critical hover:bg-sev-critical/10 hover:text-sev-critical"}
      >
        {enabled ? <ShieldCheck /> : <ShieldAlert />}
        {enabled ? "Disable raid mode" : "Enable raid mode"}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{enabled ? "Disable raid mode?" : "Enable raid mode?"}</DialogTitle>
            <DialogDescription>
              {enabled
                ? "New members will join normally again. Detection keeps running."
                : "Every new member gets the restricted role (if configured), every join is logged, and moderators are alerted. Nobody is banned or kicked."}
            </DialogDescription>
          </DialogHeader>
          {!enabled ? (
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="raid-minutes">Switch off automatically</label>
              <Select value={minutes} onValueChange={setMinutes}>
                <SelectTrigger id="raid-minutes" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="15">After 15 minutes</SelectItem>
                  <SelectItem value="30">After 30 minutes</SelectItem>
                  <SelectItem value="60">After 1 hour</SelectItem>
                  <SelectItem value="240">After 4 hours</SelectItem>
                  <SelectItem value="0">Never — I&apos;ll turn it off</SelectItem>
                </SelectContent>
              </Select>
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant={enabled ? "default" : "destructive"} onClick={apply} disabled={busy}>
              {busy ? <Loader2 className="animate-spin" /> : null}
              {enabled ? "Disable" : "Enable raid mode"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
