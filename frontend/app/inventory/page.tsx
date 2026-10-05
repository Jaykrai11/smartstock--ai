"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { n0, n1, pct, signed } from "@/lib/format";
import { ActionBadge, Button, Empty, ErrorBox, Field, Loading, NumberField, opt, PageTitle, Panel, Reasons } from "@/components/ui";
import SeriesPicker, { Pick } from "@/components/SeriesPicker";
import { PlacementChart } from "@/components/charts";

export default function InventoryPage() {
  const [pick, setPick] = useState<Pick>({ item: "", store: "" });
  const [cur, setCur] = useState(""); const [lead, setLead] = useState(""); const [sl, setSl] = useState("0.95");
  const { run, data, error, loading, slow } = useAction(api.recommendation);
  const go = () => run({ item_id: pick.item, store_id: pick.store, current_inventory: opt(cur), lead_time_days: opt(lead), service_level: Number(sl) });
  return (
    <>
      <PageTitle title="Stock recommendation" sub="How much stock each store should hold for this product, given forecast demand, supplier lead time and the warehouse's limited supply." />
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Panel title="Inputs">
          <div className="space-y-4">
            <SeriesPicker value={pick} onChange={setPick} />
            <Field label="Current stock in this store" hint="Leave blank to use the simulated value."><NumberField value={cur} onChange={setCur} min={0} placeholder="Simulated" /></Field>
            <Field label="Supplier lead time (days)" hint="Leave blank to use the simulated value."><NumberField value={lead} onChange={setLead} min={1} max={14} placeholder="Simulated" /></Field>
            <Field label="Service-level target" hint="Chance of not running out between deliveries."><NumberField value={sl} onChange={setSl} min={0.5} max={0.999} step={0.01} /></Field>
            <Button onClick={go} loading={loading} disabled={!pick.item}>Get recommendation</Button>
          </div>
        </Panel>
        <div className="min-w-0 space-y-6">
          {loading && <Loading slow={slow} label="Optimizing stock…" />}
          {error && <ErrorBox message={error} onRetry={go} />}
          {!data && !loading && !error && <Empty>Choose a product and store to see how much stock to hold.</Empty>}
          {data && !loading && (<>
            <Panel title={`${data.item_id} · ${data.store_id}`} aside={<ActionBadge action={data.action} />}>
              <div className="grid gap-6 md:grid-cols-[1fr_1fr]">
                <div>
                  <div className="text-sm text-mute">Stock on hand → recommended</div>
                  <div className="mt-1 flex items-baseline gap-3 tabular-nums"><span className="text-2xl text-mute">{n0(data.inventory.current)}</span><span className="text-mute">→</span><span className="text-4xl font-semibold">{n0(data.inventory.recommended)}</span><span className="text-base font-medium">{signed(data.inventory.delta)} units</span></div>
                  <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    <dt className="text-mute">Expected demand ({data.forecast.horizon_days} days)</dt><dd className="text-right tabular-nums">{n0(data.forecast.mean_total)}</dd>
                    <dt className="text-mute">High-demand case (P90)</dt><dd className="text-right tabular-nums">{n0(data.forecast.p90_total)}</dd>
                    <dt className="text-mute">Safety stock</dt><dd className="text-right tabular-nums">{n1(data.inventory.safety_stock)}</dd>
                    <dt className="text-mute">Lead time</dt><dd className="text-right tabular-nums">{data.inventory.lead_time_days} days</dd>
                    <dt className="text-mute">Service level reached</dt><dd className="text-right tabular-nums">{pct(data.service_level)} <span className="text-mute">(target {pct(data.target_service_level, 0)})</span></dd>
                  </dl>
                </div>
                <div><div className="mb-2 text-sm font-medium">Why</div><Reasons codes={data.reason} /></div>
              </div>
            </Panel>
            <Panel title={`All stores for ${data.item_id}`} aside={<span className="text-xs text-mute">Warehouse supply: {n0(data.solver.warehouse_supply_units)} units</span>}>
              <PlacementChart rows={data.placement} selected={data.store_id} />
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-mute"><tr><th className="pb-2 font-medium">Store</th><th className="pb-2 text-right font-medium">Now</th><th className="pb-2 text-right font-medium">Recommended</th><th className="pb-2 text-right font-medium">Service level</th><th className="pb-2 pl-4 font-medium">Action</th></tr></thead>
                  <tbody>{data.placement.map((r) => (
                    <tr key={r.store_id} className={`border-t border-line ${r.store_id === data.store_id ? "bg-teal-soft/60 font-medium" : ""}`}>
                      <td className="py-2">{r.store_id}</td><td className="py-2 text-right tabular-nums">{n0(r.current)}</td><td className="py-2 text-right tabular-nums">{n0(r.recommended)} <span className="font-normal text-mute">({signed(r.delta)})</span></td>
                      <td className="py-2 text-right tabular-nums">{pct(r.expected_service_level)}</td><td className="py-2 pl-4"><ActionBadge action={r.action} /></td>
                    </tr>))}</tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-mute">{data.assumptions.note}</p>
            </Panel>
          </>)}
        </div>
      </div>
    </>
  );
}
