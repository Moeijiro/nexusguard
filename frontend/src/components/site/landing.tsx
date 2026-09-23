"use client";

import Link from "next/link";
import { motion } from "motion/react";
import {
  ArrowRight,
  AtSign,
  Ban,
  BellRing,
  Bot,
  Copy,
  Database,
  FileClock,
  Gauge,
  Code2,
  LayoutDashboard,
  MessagesSquare,
  Radar,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UserPlus,
  UserRoundCog,
  Workflow,
  Zap,
} from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { SeverityBadge } from "@/components/app/severity";
import { Button } from "@/components/ui/button";
import type { Severity } from "@/lib/types";

const ease = [0.22, 1, 0.36, 1] as const;

function Reveal({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.5, delay, ease }}>
      {children}
    </motion.div>
  );
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="font-mono text-[11px] tracking-[0.16em] text-signal uppercase">{children}</p>;
}

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md">
      <nav aria-label="Main" className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-5 sm:px-8">
        <Link href="/" aria-label="NexusGuard home"><Logo /></Link>
        <ul className="hidden items-center gap-1 text-sm md:flex">
          {[["#architecture", "Architecture"], ["#modules", "Modules"], ["#safety", "Safety"], ["#dashboard", "Dashboard"]].map(([href, label]) => (
            <li key={href}><a href={href} className="rounded-md px-3 py-1.5 text-muted-foreground hover:text-foreground">{label}</a></li>
          ))}
        </ul>
        <div className="ml-auto flex items-center gap-2">
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex"><Link href="/login">Sign in</Link></Button>
          <Button asChild size="sm"><Link href="/login">Open the demo</Link></Button>
        </div>
      </nav>
    </header>
  );
}

const STREAM: { time: string; title: string; detail: string; action: string; severity: Severity }[] = [
  { time: "22:41", title: "Mass mention blocked", detail: "User: vex_drift · @everyone/@here in one message", action: "Message deleted; Warning sent", severity: "high" },
  { time: "22:43", title: "Join spike detected", detail: "14 joins / 10 sec", action: "Moderators notified · Raid mode on", severity: "high" },
  { time: "22:43", title: "Suspicious join", detail: "User: airdrop_4471 · joined during raid mode", action: "Restricted role assigned", severity: "low" },
  { time: "22:47", title: "Spam detected", detail: "User: kai.loop · 8 messages in 1.9 s", action: "Message deleted; Timed out for 10 min", severity: "high" },
  { time: "22:52", title: "Privileged role granted", detail: "@Admin granted to newbie", action: "Moderators notified", severity: "critical" },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b">
      <div className="pointer-events-none absolute inset-0 bg-grid fade-edges" aria-hidden />
      <div className="relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-5 py-16 sm:px-8 sm:py-24 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease }}>
          <Eyebrow>Discord security infrastructure</Eyebrow>
          <h1 className="mt-5 text-4xl leading-[1.05] font-semibold tracking-tight sm:text-5xl lg:text-6xl">
            Server protection that runs on rules you can read.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
            NexusGuard streams joins, messages and role changes through a detection engine, a rule engine and an action
            engine — and shows every decision, and why it was made, on a live dashboard.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="h-11 px-5"><Link href="/login">Open the live demo<ArrowRight data-icon="inline-end" /></Link></Button>
            <Button asChild size="lg" variant="outline" className="h-11 px-5"><a href="#architecture">See the architecture</a></Button>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">The demo runs on simulated servers and events — no Discord account needed.</p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.15, ease }}>
          <div className="overflow-hidden rounded-lg border bg-card shadow-[0_30px_80px_-40px_rgba(0,0,0,0.9)]">
            <div className="flex items-center justify-between border-b px-4 py-2.5">
              <span className="font-mono text-[11px] tracking-[0.12em] text-muted-foreground uppercase">Event stream · Nimbus Labs</span>
              <span className="flex items-center gap-1.5 font-mono text-[10.5px] text-signal uppercase"><span className="size-1.5 animate-pulse rounded-full bg-signal" />Live</span>
            </div>
            <ol>
              {STREAM.map((row, index) => (
                <motion.li
                  key={index}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, delay: 0.5 + index * 0.25, ease }}
                  className="grid grid-cols-[46px_minmax(0,1fr)_auto] gap-3 border-b px-4 py-3 last:border-b-0"
                >
                  <span className="pt-0.5 font-mono text-[12.5px] text-muted-foreground">{row.time}</span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{row.title}</span>
                    <span className="block truncate font-mono text-[11.5px] text-muted-foreground">{row.detail}</span>
                    <span className="block truncate font-mono text-[11.5px] text-muted-foreground">Action: <span className="text-foreground/85">{row.action}</span></span>
                  </span>
                  <SeverityBadge severity={row.severity} />
                </motion.li>
              ))}
            </ol>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

const PIPELINE = [
  { icon: MessagesSquare, name: "Discord events", detail: "joins · messages · role changes · audit log" },
  { icon: Bot, name: "NexusGuard bot", detail: "discord.py adapter → plain event objects" },
  { icon: Radar, name: "Detection engine", detail: "6 detectors, sliding windows" },
  { icon: Scale, name: "Rule engine", detail: "per-guild config, escalation, notes" },
  { icon: Zap, name: "Action engine", detail: "safety limits, one REST executor" },
  { icon: ShieldCheck, name: "Discord action", detail: "delete · timeout · role · alert" },
  { icon: FileClock, name: "Audit log", detail: "events, moderation, flags" },
];

export function Architecture() {
  return (
    <section id="architecture" className="scroll-mt-14 border-b py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Eyebrow>Architecture</Eyebrow>
        <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight">An event pipeline, not a command bot</h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          The engine never imports discord.py. The live bot, the demo simulator and the test suite all run the same
          detectors, rules and actions on plain event objects.
        </p>
        <ol className="mt-12 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-7">
          {PIPELINE.map((step, index) => (
            <Reveal key={step.name} delay={index * 0.05} className="relative">
              <li className="h-full rounded-lg border bg-card p-4">
                <step.icon className="size-5 text-signal" aria-hidden />
                <p className="mt-3 text-sm font-medium">{step.name}</p>
                <p className="mt-1 font-mono text-[11px] leading-relaxed text-muted-foreground">{step.detail}</p>
                <span className="absolute top-3 right-3 font-mono text-[10px] text-muted-foreground">{String(index + 1).padStart(2, "0")}</span>
              </li>
            </Reveal>
          ))}
        </ol>
        <Reveal className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {[
            { icon: LayoutDashboard, name: "Web dashboard", detail: "Next.js · shadcn/ui" },
            { icon: Workflow, name: "FastAPI backend", detail: "OAuth2 · permission checks" },
            { icon: Database, name: "Database", detail: "SQLAlchemy · SQLite / PostgreSQL" },
          ].map((box, index) => (
            <div key={box.name} className="relative flex items-center gap-3 rounded-lg border border-dashed bg-card/60 p-4">
              <box.icon className="size-5 text-chart-2" aria-hidden />
              <div>
                <p className="text-sm font-medium">{box.name}</p>
                <p className="font-mono text-[11px] text-muted-foreground">{box.detail}</p>
              </div>
              {index < 2 ? <span className="absolute top-1/2 -right-2 z-10 hidden -translate-y-1/2 font-mono text-muted-foreground sm:block" aria-hidden>↔</span> : null}
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  );
}

const MODULES = [
  { icon: MessagesSquare, name: "Message flood", rule: "6 messages / 5 s", severity: "medium → high if scripted-fast" },
  { icon: Copy, name: "Duplicate messages", rule: "3 identical / 30 s", severity: "high when it carries a link" },
  { icon: AtSign, name: "Mass mentions", rule: "5 pings or @everyone", severity: "high for @everyone from members" },
  { icon: UserPlus, name: "Raid detection", rule: "10 joins / 10 s", severity: "high → critical if it keeps growing" },
  { icon: Gauge, name: "Account age", rule: "younger than 24 h", severity: "low · flag only · opt-in" },
  { icon: UserRoundCog, name: "Privileged roles", rule: "Admin / Manage roles granted", severity: "critical for Administrator" },
];

export function Modules() {
  return (
    <section id="modules" className="scroll-mt-14 border-b py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Eyebrow>Protection modules</Eyebrow>
        <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight">Six detectors, each with written severity rules</h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">No AI and no scores. Every threshold is configurable per server, and severity comes from rules you can read in the source.</p>
        <div className="mt-12 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m, index) => (
            <Reveal key={m.name} delay={index * 0.04}>
              <div className="h-full rounded-lg border bg-card p-5">
                <m.icon className="size-5 text-signal" aria-hidden />
                <h3 className="mt-4 font-medium">{m.name}</h3>
                <p className="mt-3 font-mono text-[12px] text-foreground/85">{m.rule}</p>
                <p className="mt-1 font-mono text-[11.5px] text-muted-foreground">{m.severity}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const SAFETY = [
  { icon: Ban, title: "No automatic bans", body: "Bans aren't in the action set at all. Kick exists only if you choose it for a message rule." },
  { icon: ShieldAlert, title: "Blast-radius limits", body: "Per-server caps on kicks (5/min), timeouts, role changes and alerts. Past the cap, it logs and alerts instead." },
  { icon: Sparkles, title: "Every decision explained", body: "Escalations, skipped actions and missing prerequisites are written into the event as rule-engine notes." },
  { icon: BellRing, title: "Raid mode you can see", body: "Automatic or manual, time-boxed, with a banner, an alert, and restricted roles for new members — not mass kicks." },
];

export function Safety() {
  return (
    <section id="safety" className="scroll-mt-14 border-b py-20 sm:py-24">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 px-5 sm:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <div>
          <Eyebrow>Safety by design</Eyebrow>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight">Automation that can&apos;t take your server down</h2>
          <p className="mt-3 text-muted-foreground">
            A moderation bot with a bug, or a rule set too tight, can do more damage than a raid. NexusGuard is built
            to fail towards &quot;log and tell a human&quot;.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {SAFETY.map((item, index) => (
            <Reveal key={item.title} delay={index * 0.05}>
              <div className="h-full rounded-lg border bg-card p-5">
                <item.icon className="size-5 text-sev-medium" aria-hidden />
                <h3 className="mt-4 font-medium">{item.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function DashboardCta() {
  return (
    <section id="dashboard" className="scroll-mt-14 py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <div className="relative overflow-hidden rounded-xl border bg-card px-6 py-14 text-center sm:px-12">
            <div className="pointer-events-none absolute inset-0 bg-grid opacity-60" aria-hidden />
            <div className="relative">
              <Eyebrow>Dashboard</Eyebrow>
              <h2 className="mx-auto mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
                Security status, event stream, rule cards and a raid-mode switch.
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
                Sign in with Discord to manage servers where you have Manage Server — or explore two simulated servers
                that keep generating incidents while you watch.
              </p>
              <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
                <Button asChild size="lg" className="h-11 px-5"><Link href="/login">Explore the demo<ArrowRight data-icon="inline-end" /></Link></Button>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <Logo />
        <p className="max-w-md text-xs">A portfolio project. Demo servers, members and events are simulated. Not affiliated with Discord.</p>
        <span className="flex items-center gap-1.5 font-mono text-[11px]"><Code2 className="size-3.5" />MIT licensed</span>
      </div>
    </footer>
  );
}
