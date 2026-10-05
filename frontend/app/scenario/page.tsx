"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { n0, n1, pct } from "@/lib/format";
import { Button, Empty, ErrorBox, Field, Loading, NumberField, opt, PageTitle, Panel } from "@/components/ui";
import SeriesPicker, { Pick } from "@/components/SeriesPicker";
import { DemandBand, InventoryLines } from "@/components/charts";
import type { PolicyKpis } from "@/lib/types";

const ROWS: { label: string; get: (k: PolicyKpis) => string; better: "low" | "high" }[] = [
  { label: "Share of demand served (fill rate)", get: (k) => pct(k.fill_rate), better: "high" },
  { label: "Chance of at least one stock-out", get: (k) => pct(k.prob_any_stockout, 0), better: "low" },
  { label: "Average stock on hand", get: (k) => n1(k.avg_inventory), better: "low" },
  { label: "Holding cost", get: (k) => n1(k.holding_cost), better: "low" },
  { label: "Lost-sales cost", get: (k) => n1(k.stockout_cost), better: "low" },
  { label: "Total cost", get: (k) => n1(k.total_cost), better: "low" },
];

export default function ScenarioPage() {
  const [pick, setPick] = useState<Pick>({ item: "", store: "" });
  const [mult, setMult] = useState("1.3"); const [lead, setLead] = useState(""); const [sl, setSl] = useState("0.95"); const [start, setStart] = useState(""); const [aware, setAware] = useState(false);
  const { run, data, error, loading, slow } = useAction(api.simulate);
  const go = () => run({ item_id: pick.item, store_id: pick.store, demand_multiplier: Number(mult), lead_time_days: opt(lead), service_level: Number(sl), starting_inventory: opt(start), planner_aware: aware });
  return (
    <>
      <PageTitle title="What-if scenarios" sub="Simulate the next 28 days 300 times under a demand shock or a slower supplier, and compare a textbook stocking rule with the SmartStock policy." />
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Panel title="Scenario">
          <div className="space-y-4">
            <SeriesPicker value={pick} onChange={setPick} />
            <Field label={`Demand vs forecast: ×${mult}`}><input type="range" className="w-full accent-teal" min={0.5} max={2} step={0.05} value={mult} onChange={(e) => setMult(e.target.value)} /></Field>
            <Field label="Supplier lead time (days)" hint="Blank = simulated value."><NumberField value={lead} onChange={setLead} min={1} max={14} placeholder="Simulated" /></Field>
            <Field label="Service-level target"><NumberField value={sl} onChange={setSl} min={0.5} max={0.999} step={0.01} /></Field>
            <Field label="Starting stock" hint="Blank = simulated value."><NumberField value={start} onChange={setStart} min={0} placeholder="Simulated" /></Field>
            <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1 accent-teal" checked={aware} onChange={(e) => setAware(e.target.checked)} /><span>Planners know about the change in advance<span className="block text-xs text-mute">Off = the shock is a surprise (stress test).</span></span></label>
            <Button onClick={go} loading={loading} disabled={!pick.item}>Run simulation</Button>
          </div>
        </Panel>
        <div className="min-w-0 space-y-6">
          {loading && <Loading slow={slow} label="Running simulations…" />}
          {error && <ErrorBox message={error} onRetry={go} />}
          {!data && !loading && !error && <Empty>Set a scenario and run the simulation.</Empty>}
          {data && !loading && (<>
            <Panel title={`${data.item_id} · ${data.store_id}: ${data.scenario.n_simulations} simulated runs`}>
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-mute"><tr><th className="pb-2 font-medium">Average per run</th><th className="pb-2 text-right font-medium">Textbook rule</th><th className="pb-2 text-right font-medium">SmartStock</th></tr></thead>
                <tbody>{ROWS.map((r) => {
                  const b = data.results.baseline_policy, s = data.results.smartstock_policy;
                  const sv = r.get(s), bv = r.get(b);
                  return <tr key={r.label} className="border-t border-line"><td className="py-2">{r.label}</td><td className="py-2 text-right tabular-nums">{bv}</td><td className="py-2 text-right font-medium tabular-nums">{sv}</td></tr>;
                })}</tbody>
              </table>
              <p className="mt-3 text-xs text-mute">Costs are in simulated currency units. The same random demand is applied to both policies. A cheaper policy can serve fewer customers — read cost and fill rate together.</p>
            </Panel>
            <Panel title="Simulated demand"><DemandBand data={data.trajectory} /></Panel>
            <Panel title="Stock on hand over time"><InventoryLines data={data.trajectory} /></Panel>
          </>)}
        </div>
      </div>
    </>
  );
}
