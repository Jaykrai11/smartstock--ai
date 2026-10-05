"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";

const NAV = [
  { href: "/", label: "Overview" }, { href: "/forecast", label: "Demand forecast" }, { href: "/inventory", label: "Stock recommendation" },
  { href: "/scenario", label: "What-if scenarios" }, { href: "/model", label: "Model & validation" },
];

function ApiStatus() {
  const { data, error, loading, slow } = useAsync(() => api.health());
  const state = loading ? (slow ? "Waking up the API…" : "Connecting…") : error ? "API unreachable" : "API online";
  const dot = loading ? "bg-amber-400" : error ? "bg-red-400" : "bg-emerald-400";
  return (
    <div className="px-5 py-4 text-xs text-slate-300" aria-live="polite">
      <div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${dot}`} />{state}</div>
      {data?.model_version && <div className="mt-1 text-slate-400">Model {data.model_version}</div>}
    </div>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  return (
    <div className="min-h-screen md:flex">
      <aside className="bg-ink text-white md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0 md:flex md:flex-col">
        <div className="px-5 pb-3 pt-5"><div className="text-lg font-semibold tracking-tight">SmartStock AI</div><div className="text-xs text-slate-400">Demand, stock and placement</div></div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:overflow-visible" aria-label="Main">
          {NAV.map((n) => {
            const on = n.href === "/" ? path === "/" : path.startsWith(n.href);
            return <Link key={n.href} href={n.href} aria-current={on ? "page" : undefined} className={`whitespace-nowrap rounded px-3 py-2 text-sm ${on ? "bg-white/15 font-medium" : "text-slate-300 hover:bg-white/10"}`}>{n.label}</Link>;
          })}
        </nav>
        <div className="hidden md:block"><ApiStatus /></div>
      </aside>
      <main className="min-w-0 flex-1">
        <div className="border-b border-amber-200 bg-amber-50 px-6 py-2 text-xs text-amber-900">
          Portfolio demo: lead times, costs, current stock and capacities are <strong>simulated</strong>. Demand data comes from the forecasting dataset.
        </div>
        <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
      </main>
    </div>
  );
}
