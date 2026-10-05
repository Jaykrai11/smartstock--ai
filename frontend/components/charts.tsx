"use client";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Daily, Overview, PlacementRow, SimResponse } from "@/lib/types";
import { day } from "@/lib/format";

const C = { ink: "#10243E", teal: "#0E7C7B", band: "#0E7C7B", grid: "#E3E8EE", restock: "#1D6FA5", trim: "#B7791F" };
const axis = { stroke: "#5A6B82", tickLine: false, axisLine: false } as const;
const tickDate = (v: string) => day(v);

export const NetworkChart = ({ data }: { data: Overview["network_demand"] }) => (
  <ResponsiveContainer width="100%" height={300}>
    <ComposedChart data={data} margin={{ left: 0, right: 8, top: 8 }}>
      <CartesianGrid stroke={C.grid} vertical={false} /><XAxis dataKey="date" tickFormatter={tickDate} minTickGap={40} {...axis} /><YAxis width={44} {...axis} />
      <Tooltip labelFormatter={tickDate} /><Legend verticalAlign="top" align="right" height={28} iconType="plainline" />
      <Line dataKey="actual" name="Actual units" stroke={C.ink} dot={false} strokeWidth={1.5} connectNulls={false} />
      <Line dataKey="forecast" name="Forecast units" stroke={C.teal} dot={false} strokeWidth={2.5} strokeDasharray="5 3" connectNulls={false} />
    </ComposedChart>
  </ResponsiveContainer>
);

export const ForecastChart = ({ history, daily }: { history: { date: string; sales: number }[]; daily: Daily[] }) => {
  const data = [...history.map((h) => ({ date: h.date, actual: h.sales })), ...daily.map((d) => ({ date: d.date, p50: d.p50, mean: d.mean, band: [d.p10, d.p90] as [number, number] }))];
  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={data} margin={{ left: 0, right: 8, top: 8 }}>
        <CartesianGrid stroke={C.grid} vertical={false} /><XAxis dataKey="date" tickFormatter={tickDate} minTickGap={40} {...axis} /><YAxis width={36} {...axis} />
        <Tooltip labelFormatter={tickDate} formatter={(v: any) => (Array.isArray(v) ? `${v[0].toFixed(1)} – ${v[1].toFixed(1)}` : typeof v === "number" ? v.toFixed(2) : v)} />
        <Legend verticalAlign="top" align="right" height={28} />
        <Area dataKey="band" name="P10–P90 range" stroke="none" fill={C.band} fillOpacity={0.16} />
        <Line dataKey="actual" name="Actual" stroke={C.ink} dot={false} strokeWidth={1.4} />
        <Line dataKey="mean" name="Expected (mean)" stroke={C.teal} dot={false} strokeWidth={2.5} />
        <Line dataKey="p50" name="Median (P50)" stroke={C.teal} dot={false} strokeWidth={1.2} strokeDasharray="4 3" />
      </ComposedChart>
    </ResponsiveContainer>
  );
};

export const PlacementChart = ({ rows, selected }: { rows: PlacementRow[]; selected: string }) => (
  <ResponsiveContainer width="100%" height={260}>
    <BarChart data={rows} margin={{ left: 0, right: 8, top: 8 }}>
      <CartesianGrid stroke={C.grid} vertical={false} /><XAxis dataKey="store_id" {...axis} /><YAxis width={36} {...axis} /><Tooltip /><Legend verticalAlign="top" align="right" height={28} />
      <Bar dataKey="current" name="Current stock" fill="#B8C4D2" radius={[2, 2, 0, 0]} />
      <Bar dataKey="recommended" name="Recommended stock" fill={C.restock} radius={[2, 2, 0, 0]} />
    </BarChart>
  </ResponsiveContainer>
);

export const DemandBand = ({ data }: { data: SimResponse["trajectory"] }) => (
  <ResponsiveContainer width="100%" height={200}>
    <ComposedChart data={data.map((d) => ({ ...d, band: [d.demand_p10, d.demand_p90] }))} margin={{ left: 0, right: 8, top: 8 }}>
      <CartesianGrid stroke={C.grid} vertical={false} /><XAxis dataKey="date" tickFormatter={tickDate} minTickGap={40} {...axis} /><YAxis width={36} {...axis} />
      <Tooltip labelFormatter={tickDate} /><Area dataKey="band" name="Simulated demand P10–P90" stroke="none" fill={C.band} fillOpacity={0.18} />
      <Line dataKey="demand_mean" name="Mean demand" stroke={C.teal} dot={false} strokeWidth={2} />
    </ComposedChart>
  </ResponsiveContainer>
);

export const InventoryLines = ({ data }: { data: SimResponse["trajectory"] }) => (
  <ResponsiveContainer width="100%" height={260}>
    <ComposedChart data={data} margin={{ left: 0, right: 8, top: 8 }}>
      <CartesianGrid stroke={C.grid} vertical={false} /><XAxis dataKey="date" tickFormatter={tickDate} minTickGap={40} {...axis} /><YAxis width={36} {...axis} />
      <Tooltip labelFormatter={tickDate} /><Legend verticalAlign="top" align="right" height={28} />
      <Line dataKey="baseline_inventory" name="Baseline policy: stock on hand" stroke="#7B8AA0" dot={false} strokeWidth={2} />
      <Line dataKey="smartstock_inventory" name="SmartStock policy: stock on hand" stroke={C.restock} dot={false} strokeWidth={2.5} />
    </ComposedChart>
  </ResponsiveContainer>
);
