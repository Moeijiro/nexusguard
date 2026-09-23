"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, LogOut, Plus, ServerOff } from "lucide-react";
import { GuildInitial } from "@/components/app/guild-shell";
import { useSession } from "@/components/app/session";
import { Empty, ErrorState, LoadingRows } from "@/components/app/ui";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ServersPage() {
  const user = useSession();
  const router = useRouter();
  const guilds = useApi(() => api.guilds(), "guilds");
  const mode = useApi(() => api.mode(), "mode");

  return (
    <div className="min-h-screen bg-grid">
      <header className="border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4 sm:px-6">
          <Logo />
          <span className="ml-auto hidden text-sm text-muted-foreground sm:inline">{user.global_name ?? user.username}</span>
          <Button variant="ghost" size="icon-sm" aria-label="Sign out" onClick={async () => { await api.logout().catch(() => undefined); router.push("/login"); }}>
            <LogOut />
          </Button>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        <p className="font-mono text-[11px] tracking-[0.14em] text-signal uppercase">{user.is_demo ? "Demo · simulated servers" : "Your servers"}</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">Choose a server</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {user.is_demo
            ? "These servers and everything in them are simulated. Change anything you like."
            : "Servers where you're the owner or have Manage Server, and NexusGuard is installed."}
        </p>

        <div className="mt-8">
          {guilds.loading ? (
            <LoadingRows rows={3} />
          ) : guilds.error ? (
            <ErrorState message={guilds.error} onRetry={guilds.reload} />
          ) : guilds.data?.length ? (
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {guilds.data.map((guild) => (
                <li key={guild.id}>
                  <Link href={`/servers/${guild.id}`} className="group flex items-center gap-4 rounded-lg border bg-card p-4 transition-colors hover:border-signal/40">
                    <GuildInitial name={guild.name} icon={guild.icon_url} className="size-11 text-sm" />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate font-medium">{guild.name}</span>
                        {guild.is_demo ? <span className="font-mono text-[10px] text-chart-2 uppercase">sim</span> : null}
                      </span>
                      <span className="mt-1 flex flex-wrap gap-x-3 font-mono text-[11.5px] text-muted-foreground">
                        <span>{guild.modules_enabled}/{guild.modules_total} modules</span>
                        <span>{guild.events_today} events · 24 h</span>
                        <span>{guild.member_count.toLocaleString("en")} members</span>
                      </span>
                    </span>
                    <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10.5px] uppercase", guild.raid_mode ? "border-sev-critical/40 text-sev-critical" : "border-signal/30 text-signal")}>
                      {guild.raid_mode ? "Raid mode" : "Protected"}
                    </span>
                    <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className="rounded-lg border border-dashed bg-card/50">
              <Empty
                icon={ServerOff}
                title="No servers to manage yet"
                description="Add NexusGuard to a server where you have Manage Server, then sign in again so your permissions are refreshed."
              />
            </div>
          )}
        </div>

        {!user.is_demo && mode.data?.bot_invite_url ? (
          <Button asChild variant="outline" className="mt-6">
            <a href={mode.data.bot_invite_url}><Plus />Add NexusGuard to a server</a>
          </Button>
        ) : null}
      </main>
    </div>
  );
}
