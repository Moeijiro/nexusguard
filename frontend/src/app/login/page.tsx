"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FlaskConical, Loader2, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";

const ERRORS: Record<string, string> = {
  access_denied: "You cancelled the Discord login.",
  invalid_state: "That login link expired or didn't start here. Try again.",
  missing_code: "Discord didn't return a login code. Try again.",
  discord_error: "Discord couldn't be reached. Try again in a moment.",
};

function DiscordMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden>
      <path d="M20.3 4.4A19.6 19.6 0 0 0 15.4 3l-.6 1.3a18 18 0 0 0-5.6 0L8.6 3a19.5 19.5 0 0 0-4.9 1.5C.6 9.1-.3 13.6.1 18a19.8 19.8 0 0 0 6 3l1.3-2a12.8 12.8 0 0 1-2-1l.5-.4a14 14 0 0 0 12.2 0l.5.4a12.7 12.7 0 0 1-2 1l1.3 2a19.7 19.7 0 0 0 6-3c.5-5.1-.8-9.6-3.6-13.6ZM8 15.3c-1.2 0-2.2-1.1-2.2-2.4S6.8 10.5 8 10.5s2.2 1.1 2.2 2.4S9.2 15.3 8 15.3Zm8 0c-1.2 0-2.2-1.1-2.2-2.4s1-2.4 2.2-2.4 2.2 1.1 2.2 2.4-1 2.4-2.2 2.4Z" />
    </svg>
  );
}

function Login() {
  const router = useRouter();
  const params = useSearchParams();
  const mode = useApi(() => api.mode(), "mode");
  const [busy, setBusy] = useState(false);
  const error = params.get("error");

  async function demo() {
    setBusy(true);
    try {
      await api.demoLogin();
      router.push("/servers");
    } catch {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-5 py-16">
      <div className="pointer-events-none absolute inset-0 bg-grid fade-edges" aria-hidden />
      <main id="main" className="relative w-full max-w-sm">
        <Link href="/" className="mb-10 flex justify-center"><Logo /></Link>
        <div className="rounded-lg border bg-card p-6">
          <h1 className="text-lg font-semibold">Sign in to the dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Discord login shows the servers you own or can manage (Manage Server). NexusGuard asks only for your
            identity and server list.
          </p>
          {error ? <p role="alert" className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{ERRORS[error] ?? "Sign-in failed."}</p> : null}
          <div className="mt-6 space-y-2.5">
            {mode.data?.discord_login ? (
              <Button asChild className="h-10 w-full bg-[#5865F2] text-white hover:bg-[#4752c4]">
                <a href={api.loginUrl}><DiscordMark />Continue with Discord</a>
              </Button>
            ) : mode.data ? (
              <p className="rounded-md border px-3 py-2 text-xs text-muted-foreground">
                Discord login isn&apos;t configured on this instance (no client ID/secret). The demo works without it.
              </p>
            ) : null}
            {mode.data?.demo ? (
              <Button variant="outline" className="h-10 w-full" onClick={demo} disabled={busy}>
                {busy ? <Loader2 className="animate-spin" /> : <FlaskConical />}
                Explore the demo
              </Button>
            ) : null}
          </div>
        </div>
        <p className="mt-5 flex items-start gap-2 text-xs text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-3.5 shrink-0 text-signal" />
          Your Discord token is used once to read your server list and is not stored. Demo mode uses simulated servers and never touches Discord.
        </p>
      </main>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <Login />
    </Suspense>
  );
}
