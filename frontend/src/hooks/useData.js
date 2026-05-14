import { useState, useEffect, useCallback } from "react";

const _cache = new Map();

export function useData(fetcher, deps = [], interval = 0) {
  const baseKey = JSON.stringify(deps) + (interval || 0);
  const cacheKey = baseKey + fetcher.toString().slice(0, 80);

  const [state, setState] = useState(() => ({
    cacheKey,
    data: _cache.get(cacheKey) ?? null,
    loading: !_cache.has(cacheKey),
    error: null
  }));

  if (state.cacheKey !== cacheKey) {
    setState({
      cacheKey,
      data: _cache.get(cacheKey) ?? null,
      loading: !_cache.has(cacheKey),
      error: null
    });
  }

  const load = useCallback(async () => {
    try {
      const result = await fetcher();
      _cache.set(cacheKey, result);
      setState(prev => ({ ...prev, data: result, loading: false, error: null }));
    } catch (e) {
      setState(prev => ({ ...prev, error: e.message, loading: false }));
    }
  }, deps);

  useEffect(() => {
    load();
    if (interval > 0) {
      const id = setInterval(load, interval);
      return () => clearInterval(id);
    }
  }, [load, interval]);

  return { data: state.data, loading: state.loading, error: state.error, reload: load };
}
