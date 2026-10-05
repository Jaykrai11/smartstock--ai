export type Action = "INCREASE" | "REDUCE" | "MAINTAIN";
export interface Daily { date: string; mean: number; p10: number; p50: number; p90: number }
export interface Catalog { items: string[]; stores: string[]; series: { item_id: string; store_id: string; category: string }[] }
export interface ForecastResponse {
  model_version: string; item_id: string; store_id: string; origin_date: string; horizon: number;
  totals: { mean: number; p50: number; p90: number }; daily: Daily[]; history: { date: string; sales: number }[];
}
export interface PlacementRow {
  item_id: string; store_id: string; current: number; recommended: number; delta: number; action: Action; reason: string[];
  target_before_constraints: number; safety_stock: number; expected_service_level: number; lead_time_days: number; shortage_units: number;
}
export interface Recommendation {
  model_version: string; generated_at: string; item_id: string; store_id: string;
  forecast: { horizon_days: number; mean_total: number; p50_total: number; p90_total: number };
  inventory: { current: number; recommended: number; delta: number; safety_stock: number; lead_time_days: number; lead_time_demand: number; cover_days: number; target_before_constraints: number };
  service_level: number; target_service_level: number; action: Action; reason: string[]; placement: PlacementRow[]; daily: Daily[];
  solver: { status: string; objective: number; warehouse_supply_units: number }; assumptions: { note: string };
}
export interface Overview {
  model_version: string; n_series: number; n_items: number; n_stores: number; forecast_units_28d: number;
  actions: Record<Action, number>; mean_expected_service_level: number; shortage_units: number;
  network_demand: { date: string; actual?: number; forecast?: number }[]; top_actions: PlacementRow[];
  backtest_95: { total_cost_change_pct: number; fill_rate_change_pts: number; avg_inventory_change_pct: number } | null; backtest_note: string;
}
export interface PolicyKpis { fill_rate: number; stockout_day_rate: number; avg_inventory: number; holding_cost: number; stockout_cost: number; transport_cost: number; total_cost: number; prob_any_stockout: number }
export interface SimResponse {
  item_id: string; store_id: string; scenario: { demand_multiplier: number; lead_time_days: number; service_level: number; starting_inventory: number; planner_aware: boolean; n_simulations: number };
  results: { baseline_policy: PolicyKpis; smartstock_policy: PolicyKpis };
  trajectory: { date: string; demand_mean: number; demand_p10: number; demand_p90: number; baseline_inventory: number; smartstock_inventory: number }[];
}
export interface ModelInfo {
  model_version: string; trained_at: string; algorithm: string; data_source: string; last_observed_date: string; loaded_series: number;
  test_metrics: Record<string, { MAE: number; RMSE: number; WAPE: number; sMAPE: number; bias: number }>; best_baseline: string;
  uncertainty: Record<string, number>; wape_improvement_vs_best_baseline: number; simulated_parameters_note: string;
  business_backtest: { assumptions: string; results: Record<string, any> };
}
