"use client";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { ErrorBox, Field, Loading, Select } from "./ui";
import { useEffect } from "react";

export interface Pick { item: string; store: string }

/** Loads the catalog once and renders item/store selects. */
export default function SeriesPicker({ value, onChange }: { value: Pick; onChange: (p: Pick) => void }) {
  const { data, error, loading, slow, retry } = useAsync(() => api.catalog());
  useEffect(() => { if (data && !value.item) onChange({ item: data.items[0], store: data.stores[0] }); }, [data]); // eslint-disable-line
  if (loading) return <Loading slow={slow} label="Loading products and stores…" />;
  if (error || !data) return <ErrorBox message={error ?? "No catalog"} onRetry={retry} />;
  return (
    <>
      <Field label="Product"><Select value={value.item} onChange={(item) => onChange({ ...value, item })} options={data.items} /></Field>
      <Field label="Store"><Select value={value.store} onChange={(store) => onChange({ ...value, store })} options={data.stores} /></Field>
    </>
  );
}
