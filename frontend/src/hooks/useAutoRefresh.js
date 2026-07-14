import { useEffect, useRef } from 'react';

/**
 * Keep manually-fetched data fresh across accounts without a page refresh.
 * Calls `refetch`:
 *   - on a fixed interval (default 20s) while the tab is VISIBLE,
 *   - immediately when the tab becomes visible again, and
 *   - when the window regains focus.
 * Polling is paused while the tab is hidden (no wasted requests) and resumes on
 * return. `refetch` is read through a ref so passing an inline function is fine.
 */
export function useAutoRefresh(refetch, intervalMs = 20000) {
  const cb = useRef(refetch);
  cb.current = refetch;

  useEffect(() => {
    let timer = null;
    const run = () => { if (document.visibilityState === 'visible') cb.current?.(); };
    const start = () => { if (!timer) timer = setInterval(run, intervalMs); };
    const stop = () => { if (timer) { clearInterval(timer); timer = null; } };

    const onVisibility = () => {
      if (document.visibilityState === 'visible') { cb.current?.(); start(); }
      else stop();
    };
    const onFocus = () => cb.current?.();

    start();
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('focus', onFocus);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('focus', onFocus);
    };
  }, [intervalMs]);
}

export default useAutoRefresh;
