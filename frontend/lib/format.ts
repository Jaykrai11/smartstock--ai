export const n0 = (v: number) => Math.round(v).toLocaleString("en-US");
export const n1 = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
export const pct = (v: number, d = 1) => `${(v * 100).toFixed(d)}%`;
export const day = (iso: string) => new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
export const signed = (v: number) => (v > 0 ? `+${n0(v)}` : n0(v));

export const REASONS: Record<string, string> = {
  forecast_growth: "Demand is trending above recent sales",
  forecast_decline: "Demand is trending below recent sales",
  low_stock: "Stock won't cover demand during the supplier lead time",
  lead_time_risk: "Long supplier lead time",
  high_demand_uncertainty: "Demand is hard to predict, so safety stock is large",
  target_service_level: "Needed to reach the service-level target",
  overstock: "More stock than the next replenishment cycle needs",
  capacity_constraint: "Limited by store capacity",
  supply_constraint: "Limited by warehouse supply",
  on_target: "Stock is already close to the target",
};
