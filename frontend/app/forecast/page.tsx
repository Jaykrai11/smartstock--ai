"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { day, n0, n1 } from "@/lib/format";
import { Button, Empty, ErrorBox, Field, KpiStrip, Loading, NumberField, PageTitle, Panel, Select } from "@/components/ui";
import SeriesPicker, { Pick } from "@/components/SeriesPicker";
import { ForecastChart } from "@/components/charts";

export default function ForecastPage() {
  const [pick, setPick] = useState<Pick>({ item: "", store: "" });
  const [horizon, setHorizon] = useState("28"); const [price, setPrice] = useState("1");
  const { run, data, error, loading, slow } = useAction(api.forecast);
  const go = () => run({ item_id: pick.item, store_id: pick.store, horizon: Number(horizon), price_multiplier: Number(price) });
  return (
    <>
      <PageTitle title="Demand forecast" sub="How many units a product is expected to sell in a store, with a range that shows how uncertain the forecast is." />
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Panel title="Forecast settings">
          <div className="space-y-4">
            <SeriesPicker value={pick} onChange={setPick} />
            <Field label="Days ahead"><Select value={horizon} onChange={setHorizon} options={["7", "14", "21", "28"]} /></Field>
            <Field label="Planned price vs today" hint="1.0 keeps today's price; 0.9 is a 10% discount."><NumberField value={price} onChange={setPrice} min={0.5} max={2} step={0.05} /></Field>
            <Button onClick={go} loading={loading} disabled={!pick.item}>Run forecast</Button>
          </div>
        </Panel>
        <div className="min-w-0 space-y-6">
          {loading && <Loading slow={slow} label="Forecasting…" />}
          {error && <ErrorBox message={error} onRetry={go} />}
          {!data && !loading && !error && <Empty>Choose a product and store, then run the forecast.</Empty>}
          {data && !loading && (<>
            <KpiStrip items={[
              { label: `Expected demand, ${data.horizon} days`, value: `${n0(data.totals.mean)} units` },
              { label: "High-demand case (P90)", value: `${n0(data.totals.p90)} units`, note: "Demand exceeds this about 1 time in 10" },
              { label: "Last sales data", value: day(data.origin_date) }, { label: "Model", value: data.model_version },
            ]} />
            <Panel title={`${data.item_id} · ${data.store_id}`} aside={<span className="text-xs text-mute">Units per day</span>}>
              <ForecastChart history={data.history} daily={data.daily} />
              <p className="mt-3 text-xs text-mute">The shaded band covers the range between the 10th and 90th percentile of daily demand. Daily forecasts are shown at {n1(data.daily.reduce((a, d) => a + d.mean, 0) / data.daily.length)} units per day on average.</p>
            </Panel>
          </>)}
        </div>
      </div>
    </>
  );
}
