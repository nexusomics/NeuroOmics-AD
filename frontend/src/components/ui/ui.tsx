import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card p-5 ${className}`}>{children}</div>;
}

export function StatCard({ label, value, accent = "text-teal-300", hint }: { label: string; value: ReactNode; accent?: string; hint?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <div className="text-[11px] font-bold uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-3xl font-extrabold ${accent}`}>{value}</div>
      {hint && <div className="text-xs text-slate-500">{hint}</div>}
    </Card>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "teal" | "cyan" | "amber" | "rose" | "slate" | "emerald" }) {
  return <span className={`badge-${tone}`}>{children}</span>;
}

export function Spinner({ label = "Working…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-slate-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
      <div className="text-sm">{label}</div>
    </div>
  );
}

export function EmptyState({ icon = "◌", title, hint }: { icon?: string; title: string; hint?: string }) {
  return (
    <Card className="flex flex-col items-center gap-2 py-12 text-center">
      <div className="text-3xl text-slate-600">{icon}</div>
      <div className="font-semibold text-slate-300">{title}</div>
      {hint && <div className="max-w-md text-sm text-slate-500">{hint}</div>}
    </Card>
  );
}

export function ErrorBanner({ error }: { error: string }) {
  return (
    <div className="mb-4 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
      ⚠ {error}
    </div>
  );
}

export function Progress({ value, tone = "bg-teal-500" }: { value: number; tone?: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
      <div className={`h-full rounded-full ${tone} transition-all`} style={{ width: `${Math.min(100, value)}%` }} />
    </div>
  );
}
