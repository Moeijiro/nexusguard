import { cn } from "@/lib/utils";

/** A shield with a node in it: detection at the centre of the network. */
export function Logo({ className, wordmark = true }: { className?: string; wordmark?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <span className="flex size-7 items-center justify-center rounded-md border border-signal/40 bg-signal/10 text-signal" aria-hidden>
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3 4.5 6v5.5c0 4.6 3.1 8 7.5 9.5 4.4-1.5 7.5-4.9 7.5-9.5V6L12 3z" />
          <circle cx="12" cy="11.5" r="2.2" fill="currentColor" />
        </svg>
      </span>
      {wordmark ? <span className="font-semibold tracking-tight">Nexus<span className="text-signal">Guard</span></span> : null}
    </span>
  );
}
