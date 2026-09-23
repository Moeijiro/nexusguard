"use client";

import { createContext, useContext, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Activity, ChevronsUpDown, FlaskConical, Gavel, LayoutDashboard, LogOut, Menu, Settings2, SlidersHorizontal } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { RaidModeBanner, RaidModeButton } from "@/components/app/raid-mode";
import { useSession } from "@/components/app/session";
import { ErrorState, PageLoading } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import type { GuildDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

interface GuildState {
  guild: GuildDetail;
  setGuild: (guild: GuildDetail) => void;
  refreshGuild: () => void;
}

const GuildContext = createContext<GuildState | null>(null);

export function useGuild(): GuildState {
  const value = useContext(GuildContext);
  if (!value) throw new Error("useGuild must be used inside <GuildShell>");
  return value;
}

const NAV = [
  { segment: "", label: "Overview", icon: LayoutDashboard },
  { segment: "/events", label: "Events", icon: Activity },
  { segment: "/rules", label: "Protection rules", icon: SlidersHorizontal },
  { segment: "/moderation", label: "Moderation", icon: Gavel },
  { segment: "/settings", label: "Settings", icon: Settings2 },
];

export function GuildInitial({ name, icon, className }: { name: string; icon: string | null; className?: string }) {
  if (icon) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={icon} alt="" className={cn("size-8 rounded-md", className)} />;
  }
  const letters = name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  return <span className={cn("flex size-8 items-center justify-center rounded-md border bg-secondary font-mono text-[11px] font-semibold", className)}>{letters}</span>;
}

function Sidebar({ guild, onNavigate }: { guild: GuildDetail; onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const user = useSession();
  const base = `/servers/${guild.id}`;
  const guilds = useApi(() => api.guilds(), "sidebar-guilds");

  async function signOut() {
    await api.logout().catch(() => undefined);
    router.push("/login");
  }

  return (
    <div className="flex h-full flex-col">
      <div className="px-4 pt-4 pb-3"><Link href="/servers" onClick={onNavigate}><Logo /></Link></div>
      <div className="px-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button" className="flex w-full items-center gap-2.5 rounded-md border bg-background/40 p-2 text-left hover:bg-accent/60" aria-label="Switch server">
              <GuildInitial name={guild.name} icon={guild.icon_url} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{guild.name}</span>
                <span className="block font-mono text-[10.5px] text-muted-foreground">{guild.member_count.toLocaleString("en")} members</span>
              </span>
              <ChevronsUpDown className="size-4 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-60">
            <DropdownMenuLabel>Servers</DropdownMenuLabel>
            {guilds.data?.map((g) => (
              <DropdownMenuItem key={g.id} onSelect={() => { router.push(`/servers/${g.id}`); onNavigate?.(); }}>
                <GuildInitial name={g.name} icon={g.icon_url} className="size-5 text-[9px]" />
                <span className="truncate">{g.name}</span>
                {g.raid_mode ? <span className="ml-auto size-2 rounded-full bg-sev-critical" aria-label="Raid mode" /> : null}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => router.push("/servers")}>All servers</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <nav aria-label="Server" className="mt-4 space-y-0.5 px-3">
        {NAV.map((item) => {
          const href = `${base}${item.segment}`;
          const active = item.segment ? pathname.startsWith(href) : pathname === base;
          return (
            <Link
              key={item.segment}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                active ? "bg-sidebar-accent font-medium text-foreground" : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
              )}
            >
              <item.icon className={cn("size-4", active && "text-signal")} aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto space-y-3 border-t p-3">
        {user.is_demo ? (
          <p className="flex items-start gap-2 rounded-md border border-chart-2/30 bg-chart-2/10 px-2.5 py-2 text-[11.5px] text-chart-2">
            <FlaskConical className="mt-0.5 size-3.5 shrink-0" />
            Demo mode — simulated servers and events. Nothing reaches Discord.
          </p>
        ) : null}
        <div className="flex items-center gap-2 px-1">
          {user.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.avatar_url} alt="" className="size-7 rounded-full" />
          ) : (
            <span className="flex size-7 items-center justify-center rounded-full bg-secondary font-mono text-[10px]">{(user.global_name ?? user.username).slice(0, 2).toUpperCase()}</span>
          )}
          <span className="min-w-0 flex-1 truncate text-sm">{user.global_name ?? user.username}</span>
          <Button variant="ghost" size="icon-sm" onClick={signOut} aria-label="Sign out"><LogOut /></Button>
        </div>
      </div>
    </div>
  );
}

export function GuildShell({ guildId, children }: { guildId: string; children: React.ReactNode }) {
  const detail = useApi(() => api.guild(guildId), `guild-${guildId}`);
  const [open, setOpen] = useState(false);

  if (detail.loading) return <div className="p-6"><PageLoading /></div>;
  if (detail.error || !detail.data) {
    return (
      <div className="mx-auto max-w-lg p-6 pt-24">
        <ErrorState message={detail.error ?? "Server not found."} />
        <div className="mt-4 text-center"><Button asChild variant="outline"><Link href="/servers">Back to servers</Link></Button></div>
      </div>
    );
  }
  const guild = detail.data;
  const state: GuildState = { guild, setGuild: (next) => detail.mutate(() => next), refreshGuild: detail.reload };
  const status = guild.raid.enabled ? "Raid mode" : guild.modules_enabled === guild.modules_total ? "Fully protected" : "Protected";

  return (
    <GuildContext.Provider value={state}>
      <div className="min-h-screen lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
        <aside className="sticky top-0 hidden h-screen border-r bg-sidebar lg:block"><Sidebar guild={guild} /></aside>
        <div className="min-w-0">
          <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur-md">
            <div className="flex h-14 items-center gap-3 px-4 sm:px-6">
              <Sheet open={open} onOpenChange={setOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation"><Menu /></Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-72 bg-sidebar p-0">
                  <SheetTitle className="sr-only">Navigation</SheetTitle>
                  <Sidebar guild={guild} onNavigate={() => setOpen(false)} />
                </SheetContent>
              </Sheet>
              <span className={cn("inline-flex items-center gap-2 rounded-full border px-2.5 py-1 font-mono text-[11px] uppercase", guild.raid.enabled ? "border-sev-critical/40 text-sev-critical" : "border-signal/30 text-signal")}>
                <span className={cn("size-1.5 rounded-full", guild.raid.enabled ? "bg-sev-critical" : "bg-signal")} />
                {status}
              </span>
              <span className="hidden font-mono text-[11px] text-muted-foreground sm:inline">
                {guild.modules_enabled}/{guild.modules_total} modules
              </span>
              <div className="ml-auto"><RaidModeButton guild={guild} onChange={state.setGuild} /></div>
            </div>
            <RaidModeBanner guild={guild} />
          </header>
          <main id="main" className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6">{children}</main>
        </div>
      </div>
    </GuildContext.Provider>
  );
}
