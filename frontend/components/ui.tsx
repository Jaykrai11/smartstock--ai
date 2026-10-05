"use client";
import { ReactNode } from "react";
import type { Action } from "@/lib/types";
import { REASONS } from "@/lib/format";

export const Panel = ({ title, aside, children, className = "" }: { title?: string; aside?: ReactNode; children: ReactNode; className?: string }) => (
  <section className={`rounded-md border border-line bg-white ${className}`}>
    {(title || aside) && (
      <header className="flex items-center justify-between gap-4 border-b border-line px-5 py-3">
        <h2 className="text-[15px] font-semibold">{title}</h2>{aside}
      </header>
    )}
    <div className="p-5">{children}</div>
  </section>
);

export const PageTitle = ({ title, sub }: { title: string; sub?: string }) => (
  <div className="mb-6"><h1 className="text-2xl font-semibold tracking-tight">{title}</h1>{sub && <p className="mt-1 max-w-2xl text-sm text-mute">{sub}</p>}</div>
);

/** A strip of figures separated by hairlines (one panel, not a grid of identical cards). */
export const KpiStrip = ({ items }: { items: { label: string; value: string; note?: string }[] }) => (
  <div className="grid grid-cols-2 divide-line rounded-md border border-line bg-white md:grid-cols-4 md:divide-x">
    {items.map((k) => (
      <div key={k.label} className="border-b border-line px-5 py-4 last:border-b-0 md:border-b-0">
        <div className="text-sm text-mute">{k.label}</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums">{k.value}</div>
        {k.note && <div className="mt-0.5 text-xs text-mute">{k.note}</div>}
      </div>
    ))}
  </div>
);

const ACTION_STYLE: Record<Action, string> = { INCREASE: "bg-sky-100 text-sky-900", REDUCE: "bg-amber-100 text-amber-900", MAINTAIN: "bg-slate-100 text-slate-700" };
const ACTION_LABEL: Record<Action, string> = { INCREASE: "Increase stock", REDUCE: "Reduce stock", MAINTAIN: "Keep as is" };
export const ActionBadge = ({ action }: { action: Action }) => (
  <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${ACTION_STYLE[action]}`}>{ACTION_LABEL[action]}</span>
);

export const Reasons = ({ codes }: { codes: string[] }) => (
  <ul className="space-y-1 text-sm">{codes.map((c) => <li key={c} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal" />{REASONS[c] ?? c}</li>)}</ul>
);

export const Loading = ({ slow, label = "Loading…" }: { slow?: boolean; label?: string }) => (
  <div role="status" className="flex items-center gap-3 py-10 text-sm text-mute">
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-teal" />
    <span>{slow ? "Still working — the free-tier API sleeps when idle and can take up to a minute to wake up." : label}</span>
  </div>
);

export const ErrorBox = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div role="alert" className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
    <div className="font-medium">Something went wrong</div><p className="mt-0.5">{message}</p>
    {onRetry && <button onClick={onRetry} className="mt-2 font-medium underline">Try again</button>}
  </div>
);

export const Empty = ({ children }: { children: ReactNode }) => (
  <div className="rounded-md border border-dashed border-line bg-white px-6 py-14 text-center text-sm text-mute">{children}</div>
);

const fieldCls = "w-full rounded border border-line bg-white px-3 py-2 text-sm focus:border-teal";
export const Field = ({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) => (
  <label className="block text-sm"><span className="mb-1 block font-medium">{label}</span>{children}{hint && <span className="mt-1 block text-xs text-mute">{hint}</span>}</label>
);
export const Select = ({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: string[] }) => (
  <select className={fieldCls} value={value} onChange={(e) => onChange(e.target.value)}>{options.map((o) => <option key={o}>{o}</option>)}</select>
);
export const NumberField = ({ value, onChange, min, max, step = 1, placeholder }: { value: string; onChange: (v: string) => void; min?: number; max?: number; step?: number; placeholder?: string }) => (
  <input className={fieldCls} type="number" inputMode="decimal" value={value} min={min} max={max} step={step} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
);
export const Button = ({ children, loading, ...p }: { children: ReactNode; loading?: boolean } & React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button {...p} disabled={loading || p.disabled} className="rounded bg-ink px-4 py-2 text-sm font-medium text-white hover:bg-[#1b3a5e] disabled:opacity-60">{loading ? "Working…" : children}</button>
);
export const opt = (s: string): number | undefined => (s.trim() === "" || Number.isNaN(Number(s)) ? undefined : Number(s));
