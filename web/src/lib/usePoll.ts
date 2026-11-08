"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Fetch now, then every `intervalMs` while the tab is visible.
 * Pass `null` as the fetcher to pause (e.g. nothing selected).
 * Returns the latest data, the latest error, and `refresh` to fetch immediately.
 */
export function usePoll<T>(fetcher: (() => Promise<T>) | null, deps: unknown[], intervalMs = 3000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    const f = fetcherRef.current;
    if (!f) return;
    try {
      setData(await f());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    setData(null);
    if (!fetcherRef.current) return;
    refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, intervalMs);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, intervalMs, refresh]);

  return { data, error, refresh };
}
