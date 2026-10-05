"use client";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { n0, pct, signed, day } from "@/lib/format";
import { ActionBadge, ErrorBox, KpiStrip, Loading, PageTitle, Panel } from "@/components/ui";
import { NetworkChart } from "@/components/charts";

export default function Overview() {
  const { data, error, loading, slow, retry } = useAsync(() => api.overview());
  return (
    <>
      <PageTitle title="Network overview" sub="Total demand across every product and store, the stock decisions the optimizer recommends, and how the approach performed in a back-test." />
      {loading && <Loading slow={slow} />}
      {error && <ErrorBox message={error} onRetry={retry} />}
      {data && (
        <div className="space-y-6">
          <Panel title="Units sold: last 8 weeks and next 28 days">
            <NetworkChart data={data.network_demand} />
          </Panel>
          <KpiStrip items={[
            { label: "Expected demand, next 28 days", value: `${n0(data.forecast_units_28d)} units`, note: `${data.n_items} products × ${data.n_stores} stores` },
            { label: "Expected service level", value: pct(data.mean_expected_service_level), note: "Chance of not running out in a replenishment cycle" },
            { label: "Need more stock", value: `${data.actions.INCREASE} of ${data.n_series}`, note: "product-store pairs" },
            { label: "Holding too much", value: `${data.actions.REDUCE} of ${data.n_series}`, note: "product-store pairs" },
          ]} />
          <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
            <Panel title="Largest restock needs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-mute"><tr><th className="pb-2 font-medium">Product</th><th className="pb-2 font-medium">Store</th><th className="pb-2 text-right font-medium">Now</th><th className="pb-2 text-right font-medium">Recommended</th><th className="pb-2 pl-4 font-medium">Action</th></tr></thead>
                  <tbody>{data.top_actions.map((r) => (
                    <tr key={r.item_id + r.store_id} className="border-t border-line">
                      <td className="py-2 pr-2">{r.item_id}</td><td className="py-2">{r.store_id}</td>
                      <td className="py-2 text-right tabular-nums">{n0(r.current)}</td><td className="py-2 text-right tabular-nums">{n0(r.recommended)} <span className="text-mute">({signed(r.delta)})</span></td>
                      <td className="py-2 pl-4"><ActionBadge action={r.action} /></td>
                    </tr>))}</tbody>
                </table>
              </div>
            </Panel>
            <Panel title="Back-test vs textbook safety stock">
              {data.backtest_95 ? (
                <div className="space-y-3 text-sm">
                  <p>Over the last 112 days of held-out data, at a 95% service target:</p>
                  <ul className="space-y-1 tabular-nums">
                    <li>Total cost <strong>{data.backtest_95.total_cost_change_pct > 0 ? "+" : ""}{data.backtest_95.total_cost_change_pct}%</strong></li>
                    <li>Fill rate <strong>{data.backtest_95.fill_rate_change_pts > 0 ? "+" : ""}{data.backtest_95.fill_rate_change_pts} pts</strong></li>
                    <li>Average stock <strong>{data.backtest_95.avg_inventory_change_pct > 0 ? "+" : ""}{data.backtest_95.avg_inventory_change_pct}%</strong></li>
                  </ul>
                  <p className="text-xs text-mute">{data.backtest_note}. Results apply to this dataset and these simulated costs only.</p>
                </div>
              ) : <p className="text-sm text-mute">No back-test results available.</p>}
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}
