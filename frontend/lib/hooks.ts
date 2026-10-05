"use client";
import { useCallback, useEffect, useRef, useState } from "react";

function useSlow(loading: boolean, ms = 4000) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!loading) { setSlow(false); return; }
    const t = setTimeout(() => setSlow(true), ms); return () => clearTimeout(t);
  }, [loading, ms]);
  return slow;
}

/** Run an async loader on mount / when deps change. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null); const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0); const slow = useSlow(loading);
  useEffect(() => {
    let live = true; setLoading(true); setError(null);
    fn().then((d) => live && setData(d)).catch((e) => live && setError(e.message)).finally(() => live && setLoading(false));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, loading, slow, retry: () => setTick((t) => t + 1) };
}

/** Run an async action on demand (button click). */
export function useAction<A, T>(fn: (a: A) => Promise<T>) {
  const [data, setData] = useState<T | null>(null); const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(false);
  const seq = useRef(0); const slow = useSlow(loading);
  const run = useCallback(async (a: A) => {
    const id = ++seq.current; setLoading(true); setError(null);
    try { const d = await fn(a); if (id === seq.current) setData(d); } catch (e) { if (id === seq.current) setError((e as Error).message); } finally { if (id === seq.current) setLoading(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { run, data, error, loading, slow };
}
