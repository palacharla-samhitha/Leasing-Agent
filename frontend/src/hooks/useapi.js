// src/hooks/useApi.js
// Reusable data fetching hook — handles loading, error, and data states

import { useState, useEffect, useCallback } from "react";

export function useApi(apiFn, deps = []) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const fetch = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFn(...args);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { fetch(); }, [fetch]);

  return { data, loading, error, refetch: fetch };
}


// ── Polling hook — for workflow state ─────────────────────────────────────────
// Polls an API every `interval` ms until `stopCondition` returns true

export function usePolling(apiFn, interval = 3000, stopCondition = null) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    if (!polling) return;

    let timer;

    const tick = async () => {
      try {
        const result = await apiFn();
        setData(result);
        setLoading(false);

        // Stop polling if condition met (e.g. workflow paused or completed)
        if (stopCondition && stopCondition(result)) {
          setPolling(false);
          return;
        }
      } catch (err) {
        setError(err.message);
        setLoading(false);
        setPolling(false);
      }
      timer = setTimeout(tick, interval);
    };

    tick();
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [polling, interval]);

  const stopPoll  = () => setPolling(false);
  const startPoll = () => { setPolling(true); setLoading(true); };

  return { data, loading, error, polling, stopPoll, startPoll };
}