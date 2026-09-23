import { SEVERITY } from "@/lib/format";
import type { Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const { label, color } = SEVERITY[severity];
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 font-mono text-[10.5px] font-medium tracking-wide uppercase", className)}
      style={{ color, borderColor: `color-mix(in oklch, ${color} 35%, transparent)`, background: `color-mix(in oklch, ${color} 10%, transparent)` }}
    >
      <span className="size-1.5 rounded-full" style={{ background: color }} aria-hidden />
      {label}
    </span>
  );
}

export function SeverityRail({ severity }: { severity: Severity }) {
  return <span className="absolute inset-y-2 left-0 w-0.5 rounded-full" style={{ background: SEVERITY[severity].color }} aria-hidden />;
}
