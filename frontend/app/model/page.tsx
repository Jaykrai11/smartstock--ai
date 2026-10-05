"use client";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { pct, n1 } from "@/lib/format";
import { ErrorBox, Loading, PageTitle, Panel } from "@/components/ui";

const NAMES: Record<string, string> = { naive_last_day: "Naive (last day)", moving_avg_7: "7-day average", moving_avg_28: "28-day average", seasonal_naive: "Same weekday last week", lightgbm: "LightGBM (SmartStock)" };

export default function ModelPage() {
  const { data, error, loading, slow, retry } = useAsync(() => api.modelInfo());
  return (
    <>
      <PageTitle title="Model & validation" sub="Accuracy is measured on a final period the model never saw during training or tuning." />
      {loading && <Loading slow={slow} />}{error && <ErrorBox message={error} onRetry={retry} />}
      {data && (
        <div className="space-y-6">
          <Panel title="Model">
            <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
              <dt className="text-mute">Version</dt><dd>{data.model_version}</dd><dt className="text-mute">Trained</dt><dd>{new Date(data.trained_at).toLocaleString()}</dd>
              <dt className="text-mute">Algorithm</dt><dd>{data.algorithm}</dd><dt className="text-mute">Data</dt><dd>{data.data_source}</dd><dt className="text-mute">Last sales date</dt><dd>{data.last_observed_date}</dd>
            </dl>
          </Panel>
          <Panel title="Accuracy on held-out weeks" aside={<span className="text-xs text-mute">Lower is better</span>}>
            <div className="overflow-x-auto"><table className="w-full text-left text-sm">
              <thead className="text-xs text-mute"><tr><th className="pb-2 font-medium">Method</th><th className="pb-2 text-right font-medium">WAPE</th><th className="pb-2 text-right font-medium">MAE</th><th className="pb-2 text-right font-medium">RMSE</th><th className="pb-2 text-right font-medium">Bias</th></tr></thead>
              <tbody>{Object.entries(data.test_metrics).map(([k, m]) => (
                <tr key={k} className={`border-t border-line ${k === "lightgbm" ? "bg-teal-soft/60 font-medium" : ""}`}><td className="py-2">{NAMES[k] ?? k}</td><td className="py-2 text-right tabular-nums">{pct(m.WAPE)}</td><td className="py-2 text-right tabular-nums">{m.MAE.toFixed(2)}</td><td className="py-2 text-right tabular-nums">{m.RMSE.toFixed(2)}</td><td className="py-2 text-right tabular-nums">{pct(m.bias)}</td></tr>))}</tbody>
            </table></div>
            <p className="mt-3 text-sm">LightGBM has {pct(data.wape_improvement_vs_best_baseline)} lower weighted error than the best simple baseline ({NAMES[data.best_baseline]}).</p>
          </Panel>
          <Panel title="Is the uncertainty range honest?">
            <p className="text-sm">Actual demand fell at or below the P90 forecast <strong>{pct(data.uncertainty.p90_coverage)}</strong> of the time (target 90%), and inside the P10–P90 band <strong>{pct(data.uncertainty.p10_p90_interval_coverage)}</strong> of the time (target 80%).</p>
          </Panel>
          <Panel title="Inventory back-test (simulated costs)">
            <div className="overflow-x-auto"><table className="w-full text-left text-sm">
              <thead className="text-xs text-mute"><tr><th className="pb-2 font-medium">Service target</th><th className="pb-2 text-right font-medium">Cost vs textbook rule</th><th className="pb-2 text-right font-medium">Fill rate</th><th className="pb-2 text-right font-medium">Average stock</th></tr></thead>
              <tbody>{Object.entries(data.business_backtest.results).map(([k, v]: [string, any]) => (
                <tr key={k} className="border-t border-line"><td className="py-2">{(Number(k.replace("service_level_", "")) * 100).toFixed(0)}%</td>
                  <td className="py-2 text-right tabular-nums">{n1(v.smartstock_vs_classic.total_cost_change_pct)}%</td><td className="py-2 text-right tabular-nums">{pct(v.smartstock.fill_rate)} vs {pct(v.classic_ss.fill_rate)}</td><td className="py-2 text-right tabular-nums">{n1(v.smartstock_vs_classic.avg_inventory_change_pct)}%</td></tr>))}</tbody>
            </table></div>
            <p className="mt-3 text-xs text-mute">{data.business_backtest.assumptions}. {data.simulated_parameters_note}</p>
          </Panel>
        </div>
      )}
    </>
  );
}
